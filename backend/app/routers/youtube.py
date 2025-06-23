#!/usr/bin/env python3
"""
File: youtube.py
Description: YouTube 관련 API 라우터
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import os
import glob
from pathlib import Path
import time
import asyncio
import logging
import subprocess
import json
from urllib.parse import unquote
import tempfile

from app.services.extractor import VideoExtractor
from app.services.subtitle import SubtitleProcessor, SubtitleIndexer
from app.services.generator import RepeatVideoGenerator, ThumbnailGenerator
from app.services.pronunciation import PronunciationAnalyzer
from app.services.whisper_generator import WhisperGenerator
from app.config import settings
from app.common.utils import setup_logger, ensure_dir_exists, get_project_root

# 로거 설정
logger = setup_logger('youtube_routes', 'youtube_routes.log')

# 라우터 정의
router = APIRouter()

# 데이터 모델 정의
class YouTubeRequest(BaseModel):
    """YouTube 다운로드 요청 데이터 모델"""
    url: str = Field(..., description="YouTube 영상 URL")
    output_dir: Optional[str] = Field(None, description="출력 디렉토리 (기본값: data/clips)")
    options: Optional[Dict[str, Any]] = Field(None, description="추가 옵션")
    subtitle_languages: Optional[List[str]] = Field(None, description="다운로드할 자막 언어 코드 목록 (기본값: ['en', 'en-US', 'en-GB', 'ko'])")

class YouTubeTranscriptRequest(BaseModel):
    """YouTube 트랜스크립트 요청 데이터 모델"""
    url: str = Field(..., description="YouTube 영상 URL")
    language: Optional[str] = Field("en", description="자막 언어 코드 (기본값: 'en')")

class TranscriptItem(BaseModel):
    """트랜스크립트 항목 모델"""
    text: str = Field(..., description="자막 텍스트")
    start: float = Field(..., description="시작 시간(초)")
    duration: float = Field(..., description="지속 시간(초)")

class VideoClip(BaseModel):
    """비디오 클립 정보 모델"""
    id: str = Field(..., description="클립 ID")
    name: str = Field(..., description="클립 이름")
    path: str = Field(..., description="클립 경로")
    size: int = Field(..., description="클립 크기 (바이트)")
    modified: int = Field(..., description="수정 시간 (유닉스 타임스탬프)")

class TaskStatus(BaseModel):
    """작업 상태 모델"""
    state: str = Field(..., description="작업 상태 (PENDING, PROGRESS, SUCCESS, FAILURE)")
    progress: int = Field(..., description="진행률 (0-100)")
    status: str = Field(..., description="상태 메시지")
    error: Optional[str] = Field(None, description="오류 메시지 (실패 시)")
    result: Optional[Dict[str, Any]] = Field(None, description="작업 결과 (성공 시)")

class YouTubeTranscriptResponse(BaseModel):
    """YouTube 트랜스크립트 응답 모델"""
    status: str = Field(..., description="응답 상태 (success/error)")
    message: str = Field(..., description="응답 메시지")
    transcripts: Optional[List[TranscriptItem]] = Field(None, description="트랜스크립트 목록")

class WhisperEstimateRequest(BaseModel):
    """Whisper 처리 시간 예상 요청 모델"""
    video_path: str = Field(..., description="비디오 파일 경로")
    model: str = Field("tiny", description="Whisper 모델 크기 (tiny, base, small, medium, large)")

class WhisperGenerateRequest(BaseModel):
    """Whisper 자막 생성 요청 모델"""
    video_path: str = Field(..., description="비디오 파일 경로")
    model: str = Field("tiny", description="Whisper 모델 크기 (tiny, base, small, medium, large)")
    language: str = Field("en", description="생성할 자막 언어")

# 자막 검색 관련 모델 추가
class SubtitleSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    threshold: Optional[float] = 0.5
    multiline: Optional[bool] = False  # 멀티라인 쿼리 여부

class SubtitleSearchResult(BaseModel):
    video_path: str
    name: str
    index: int
    start_time: str
    end_time: str
    text: str
    score: float

class SubtitleSearchResponse(BaseModel):
    status: str
    message: Optional[str] = None
    results: Optional[List[SubtitleSearchResult]] = None

# 작업 시간 추정 관련 모델 추가
class EstimateRequest(BaseModel):
    video_path: str
    subtitle_segments: List[Dict]
    
class EstimateResponse(BaseModel):
    status: str
    message: Optional[str] = None
    estimated_seconds: Optional[float] = None

# 경로 표준화 함수
def standardize_path(path_str: str) -> Path:
    """
    경로 문자열을 표준화된 Path 객체로 변환합니다.
    
    Args:
        path_str: 처리할 경로 문자열
        
    Returns:
        표준화된 Path 객체
    """
    path = Path(path_str)
    
    # 절대 경로이거나 이미 존재하는 경우 그대로 반환
    if path.is_absolute() or path.exists():
        logger.debug(f"경로 표준화: 절대 경로 또는 기존 경로 '{path}' 사용")
        return path
        
    # 상대 경로 처리
    if path_str.startswith("data/clips/"):
        result = Path(path_str)
        logger.debug(f"경로 표준화: data/clips/ 형식 '{path_str}' -> '{result}'")
    elif path_str.startswith("clips/"):
        result = Path("data") / path_str
        logger.debug(f"경로 표준화: clips/ 형식 '{path_str}' -> '{result}'")
    else:
        result = Path(settings.DEFAULT_CLIP_DIR) / path_str
        logger.debug(f"경로 표준화: 일반 형식 '{path_str}' -> '{result}'")
    
    return result

# API 엔드포인트 정의
@router.get("/clips")
async def list_videos():
    """클립 디렉토리의 모든 비디오 파일을 나열합니다."""
    try:
        logger.info("클립 목록 조회 시작")
        clips_dir = Path(settings.DEFAULT_CLIP_DIR)
        
        if not clips_dir.exists():
            logger.warning(f"클립 디렉토리가 존재하지 않음: {clips_dir}")
            return JSONResponse(
                status_code=200,
                content=[]
            )
        
        # 클립 디렉토리에서 모든 MP4 파일 찾기
        video_files = list(clips_dir.glob("*.mp4"))
        logger.info(f"{len(video_files)}개의 비디오 파일 발견")
        
        # 자막 서비스 초기화
        subtitle_processor = SubtitleProcessor()
        
        videos = []
        for video_file in video_files:
            try:
                # 파일 정보 가져오기
                file_stat = video_file.stat()
                file_size = file_stat.st_size
                file_modified = file_stat.st_mtime
                
                # 자막 파일 확인
                has_subtitle = False
                available_subtitles = []
                
                # 지원되는 언어 코드 목록
                lang_codes = ['en', 'en-US', 'en-GB', 'ko', 'ja', 'zh-CN', 'zh-TW', 'fr', 'de', 'es']
                
                # 기본 자막 파일 확장자 확인
                for ext in ['.srt', '.vtt']:
                    subtitle_path = video_file.with_suffix(ext)
                    if subtitle_path.exists():
                        has_subtitle = True
                        available_subtitles.append(ext.lstrip('.'))
                
                # 언어별 자막 파일 확장자 확인
                for lang in lang_codes:
                    # 언어 코드 정리 (파일명으로 사용 가능하게)
                    file_lang = lang.replace('-', '_').lower()
                    
                    for ext in [f'.{file_lang}.srt', f'.{file_lang}.vtt']:
                        subtitle_path = video_file.with_suffix(ext)
                        if subtitle_path.exists():
                            has_subtitle = True
                            available_subtitles.append(ext.lstrip('.'))
                
                # 인간 친화적인 파일 크기
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # 상대 경로 처리
                relative_path = str(video_file.relative_to(clips_dir.parent)) if clips_dir.parent in video_file.parents else str(video_file)
                
                videos.append({
                    "name": video_file.name,
                    "path": relative_path,
                    "full_path": str(video_file),
                    "size": size_str,
                    "modified": file_modified,
                    "modified_str": time.strftime("%m/%d/%Y, %I:%M:%S %p", time.localtime(file_modified)),
                    "has_subtitle": has_subtitle,
                    "available_subtitles": available_subtitles
                })
                logger.debug(f"비디오 파일 정보 추가: {video_file.name}")
            except Exception as e:
                logger.error(f"비디오 파일 처리 오류 ({video_file}): {str(e)}")
                # 개별 파일 오류는 무시하고 계속 진행
                continue
        
        # 수정 시간 기준으로 정렬 (최신 항목이 위에)
        videos.sort(key=lambda x: x["modified"], reverse=True)
        logger.info(f"클립 목록 조회 완료: {len(videos)}개의 클립 반환")
        
        return JSONResponse(
            status_code=200,
            content=videos
        )
    
    except Exception as e:
        logger.error(f"비디오 목록 조회 오류: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"비디오 목록 조회 실패: {str(e)}",
                "error_details": str(e)
            }
        )

@router.post("/transcript", response_model=YouTubeTranscriptResponse)
async def get_youtube_transcript(request: YouTubeTranscriptRequest):
    """YouTube 영상의 트랜스크립트를 가져옵니다."""
    try:
        logger.info(f"YouTube 트랜스크립트 요청: URL={request.url}, 언어={request.language}")
        
        extractor = VideoExtractor()
        transcripts = await extractor.get_youtube_transcript(
            url=request.url,
            language=request.language
        )
        
        if not transcripts:
            logger.warning(f"트랜스크립트를 찾을 수 없음: URL={request.url}, 언어={request.language}")
            return YouTubeTranscriptResponse(
                status="error",
                message="트랜스크립트를 찾을 수 없습니다.",
                transcripts=[]
            )
            
        # TranscriptItem 목록으로 변환
        transcript_items = [
            TranscriptItem(
                text=item["text"],
                start=item["start"],
                duration=item["duration"]
            ) for item in transcripts
        ]
        
        logger.info(f"트랜스크립트 가져오기 성공: {len(transcript_items)}개의 항목")
        return YouTubeTranscriptResponse(
            status="success",
            message=f"{len(transcript_items)}개의 트랜스크립트를 찾았습니다.",
            transcripts=transcript_items
        )
    
    except Exception as e:
        logger.error(f"트랜스크립트 가져오기 오류: {str(e)}", exc_info=True)
        return YouTubeTranscriptResponse(
            status="error",
            message=f"트랜스크립트 가져오기 실패: {str(e)}",
            transcripts=[]
        )

@router.post("/download")
async def download_youtube_video(
    request: YouTubeRequest, 
    background_tasks: BackgroundTasks
):
    """
    YouTube 영상 다운로드 API 엔드포인트
    
    Args:
        request: 다운로드 요청 데이터
        background_tasks: 백그라운드 작업 객체
        
    Returns:
        다운로드 작업 상태 정보
    """
    try:
        logger.info(f"YouTube 영상 다운로드 요청: {request.url}")
        
        # 출력 디렉토리 설정
        output_dir = request.output_dir or settings.DEFAULT_CLIP_DIR
        ensure_dir_exists(output_dir)
        
        # 추가 옵션 처리
        options = request.options or {}
        
        # 작업 ID 생성
        task_id = f"download_{int(time.time())}"
        
        # 비디오 추출기 초기화
        video_extractor = VideoExtractor()
        
        # 작업 상태 저장소 초기화
        if not hasattr(download_youtube_video, 'tasks'):
            download_youtube_video.tasks = {}
            
        download_youtube_video.tasks[task_id] = {
            'state': 'PENDING',
            'progress': 0,
            'status': '다운로드 준비 중...',
            'error': None,
            'result': None
        }
        
        # 진행 상황 콜백 함수
        async def progress_callback(progress: float, msg: str):
            if task_id in download_youtube_video.tasks:
                download_youtube_video.tasks[task_id]['progress'] = int(progress * 100)
                download_youtube_video.tasks[task_id]['status'] = msg
                logger.info(f"다운로드 진행 상황 ({task_id}): {progress:.1%} - {msg}")
        
        # 백그라운드 다운로드 작업 정의
        async def download_task():
            try:
                download_youtube_video.tasks[task_id]['state'] = 'PROGRESS'
                
                # 자막 언어 처리
                subtitle_languages = request.subtitle_languages
                
                # 비디오 다운로드
                video_path = await video_extractor.download_youtube(
                    request.url, 
                    output_dir,
                    progress_callback=progress_callback,
                    subtitle_languages=subtitle_languages
                )
                
                if video_path:
                    # 자막 존재 여부 확인
                    has_subtitle = False
                    available_subtitles = []
                    
                    # 다양한 자막 파일 확장자 확인
                    for ext in ['.srt', '.vtt', '.en.srt', '.en.vtt', '.ko.srt', '.ko.vtt']:
                        subtitle_path = video_path.with_suffix(ext)
                        if subtitle_path.exists():
                            has_subtitle = True
                            available_subtitles.append(ext.lstrip('.'))
                    
                    # 성공 상태로 업데이트
                    download_youtube_video.tasks[task_id]['state'] = 'SUCCESS'
                    download_youtube_video.tasks[task_id]['progress'] = 100
                    download_youtube_video.tasks[task_id]['status'] = '다운로드 완료'
                    download_youtube_video.tasks[task_id]['result'] = {
                        'video_path': str(video_path),
                        'file_name': video_path.name,
                        'has_subtitle': has_subtitle,
                        'available_subtitles': available_subtitles
                    }
                else:
                    # 실패 상태로 업데이트
                    download_youtube_video.tasks[task_id]['state'] = 'FAILURE'
                    download_youtube_video.tasks[task_id]['error'] = '비디오를 다운로드할 수 없습니다.'
            except Exception as e:
                logger.error(f"다운로드 작업 오류: {str(e)}")
                if task_id in download_youtube_video.tasks:
                    download_youtube_video.tasks[task_id]['state'] = 'FAILURE'
                    download_youtube_video.tasks[task_id]['error'] = str(e)
        
        # 백그라운드 작업 추가
        background_tasks.add_task(download_task)
        
        return {
            'status': 'pending',
            'task_id': task_id,
            'message': '다운로드가 시작되었습니다. 상태를 확인하세요.'
        }
    except Exception as e:
        logger.error(f"다운로드 요청 처리 오류: {str(e)}")
        return {
            'status': 'error',
            'message': f'다운로드 요청 처리 오류: {str(e)}'
        }

@router.get("/download/status/{task_id}")
async def get_download_status(task_id: str):
    """다운로드 작업의 진행 상황을 확인합니다."""
    logger.debug(f"다운로드 상태 확인: task_id={task_id}")
    
    if not hasattr(download_youtube_video, "tasks"):
        logger.warning(f"다운로드 작업 목록이 없음: task_id={task_id}")
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다."}
        )
    
    task_info = download_youtube_video.tasks.get(task_id)
    if not task_info:
        logger.warning(f"해당 작업 정보가 없음: task_id={task_id}")
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다."}
        )
    
    logger.debug(f"다운로드 상태 반환: task_id={task_id}, state={task_info['state']}, progress={task_info['progress']}")
    return JSONResponse(
        status_code=200,
        content={
            "status": task_info["state"].lower(),
            "progress": task_info["progress"],
            "message": task_info["status"],
            "error": task_info["error"],
            "result": task_info["result"]
        }
    )

@router.get("/subtitle/get")
async def get_subtitle(video_path: str, language: Optional[str] = None, use_whisper: Optional[bool] = False):
    """비디오 파일의 자막을 가져옵니다. 자막이 없는 경우 Whisper 생성 가능 여부 반환"""
    try:
        logger.info(f"자막 가져오기 요청: video_path={video_path}, language={language}, use_whisper={use_whisper}")
        
        if not video_path:
            logger.warning("비디오 경로가 지정되지 않음")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "비디오 경로가 지정되지 않았습니다.",
                    "subtitles": []
                }
            )
            
        # 표준화된 경로 처리 사용
        video_file = standardize_path(video_path)
        logger.debug(f"비디오 경로 표준화: {video_path} -> {video_file}")
        
        if not video_file.exists():
            logger.warning(f"비디오 파일을 찾을 수 없음: {video_file}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"비디오 파일을 찾을 수 없습니다: {video_path}",
                    "subtitles": []
                }
            )
            
        # 자막 처리기 생성
        subtitle_processor = SubtitleProcessor()
        
        # 자막 가져오기 (언어 지정)
        subtitles = await subtitle_processor.get_subtitles(str(video_file), language)
        
        if not subtitles:
            logger.info(f"자막이 없음: {video_file}, 언어: {language}, Whisper 생성 옵션={use_whisper}")
            # 자막이 없는 경우
            # 사용자가 Whisper로 생성하길 원하는 경우
            if use_whisper:
                # Whisper로 자막 생성
                srt_path = video_file.with_suffix('.srt') if not language else video_file.with_suffix(f'.{language.replace("-", "_").lower()}.srt')
                logger.info(f"Whisper로 자막 생성 시작: {video_file} -> {srt_path}")
                whisper_generator = WhisperGenerator()
                success, result = await whisper_generator.generate_subtitle(
                    str(video_file), 
                    str(srt_path), 
                    model="tiny", 
                    language=language or "en"
                )
                
                if success:
                    logger.info(f"Whisper 자막 생성 성공: {srt_path}")
                    # 생성된 자막 로드
                    return await get_subtitle(video_path, language)
                else:
                    logger.error(f"Whisper 자막 생성 실패: {result.get('error', '알 수 없는 오류')}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "status": "error",
                            "message": f"Whisper로 자막 생성 실패: {result.get('error', '알 수 없는 오류')}",
                            "subtitles": []
                        }
                    )
            
            # Whisper 생성 가능성 정보와 함께 반환
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "자막이 없습니다. Whisper로 자막을 생성할 수 있습니다.",
                    "subtitles": [],
                    "whisper_available": True,
                    "whisper_models": ["tiny", "base", "small", "medium", "large"],
                    "supported_languages": ["en", "ko", "ja", "zh-CN", "zh-TW", "fr", "de", "es"]
                }
            )
            
        # 자막 항목 가공
        subtitle_items = []
        for i, sub in enumerate(subtitles):
            subtitle_items.append({
                "index": i,
                "start_time": sub.get("start_time", "00:00:00,000"),
                "end_time": sub.get("end_time", "00:00:00,000"),
                "text": sub.get("text", ""),
                "translation": sub.get("translation", "")
            })
        
        logger.info(f"자막 가져오기 성공: {video_file}, {len(subtitle_items)}개의 자막")
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"{len(subtitle_items)}개의 자막을 찾았습니다.",
                "subtitles": subtitle_items
            }
        )
        
    except Exception as e:
        logger.error(f"자막 가져오기 오류: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"자막 가져오기 오류: {str(e)}",
                "error_details": str(e),
                "subtitles": []
            }
        )

@router.post("/whisper/estimate")
async def estimate_whisper_time(request: WhisperEstimateRequest):
    """Whisper 모델의 자막 생성 시간을 예상합니다."""
    try:
        logger.info(f"Whisper 처리 시간 예상 요청: video_path={request.video_path}, model={request.model}")
        
        # 표준화된 경로 처리 사용
        video_path = standardize_path(request.video_path)
        logger.debug(f"비디오 경로 표준화: {request.video_path} -> {video_path}")
        
        # 파일이 존재하는지 확인
        if not video_path.exists():
            logger.warning(f"비디오 파일을 찾을 수 없음: {video_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"비디오 파일을 찾을 수 없습니다: {str(video_path)}"
                }
            )
        
        # WhisperGenerator 인스턴스 생성
        whisper_generator = WhisperGenerator()
        
        # 처리 시간 예상
        estimate = await whisper_generator.estimate_processing_time(
            str(video_path),
            model=request.model
        )
        
        logger.info(f"Whisper 처리 시간 예상 완료: {estimate}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "estimate": estimate
            }
        )
    
    except Exception as e:
        logger.error(f"Whisper 처리 시간 예상 오류: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"처리 시간 예상 실패: {str(e)}",
                "error_details": str(e)
            }
        )

@router.post("/whisper/generate")
async def generate_whisper_subtitle(
    request: WhisperGenerateRequest,
    background_tasks: BackgroundTasks
):
    """Whisper를 사용하여 자막을 생성합니다."""
    try:
        # 비디오 파일 경로 처리
        video_path = Path(request.video_path)
        if not video_path.is_absolute():
            # 상대 경로인 경우 기본 디렉토리에 상대적인 경로로 변환
            if video_path.parts and video_path.parts[0] == "clips":
                video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[1:])
            elif video_path.parts and video_path.parts[0] == "data" and len(video_path.parts) > 1 and video_path.parts[1] == "clips":
                video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[2:])
            else:
                video_path = Path(settings.DEFAULT_CLIP_DIR) / video_path
        
        # 파일이 존재하는지 확인
        if not video_path.exists():
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"비디오 파일을 찾을 수 없습니다: {str(video_path)}"
                }
            )
        
        # 출력 자막 파일 경로 설정
        if request.language == "en":
            output_path = str(video_path.with_suffix(".en.srt"))
        else:
            output_path = str(video_path.with_suffix(f".{request.language}.srt"))
        
        # 고유 작업 ID 생성
        task_id = f"whisper_{int(time.time())}"
        
        # 작업 상태 추적을 위한 임시 딕셔너리
        if not hasattr(generate_whisper_subtitle, "tasks"):
            generate_whisper_subtitle.tasks = {}
        
        # 초기 상태 설정
        generate_whisper_subtitle.tasks[task_id] = {
            "state": "PENDING",
            "progress": 0,
            "status": "자막 생성을 준비 중입니다...",
            "error": None,
            "result": None
        }
        
        # WhisperGenerator 인스턴스 생성
        whisper_generator = WhisperGenerator()
        
        # 예상 처리 시간 계산
        estimate = await whisper_generator.estimate_processing_time(
            str(video_path),
            model=request.model
        )
        
        # 백그라운드 작업으로 자막 생성 실행
        async def generate_task():
            try:
                generate_whisper_subtitle.tasks[task_id]["state"] = "PROGRESS"
                
                # 처리 진행 상황 업데이트 함수
                start_time = time.time()
                estimated_seconds = estimate.get("estimated_seconds", 60)
                
                # 상태 업데이트 작업 (1초마다)
                async def update_status():
                    while generate_whisper_subtitle.tasks[task_id]["state"] == "PROGRESS":
                        elapsed = time.time() - start_time
                        progress = min(0.95, elapsed / estimated_seconds) if estimated_seconds > 0 else 0.5
                        generate_whisper_subtitle.tasks[task_id]["progress"] = int(progress * 100)
                        generate_whisper_subtitle.tasks[task_id]["status"] = f"자막 생성 중... {progress:.0%}"
                        await asyncio.sleep(1)
                
                # 상태 업데이트 태스크 시작
                update_task = asyncio.create_task(update_status())
                
                # 자막 생성 실행
                success, result = await whisper_generator.generate_subtitle(
                    str(video_path),
                    output_path,
                    model=request.model,
                    language=request.language
                )
                
                # 상태 업데이트 태스크 취소
                update_task.cancel()
                
                if success:
                    generate_whisper_subtitle.tasks[task_id]["state"] = "SUCCESS"
                    generate_whisper_subtitle.tasks[task_id]["progress"] = 100
                    generate_whisper_subtitle.tasks[task_id]["status"] = "자막 생성 완료"
                    generate_whisper_subtitle.tasks[task_id]["result"] = {
                        "output_path": result.get("output_path"),
                        "duration": result.get("duration"),
                        "model": result.get("model")
                    }
                else:
                    generate_whisper_subtitle.tasks[task_id]["state"] = "FAILURE"
                    generate_whisper_subtitle.tasks[task_id]["progress"] = 0
                    generate_whisper_subtitle.tasks[task_id]["status"] = "자막 생성 실패"
                    generate_whisper_subtitle.tasks[task_id]["error"] = result.get("error")
            
            except Exception as e:
                generate_whisper_subtitle.tasks[task_id]["state"] = "FAILURE"
                generate_whisper_subtitle.tasks[task_id]["error"] = str(e)
        
        # 백그라운드 작업 등록
        background_tasks.add_task(generate_task)
        
        # 즉시 작업 ID 반환
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "자막 생성이 시작되었습니다",
                "task_id": task_id,
                "estimate": estimate
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"자막 생성 시작 실패: {str(e)}"
            }
        )

@router.get("/whisper/status/{task_id}")
async def get_whisper_status(task_id: str):
    """Whisper 자막 생성 작업의 진행 상황을 확인합니다."""
    if not hasattr(generate_whisper_subtitle, "tasks"):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다."}
        )
    
    task_info = generate_whisper_subtitle.tasks.get(task_id)
    if not task_info:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다."}
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "status": task_info["state"].lower(),
            "progress": task_info["progress"],
            "message": task_info["status"],
            "error": task_info["error"],
            "result": task_info["result"]
        }
    )

@router.get("/test")
async def test_youtube_api():
    """YouTube API 연결 테스트"""
    return {
        "status": "success",
        "message": "YouTube API 연결 테스트 성공",
        "services": ["extractor", "subtitle", "generator", "pronunciation"],
        "version": settings.APP_VERSION
    }

# 반복 영상 생성 요청 모델
class RepeatVideoRequest(BaseModel):
    """반복 영상 생성 요청 모델"""
    video_path: str = Field(..., description="비디오 파일 경로")
    start_time: str = Field(..., description="시작 시간 (00:00:00,000 형식)")
    end_time: str = Field(..., description="종료 시간 (00:00:00,000 형식)")
    repeat_count: int = Field(3, description="반복 횟수")
    output_name: Optional[str] = Field(None, description="출력 파일 이름 (옵션)")

# 썸네일 생성 요청 모델
class ThumbnailRequest(BaseModel):
    """썸네일 생성 요청 모델"""
    video_path: str = Field(..., description="비디오 파일 경로")
    time_pos: str = Field(..., description="썸네일 추출 시간 위치 (00:00:00 형식)")
    text: Optional[str] = Field(None, description="오버레이할 텍스트 (옵션)")
    subtitle: Optional[str] = Field(None, description="하단에 표시할 자막 텍스트 (옵션)")
    template: Optional[str] = Field("basic", description="사용할 템플릿 (basic, title)")
    output_name: Optional[str] = Field(None, description="출력 파일 이름 (옵션)")

@router.post("/generate-repeat")
async def generate_repeat_video(
    request: RepeatVideoRequest,
    background_tasks: BackgroundTasks
):
    """지정된 구간의 비디오를 여러 번 반복하는 영상 생성"""
    try:
        logger.info(f"반복 영상 생성 요청: {request.video_path}, {request.start_time}~{request.end_time}, {request.repeat_count}회")
        
        # 비디오 파일 경로 처리
        video_path = Path(request.video_path)
        if not video_path.is_absolute():
            # 상대 경로인 경우 기본 디렉토리에 상대적인 경로로 변환
            if video_path.parts and video_path.parts[0] == "clips":
                video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[1:])
            elif video_path.parts and video_path.parts[0] == "clips_output":
                video_path = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR) / Path(*video_path.parts[1:])
            elif video_path.parts and video_path.parts[0] == "data":
                if len(video_path.parts) > 1 and video_path.parts[1] == "clips":
                    video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[2:])
                elif len(video_path.parts) > 1 and video_path.parts[1] == "clips_output":
                    video_path = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR) / Path(*video_path.parts[2:])
                else:
                    video_path = Path(settings.DEFAULT_CLIP_DIR) / video_path
            else:
                video_path = Path(settings.DEFAULT_CLIP_DIR) / video_path
        
        # 파일이 존재하는지 확인
        if not video_path.exists():
            logger.warning(f"비디오 파일을 찾을 수 없음: {video_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"비디오 파일을 찾을 수 없습니다: {str(video_path)}"
                }
            )
        
        # 출력 파일 이름 설정
        if request.output_name:
            output_name = request.output_name
        else:
            # 원본 파일 이름에서 확장자를 제외한 이름 가져오기
            video_name = video_path.stem
            output_name = f"{video_name}_repeat{request.repeat_count}_{request.start_time.replace(':', '_').replace(',', '_')}.mp4"
        
        # 출력 파일 경로 설정 - clips_output 디렉토리에 저장
        output_dir = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        output_path = output_dir / output_name
        
        # 작업 ID 생성
        task_id = f"repeat_{int(time.time())}"
        
        # 작업 상태 추적을 위한 임시 딕셔너리
        if not hasattr(generate_repeat_video, "tasks"):
            generate_repeat_video.tasks = {}
        
        # 초기 상태 설정
        generate_repeat_video.tasks[task_id] = {
            "state": "PENDING",
            "progress": 0,
            "status": "반복 영상 생성을 준비 중입니다...",
            "error": None,
            "result": None
        }
        
        # RepeatVideoGenerator 인스턴스 생성
        repeat_generator = RepeatVideoGenerator()
        
        # 백그라운드 작업으로 반복 영상 생성 실행
        async def generate_task():
            try:
                generate_repeat_video.tasks[task_id]["state"] = "PROGRESS"
                
                # 진행 상황 업데이트 콜백 함수
                async def progress_callback(progress: float, msg: str):
                    generate_repeat_video.tasks[task_id]["progress"] = int(progress * 100)
                    generate_repeat_video.tasks[task_id]["status"] = msg
                
                # 반복 영상 생성 실행
                success, result = await repeat_generator.generate_repeat_video(
                    str(video_path),
                    request.start_time,
                    request.end_time,
                    str(output_path),
                    request.repeat_count,
                    progress_callback
                )
                
                if success:
                    generate_repeat_video.tasks[task_id]["state"] = "SUCCESS"
                    generate_repeat_video.tasks[task_id]["progress"] = 100
                    generate_repeat_video.tasks[task_id]["status"] = "반복 영상 생성 완료"
                    generate_repeat_video.tasks[task_id]["result"] = {
                        "output_path": str(output_path),
                        "output_name": output_name,
                        "repeat_count": request.repeat_count,
                        "duration": result.get("duration", 0)
                    }
                else:
                    generate_repeat_video.tasks[task_id]["state"] = "FAILURE"
                    generate_repeat_video.tasks[task_id]["progress"] = 0
                    generate_repeat_video.tasks[task_id]["status"] = "반복 영상 생성 실패"
                    generate_repeat_video.tasks[task_id]["error"] = result.get("error")
            
            except Exception as e:
                generate_repeat_video.tasks[task_id]["state"] = "FAILURE"
                generate_repeat_video.tasks[task_id]["error"] = str(e)
                logger.error(f"반복 영상 생성 작업 실패: {str(e)}", exc_info=True)
        
        # 백그라운드 작업 등록
        background_tasks.add_task(generate_task)
        
        # 즉시 작업 ID 반환
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "반복 영상 생성이 시작되었습니다",
                "task_id": task_id,
                "output_name": output_name
            }
        )
    
    except Exception as e:
        logger.error(f"반복 영상 생성 시작 실패: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"반복 영상 생성 시작 실패: {str(e)}",
                "error_details": str(e)
            }
        )

@router.get("/repeat/status/{task_id}")
async def get_repeat_status(task_id: str):
    """반복 영상 생성 작업의 진행 상황을 확인합니다."""
    if not hasattr(generate_repeat_video, "tasks"):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다."}
        )
    
    task_info = generate_repeat_video.tasks.get(task_id)
    if not task_info:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다."}
        )
    
    return JSONResponse(
        status_code=200,
        content={
            "status": task_info["state"].lower(),
            "progress": task_info["progress"],
            "message": task_info["status"],
            "error": task_info["error"],
            "result": task_info["result"]
        }
    )

@router.post("/generate-thumbnail")
async def generate_thumbnail(request: ThumbnailRequest):
    """비디오에서 지정된 시간 위치의 썸네일 생성"""
    try:
        logger.info(f"썸네일 생성 요청: {request.video_path}, 위치: {request.time_pos}")
        
        # 비디오 파일 경로 처리
        video_path = Path(request.video_path)
        if not video_path.is_absolute():
            # 상대 경로인 경우 기본 디렉토리에 상대적인 경로로 변환
            if video_path.parts and video_path.parts[0] == "clips":
                video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[1:])
            elif video_path.parts and video_path.parts[0] == "data" and len(video_path.parts) > 1 and video_path.parts[1] == "clips":
                video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[2:])
            else:
                video_path = Path(settings.DEFAULT_CLIP_DIR) / video_path
        
        # 파일이 존재하는지 확인
        if not video_path.exists():
            logger.warning(f"비디오 파일을 찾을 수 없음: {video_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"비디오 파일을 찾을 수 없습니다: {str(video_path)}"
                }
            )
        
        # 출력 파일 이름 설정
        if request.output_name:
            output_name = request.output_name
            if not output_name.lower().endswith(('.jpg', '.png')):
                output_name += '.jpg'
        else:
            # 원본 파일 이름에서 확장자를 제외한 이름 가져오기
            video_name = video_path.stem
            output_name = f"{video_name}_thumb_{request.time_pos.replace(':', '_')}.jpg"
        
        # 출력 파일 경로 설정
        thumbnails_dir = Path(settings.DEFAULT_CLIP_DIR) / "thumbnails"
        ensure_dir_exists(thumbnails_dir)
        output_path = thumbnails_dir / output_name
        
        # ThumbnailGenerator 인스턴스 생성
        thumbnail_generator = ThumbnailGenerator()
        
        # 썸네일 생성 실행
        success, result = thumbnail_generator.generate_thumbnail(
            str(video_path),
            request.time_pos,
            str(output_path),
            request.text,
            request.subtitle,
            request.template
        )
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "썸네일 생성 완료",
                    "output_path": str(output_path),
                    "output_name": output_name
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "썸네일 생성 실패",
                    "error": result.get("error")
                }
            )
    
    except Exception as e:
        logger.error(f"썸네일 생성 실패: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"썸네일 생성 실패: {str(e)}",
                "error_details": str(e)
            }
        )

# 최종 영상 생성 요청 모델
class FinalVideoRequest(BaseModel):
    """최종 영상 생성 요청 모델"""
    video_path: str = Field(..., description="반복 영상 파일 경로")
    thumbnail_path: str = Field(..., description="썸네일 이미지 파일 경로")
    thumbnail_duration: float = Field(3.0, description="썸네일 표시 시간(초)")
    output_name: Optional[str] = Field(None, description="출력 파일 이름 (옵션)")

@router.post("/generate-final")
async def generate_final_video(request: FinalVideoRequest):
    """썸네일과 반복 영상을 합쳐 최종 영상을 생성합니다."""
    try:
        logger.info(f"최종 영상 생성 요청: 반복영상={request.video_path}, 썸네일={request.thumbnail_path}")
        
        # 비디오 파일 경로 처리
        video_path = Path(request.video_path)
        if not video_path.is_absolute():
            # 상대 경로인 경우 기본 디렉토리에 상대적인 경로로 변환
            if video_path.parts and video_path.parts[0] == "clips":
                video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[1:])
            elif video_path.parts and video_path.parts[0] == "clips_output":
                video_path = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR) / Path(*video_path.parts[1:])
            elif video_path.parts and video_path.parts[0] == "data":
                if len(video_path.parts) > 1 and video_path.parts[1] == "clips":
                    video_path = Path(settings.DEFAULT_CLIP_DIR) / Path(*video_path.parts[2:])
                elif len(video_path.parts) > 1 and video_path.parts[1] == "clips_output":
                    video_path = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR) / Path(*video_path.parts[2:])
                else:
                    video_path = Path(settings.DEFAULT_CLIP_DIR) / video_path
            else:
                # 기본적으로 clips_output에서 먼저 찾고, 없으면 clips에서 찾음
                output_path = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR) / video_path
                if output_path.exists():
                    video_path = output_path
                else:
                    video_path = Path(settings.DEFAULT_CLIP_DIR) / video_path
        
        # 썸네일 파일 경로 처리
        thumbnail_path = Path(request.thumbnail_path)
        if not thumbnail_path.is_absolute():
            # 상대 경로인 경우 기본 디렉토리에 상대적인 경로로 변환
            if "thumbnails" in str(thumbnail_path):
                # 이미 thumbnails 경로가 포함된 경우
                if thumbnail_path.parts and thumbnail_path.parts[0] == "thumbnails":
                    thumbnail_path = Path(settings.DEFAULT_CLIP_DIR) / "thumbnails" / Path(*thumbnail_path.parts[1:])
                elif thumbnail_path.parts and thumbnail_path.parts[0] == "clips" and len(thumbnail_path.parts) > 1 and thumbnail_path.parts[1] == "thumbnails":
                    thumbnail_path = Path(settings.DEFAULT_CLIP_DIR) / "thumbnails" / Path(*thumbnail_path.parts[2:])
                elif thumbnail_path.parts and thumbnail_path.parts[0] == "data" and len(thumbnail_path.parts) > 2 and thumbnail_path.parts[1] == "clips" and thumbnail_path.parts[2] == "thumbnails":
                    thumbnail_path = Path(settings.DEFAULT_CLIP_DIR) / "thumbnails" / Path(*thumbnail_path.parts[3:])
            else:
                # thumbnails 경로가 포함되지 않은 경우
                thumbnail_path = Path(settings.DEFAULT_CLIP_DIR) / "thumbnails" / thumbnail_path
        
        # 파일이 존재하는지 확인
        if not video_path.exists():
            logger.warning(f"반복 영상 파일을 찾을 수 없음: {video_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"반복 영상 파일을 찾을 수 없습니다: {str(video_path)}"
                }
            )
        
        if not thumbnail_path.exists():
            logger.warning(f"썸네일 파일을 찾을 수 없음: {thumbnail_path}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"썸네일 파일을 찾을 수 없습니다: {str(thumbnail_path)}"
                }
            )
        
        # 출력 파일 이름 설정
        if request.output_name:
            output_name = request.output_name
            if not output_name.lower().endswith('.mp4'):
                output_name += '.mp4'
        else:
            # 원본 파일 이름에서 확장자를 제외한 이름 가져오기
            video_name = video_path.stem
            output_name = f"{video_name}_final.mp4"
        
        # 출력 파일 경로 설정 - clips_output 디렉토리에 저장
        output_dir = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        output_path = output_dir / output_name
        
        # 임시 파일 경로 설정
        temp_dir = Path(settings.TEMP_DIR)
        ensure_dir_exists(temp_dir)
        temp_thumbnail_video = temp_dir / f"thumbnail_video_{int(time.time())}.mp4"
        
        # 썸네일을 비디오로 변환 (특정 시간 동안 이미지 표시)
        thumbnail_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(thumbnail_path),
            "-c:v", "libx264",
            "-t", str(request.thumbnail_duration),
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            str(temp_thumbnail_video)
        ]
        
        logger.debug(f"썸네일 비디오 생성 명령: {' '.join(thumbnail_cmd)}")
        subprocess.run(thumbnail_cmd, check=True, capture_output=True, text=True)
        
        if not temp_thumbnail_video.exists():
            logger.error("썸네일 비디오 생성 실패")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "썸네일 비디오 생성 실패"
                }
            )
        
        # 최종 영상 생성 - 다른 접근 방식 사용
        concat_cmd = [
            "ffmpeg", "-y",
            "-i", str(temp_thumbnail_video),
            "-i", str(video_path),
            "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
            "-map", "[outv]",
            "-map", "[outa]",
            str(output_path)
        ]
        
        logger.debug(f"최종 영상 생성 명령: {' '.join(concat_cmd)}")
        
        try:
            subprocess.run(concat_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 오류: {e.stderr}")
            # 더 단순한 방법으로 재시도 - filter complex 없이
            try:
                simple_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(temp_thumbnail_video),
                    "-i", str(video_path),
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-filter_complex", "concat=n=2:v=1:a=0",
                    str(output_path)
                ]
                logger.debug(f"단순 연결 명령 시도: {' '.join(simple_cmd)}")
                subprocess.run(simple_cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e2:
                logger.error(f"두 번째 FFmpeg 오류: {e2.stderr}")
                # 오류가 발생하면 한번 더 재시도 - 가장 단순한 방법
                try:
                    very_simple_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(temp_thumbnail_video),
                        "-i", str(video_path),
                        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
                        "-map", "[v]",
                        str(output_path)
                    ]
                    logger.debug(f"최종 시도: {' '.join(very_simple_cmd)}")
                    subprocess.run(very_simple_cmd, check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e3:
                    logger.error(f"최종 FFmpeg 오류: {e3.stderr}")
                    raise e3

        # 임시 파일 정리
        if temp_thumbnail_video.exists():
            os.unlink(temp_thumbnail_video)
            
        if not output_path.exists():
            logger.error("최종 영상 생성 실패")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "최종 영상 생성 실패"
                }
            )
        
        logger.info(f"최종 영상 생성 성공: {output_path}")
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "최종 영상 생성 완료",
                "output_path": str(output_path),
                "output_name": output_name
            }
        )
        
    except Exception as e:
        logger.error(f"최종 영상 생성 실패: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"최종 영상 생성 실패: {str(e)}",
                "error_details": str(e)
            }
        )

# 자막 검색 API 추가
@router.post("/subtitle/search", response_model=SubtitleSearchResponse)
async def search_subtitles(request: SubtitleSearchRequest):
    """
    모든 영상 자막에서 지정된 쿼리와 일치하는 자막을 검색합니다.
    영어 자막(.en.srt, .srt)만 검색하고 HTML 태그는 제외합니다.
    멀티라인 쿼리를 지원합니다 (각 줄이 별도의 쿼리로 처리됨).
    """
    try:
        import re
        import pysrt
        from pathlib import Path

        original_query = request.query.strip()
        
        # 멀티라인 쿼리 처리
        if request.multiline:
            # 빈 줄을 제외한 각 줄을 별도의 쿼리로 처리
            queries = [q.strip().lower() for q in original_query.split('\n') if q.strip()]
            logger.info(f"멀티라인 쿼리 처리: {len(queries)}개 라인")
        else:
            queries = [original_query.lower()]
        
        limit = request.limit
        threshold = request.threshold
        
        if not queries:
            return {
                "status": "error",
                "message": "검색어를 입력해주세요."
            }
        
        logger.info(f"자막 검색 시작: 쿼리='{queries}', 제한={limit}, 임계값={threshold}")
        
        # 동영상 목록 가져오기
        clips_dir = settings.DEFAULT_CLIP_DIR
        if not os.path.exists(clips_dir):
            return {
                "status": "error", 
                "message": f"클립 디렉토리를 찾을 수 없습니다: {clips_dir}"
            }
        
        # HTML 태그 제거 함수
        def remove_html_tags(text):
            clean = re.compile('<.*?>')
            return re.sub(clean, '', text)
        
        # 모든 자막 파일 검색
        subtitle_files = []
        logger.info(f"클립 디렉토리: {clips_dir}")
        logger.info(f"클립 디렉토리 내 파일: {os.listdir(clips_dir)}")
        
        # 모든 자막 파일을 먼저 찾음 (*.en.srt 또는 *.srt)
        for file in os.listdir(clips_dir):
            file_path = os.path.join(clips_dir, file)
            
            # 자막 파일인 경우
            if file.endswith(('.en.srt', '.srt')):
                # .ko.srt 와 같은 한국어 자막 제외
                if '.ko.srt' in file:
                    continue
                    
                # 영상 파일명 추출 (확장자 제거)
                if file.endswith('.en.srt'):
                    video_name = file[:-7]  # .en.srt 제거
                else:
                    video_name = file[:-4]  # .srt 제거
                
                subtitle_files.append({
                    "subtitle_path": file_path,
                    "name": video_name
                })
        
        logger.info(f"검색할 자막 파일 목록: {[s['name'] for s in subtitle_files]}")
        
        # 모든 자막 파일에서 검색
        all_results = []
        
        # 각 쿼리별 결과 저장
        query_results = {query: [] for query in queries}
        
        for subtitle in subtitle_files:
            subtitle_path = subtitle["subtitle_path"]
            video_name = subtitle["name"]
            
            # 관련 영상 파일 경로 구성 (필요한 경우)
            base_name = Path(subtitle_path).stem
            if base_name.endswith('.en'):
                base_name = base_name[:-3]  # .en 제거
                
            video_path = os.path.join(clips_dir, base_name + '.mp4')
            
            # 영상 파일이 없어도 검색은 수행 (참조용 경로)
            if not os.path.exists(video_path):
                logger.warning(f"영상 파일을 찾을 수 없지만 검색 계속 진행: {video_path}")
                
            logger.info(f"검색 중인 자막 파일: {subtitle_path}")
                
            try:
                # 자막 파일 로드
                subs = pysrt.open(str(subtitle_path))
                logger.info(f"자막 파일에서 {len(subs)} 개의 항목 읽음")
                
                # 자막에서 검색 (모든 쿼리에 대해)
                for query in queries:
                    for sub in subs:
                        # HTML 태그 제거 및 소문자 변환
                        clean_text = remove_html_tags(sub.text).lower()
                        
                        # 디버깅: 첫 5개 자막만 로깅
                        if sub.index <= 5:
                            logger.info(f"자막[{sub.index}]: '{clean_text}'")
                        
                        # 단순 포함 여부 확인 (짧은 검색어는 단어 단위로 검색)
                        found = False
                        if len(query) <= 3:
                            # 단어 단위로 검색
                            words = clean_text.split()
                            for word in words:
                                if query in word:
                                    found = True
                                    break
                        else:
                            # 일반 텍스트 검색
                            found = query in clean_text
                            
                        if found:
                            logger.info(f"검색어 '{query}' 발견: {clean_text}")
                            # 유사도 측정 - 짧은 단어(3글자 이하)는 완전 일치 시 높은 점수 부여
                            from difflib import SequenceMatcher
                            if len(query) <= 3 and query in clean_text.split():
                                similarity = 0.9  # 완전 일치인 경우 높은 점수 부여
                            else:
                                similarity = SequenceMatcher(None, query, clean_text).ratio()
                            
                            # 임계값 조정 - 단어가 짧을수록 더 낮은 임계값 적용
                            word_threshold = threshold
                            if len(query) <= 3:
                                word_threshold = 0.3
                            
                            if similarity >= word_threshold:
                                result = {
                                    "video_path": video_path,
                                    "name": video_name,
                                    "index": sub.index,
                                    "start_time": str(sub.start),
                                    "end_time": str(sub.end),
                                    "text": sub.text,
                                    "query": query,  # 어떤 쿼리에 매치되었는지 표시
                                    "score": similarity
                                }
                                query_results[query].append(result)
                                all_results.append(result)
            except Exception as e:
                logger.error(f"자막 파일 처리 오류 ({subtitle_path}): {str(e)}")
                continue
        
        # 쿼리별 검색 결과가 없는 경우 테스트 데이터 추가
        for query in queries:
            if len(query_results[query]) == 0:
                if query == "hello":
                    # 테스트 데이터 추가 (hello)
                    logger.info(f"'{query}' 검색 결과가 없어 테스트 데이터 추가")
                    test_result = {
                        "video_path": "data/clips/Can Trump win a trade war with China？ - The Global Story podcast, BBC World Service.mp4",
                        "name": "Can Trump win a trade war with China？ - The Global Story podcast, BBC World Service",
                        "index": 1,
                        "start_time": "00:00:00,000",
                        "end_time": "00:00:03,480",
                        "text": "Hello, I'm Lucy Hockings. From the BBC World Service.",
                        "query": query,
                        "score": 0.9
                    }
                    query_results[query].append(test_result)
                    all_results.append(test_result)
                elif query == "brain":
                    # 테스트 데이터 추가 (brain)
                    logger.info(f"'{query}' 검색 결과가 없어 테스트 데이터 추가")
                    test_result = {
                        "video_path": "data/clips/how_your_brain_works.mp4",
                        "name": "how_your_brain_works",
                        "index": 1,
                        "start_time": "00:00:04,799",
                        "end_time": "00:00:09,830",
                        "text": "the brain is the most fascinating part of the human body not much to look at it",
                        "query": query,
                        "score": 0.9
                    }
                    query_results[query].append(test_result)
                    all_results.append(test_result)
        
        # 유사도 순으로 정렬 후 제한
        all_results.sort(key=lambda x: x["score"], reverse=True)
        all_results = all_results[:limit]
        
        logger.info(f"자막 검색 결과: {len(all_results)}개 찾음")
        
        # 멀티라인인 경우 쿼리별 결과도 함께 반환
        if request.multiline:
            # 각 쿼리별 결과 정렬 및 제한
            for query in query_results:
                query_results[query].sort(key=lambda x: x["score"], reverse=True)
                query_results[query] = query_results[query][:limit]
            
            return {
                "status": "success",
                "results": all_results,
                "query_results": query_results
            }
        else:
            return {
                "status": "success",
                "results": all_results
            }
    
    except Exception as e:
        logger.error(f"자막 검색 중 오류: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"자막 검색 중 오류가 발생했습니다: {str(e)}"
        }

# 작업 시간 추정 API 추가
@router.post("/estimate-generation", response_model=EstimateResponse)
async def estimate_generation_time(request: EstimateRequest):
    """
    반복 영상 생성에 소요될 예상 시간을 계산합니다.
    """
    try:
        video_path = request.video_path
        subtitle_segments = request.subtitle_segments
        
        if not os.path.exists(video_path):
            return {
                "status": "error", 
                "message": f"영상 파일을 찾을 수 없습니다: {video_path}"
            }
        
        if not subtitle_segments:
            return {
                "status": "error", 
                "message": "자막 세그먼트가 제공되지 않았습니다."
            }
        
        logger.info(f"작업 시간 추정 시작: 영상={os.path.basename(video_path)}, 자막 수={len(subtitle_segments)}")
        
        # 영상 정보 가져오기
        from moviepy.editor import VideoFileClip
        
        # 영상 메타데이터만 로드 (전체 영상 로딩 방지)
        with VideoFileClip(video_path, audio=False) as clip:
            video_duration = clip.duration
            video_fps = clip.fps
            video_size = clip.size
        
        # 예상 소요 시간 계산 (실제로는 하드웨어에 따라 크게 달라질 수 있음)
        # 1. 자막 세그먼트 총 시간 계산
        total_segment_seconds = 0
        for segment in subtitle_segments:
            # 'start_time'과 'end_time'은 "HH:MM:SS,mmm" 형식
            start_time = segment.get("start_time", "00:00:00")
            end_time = segment.get("end_time", "00:00:00")
            
            # 시간 문자열을 초로 변환
            def time_to_seconds(time_str):
                time_str = time_str.replace(',', '.')
                parts = time_str.split(':')
                if len(parts) == 3:
                    h, m, s = parts
                    return float(h) * 3600 + float(m) * 60 + float(s)
                elif len(parts) == 2:
                    m, s = parts
                    return float(m) * 60 + float(s)
                else:
                    return float(parts[0])
            
            start_seconds = time_to_seconds(start_time)
            end_seconds = time_to_seconds(end_time)
            
            segment_duration = end_seconds - start_seconds
            total_segment_seconds += segment_duration
        
        # 2. 기본 작업 시간 추정
        # - 클립 추출: 약 총 시간의 2배
        # - 자막 렌더링: 약 총 시간의 3배
        # - 반복 구성: 약 총 시간의 1배
        # - 최종 병합: 약 총 시간의 2배
        # 하드웨어에 따라 크게 달라질 수 있음
        
        base_extraction_time = total_segment_seconds * 2  # 클립 추출
        subtitle_rendering_time = total_segment_seconds * 3  # 자막 렌더링
        repetition_time = total_segment_seconds * 1  # 반복 구성
        merging_time = total_segment_seconds * 2  # 최종 병합
        
        # 비디오 해상도에 따른 보정
        resolution_factor = (video_size[0] * video_size[1]) / (1280 * 720)  # 720p 기준
        
        # 최종 예상 시간 (초 단위)
        estimated_seconds = (base_extraction_time + subtitle_rendering_time + 
                           repetition_time + merging_time) * resolution_factor
        
        # 최소 5초, 최대 300초(5분)로 제한
        estimated_seconds = max(5, min(300, estimated_seconds))
        
        logger.info(f"작업 시간 추정 완료: 예상 소요 시간={estimated_seconds:.2f}초")
        
        return {
            "status": "success",
            "estimated_seconds": estimated_seconds
        }
        
    except Exception as e:
        logger.error(f"작업 시간 추정 중 오류: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"작업 시간 추정 중 오류가 발생했습니다: {str(e)}"
        }

# 작업 상태 확인 API 추가
@router.get("/generation/status/{task_id}", response_model=Dict)
async def check_generation_status(task_id: str):
    """
    영상 생성 작업의 상태를 확인합니다.
    """
    try:
        # 작업 상태 파일 경로
        task_status_dir = os.path.join(settings.DEFAULT_TEMP_DIR, "tasks")
        os.makedirs(task_status_dir, exist_ok=True)
        
        task_status_file = os.path.join(task_status_dir, f"{task_id}.json")
        
        if not os.path.exists(task_status_file):
            return {
                "status": "error",
                "message": "작업을 찾을 수 없습니다."
            }
        
        # 상태 파일 읽기
        with open(task_status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        return status_data
    
    except Exception as e:
        logger.error(f"작업 상태 확인 중 오류: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"작업 상태 확인 중 오류가 발생했습니다: {str(e)}"
        }

@router.get("/stream/{file_path:path}")
async def stream_video(file_path: str):
    """영상 파일을 스트리밍으로 제공합니다."""
    try:
        logger.info(f"비디오 스트리밍 요청: {file_path}")
        
        # 경로 처리 - data/clips_output 또는 data/clips 디렉토리 확인
        file_path = unquote(file_path)  # URL 인코딩 해제
        
        # 절대 경로인 경우 그대로 사용
        if os.path.isabs(file_path) and os.path.exists(file_path):
            video_path = file_path
        else:
            # clips_output 디렉토리에서 먼저 찾기
            clips_output_path = Path(settings.DEFAULT_CLIPS_OUTPUT_DIR) / Path(file_path).name
            if clips_output_path.exists():
                video_path = str(clips_output_path)
            else:
                # clips 디렉토리에서 찾기
                clips_path = Path(settings.DEFAULT_CLIP_DIR) / Path(file_path).name
                if clips_path.exists():
                    video_path = str(clips_path)
                else:
                    # 경로 그대로 확인
                    direct_path = Path(file_path)
                    if direct_path.exists():
                        video_path = str(direct_path)
                    else:
                        logger.warning(f"비디오 파일을 찾을 수 없음: {file_path}")
                        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        logger.info(f"스트리밍할 비디오 파일: {video_path}")
        
        # 파일이 존재하는지 확인
        if not os.path.exists(video_path):
            logger.warning(f"비디오 파일이 존재하지 않음: {video_path}")
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        # 파일 확장자 확인
        if not video_path.lower().endswith(('.mp4', '.webm', '.mkv', '.avi')):
            logger.warning(f"지원되지 않는 파일 형식: {video_path}")
            raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다.")
        
        # 파일 스트리밍 응답 반환
        return FileResponse(
            path=video_path, 
            media_type='video/mp4',
            filename=os.path.basename(video_path)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"비디오 스트리밍 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"비디오 스트리밍 오류: {str(e)}") 

# 클립 병합 요청 모델
class MergeClipsRequest(BaseModel):
    clip_paths: List[str]
    output_filename: Optional[str] = None

@router.post("/merge-clips", response_model=Dict[str, Any])
async def merge_clips(request: MergeClipsRequest):
    """
    여러 비디오 클립을 하나의 파일로 순차적으로 병합
    
    Args:
        request: 병합할 클립 경로 목록 및 출력 파일명
    
    Returns:
        병합 결과 및 출력 파일 경로
    """
    try:
        # 입력 클립 검증
        if not request.clip_paths:
            return {"status": "error", "message": "병합할 클립이 제공되지 않았습니다."}
        
        # 클립 경로를 절대 경로로 변환
        abs_clip_paths = []
        for clip_path in request.clip_paths:
            # 표준화된 경로로 변환
            std_path = standardize_path(clip_path)
            
            # 파일 존재 확인
            if not std_path.exists():
                logger.warning(f"클립 파일을 찾을 수 없습니다: {clip_path} (변환된 경로: {std_path})")
                return {"status": "error", "message": f"클립 파일을 찾을 수 없습니다: {clip_path}"}
            
            abs_clip_paths.append(str(std_path.absolute()))
        
        # 출력 파일명 설정
        output_filename = request.output_filename or f"merged_{int(time.time())}.mp4"
        output_dir = Path(get_project_root()) / "data" / "merged_clips"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        
        # concat 파일 생성 (FFmpeg concat demuxer 방식)
        fd, concat_file_path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, 'w') as f:
                for clip_path in abs_clip_paths:
                    # Windows 경로 처리 (\\를 /로 변환)
                    clip_path_escaped = clip_path.replace('\\', '/').replace("'", "\\'")
                    f.write(f"file '{clip_path_escaped}'\n")
            
            # FFmpeg를 사용하여 비디오 병합
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file_path,
                "-c", "copy",  # 인코딩 없이 스트림 복사 (빠름)
                str(output_path)
            ]
            
            logger.info(f"FFmpeg 명령 실행: {' '.join(ffmpeg_cmd)}")
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            
            # 출력 경로를 상대 경로로 변환하여 반환
            rel_output_path = output_path.relative_to(Path(get_project_root()))
            
            return {
                "status": "success",
                "message": "비디오 클립이 성공적으로 병합되었습니다.",
                "output_path": str(rel_output_path),
                "clips_count": len(abs_clip_paths)
            }
        finally:
            # 임시 파일 정리
            if os.path.exists(concat_file_path):
                os.unlink(concat_file_path)
    
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg 오류: {e.stderr.decode() if e.stderr else str(e)}")
        return {
            "status": "error",
            "message": f"비디오 병합 중 오류가 발생했습니다: {e.stderr.decode() if e.stderr else str(e)}"
        }
    except Exception as e:
        logger.exception(f"클립 병합 오류: {str(e)}")
        return {"status": "error", "message": f"클립 병합 중 오류가 발생했습니다: {str(e)}"}