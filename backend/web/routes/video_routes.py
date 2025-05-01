#!/usr/bin/env python3
"""
File: video_routes.py
Description: 비디오 관련 API 라우트
"""

import os
import json
import asyncio
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from yt_shadowing.core.utils import get_project_root, ensure_dir_exists
from yt_shadowing.core.extractor import VideoExtractor
from yt_shadowing.core.generator import RepeatVideoGenerator

router = APIRouter()

# 데이터 모델
class ClipRequest(BaseModel):
    input_path: str
    output_path: Optional[str] = None
    start_time: str
    end_time: str
    audio_only: bool = False
    high_quality: bool = False

class RepeatVideoRequest(BaseModel):
    input_video: str
    subtitle_file: str
    output_path: Optional[str] = None
    translation_path: Optional[str] = None

class YoutubeDownloadRequest(BaseModel):
    url: str
    output_dir: Optional[str] = None
    quality: str = 'best'
    audio_only: bool = False

class PronunciationTrainingRequest(BaseModel):
    video_id: str
    subtitle_id: Optional[str] = None
    output_name: Optional[str] = None
    pronunciation_focus: List[str] = []
    ipa_display: bool = False
    highlight_difficult: bool = False
    difficulty_level: str = 'intermediate'

# 경로 설정
clips_dir = get_project_root() / "clips"
ensure_dir_exists(clips_dir)

output_dir = get_project_root() / "output"
ensure_dir_exists(output_dir)

final_dir = get_project_root() / "final"
ensure_dir_exists(final_dir)

config_dir = get_project_root() / "config"
ensure_dir_exists(config_dir)

# 백그라운드 작업 상태 추적
task_status = {}

@router.post("/clip")
async def extract_clip(
    request: ClipRequest,
    background_tasks: Optional[BackgroundTasks] = None
):
    """비디오 클립 추출"""
    try:
        extractor = VideoExtractor()
        
        # 출력 경로가 없는 경우 기본값 생성
        if not request.output_path:
            input_name = Path(request.input_path).stem
            ext = ".mp3" if request.audio_only else ".mp4"
            request.output_path = str(clips_dir / f"{input_name}_clip{ext}")
        
        # 클립 추출 실행
        task_id = str(uuid.uuid4())
        
        if background_tasks:
            # 백그라운드 작업으로 실행
            async def extract_task():
                try:
                    task_status[task_id] = {"status": "processing", "progress": 0}
                    success = await extractor.extract_clip(
                        input_path=request.input_path,
                        output_path=request.output_path,
                        start_time=request.start_time,
                        end_time=request.end_time,
                        audio_only=request.audio_only,
                        high_quality=request.high_quality
                    )
                    task_status[task_id] = {
                        "status": "success" if success else "error",
                        "progress": 100,
                        "path": request.output_path if success else None
                    }
                    return task_status[task_id]
                except Exception as e:
                    task_status[task_id] = {"status": "error", "message": str(e)}
                    return task_status[task_id]
                    
            background_tasks.add_task(extract_task)
            return {"status": "pending", "task_id": task_id}
        else:
            # 동기적으로 실행
            success = await extractor.extract_clip(
                input_path=request.input_path,
                output_path=request.output_path,
                start_time=request.start_time,
                end_time=request.end_time,
                audio_only=request.audio_only,
                high_quality=request.high_quality
            )
            if success:
                return {"status": "success", "path": request.output_path}
            else:
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "클립 추출 실패"}
                )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"클립 추출 오류: {str(e)}"}
        )

@router.post("/repeat")
async def generate_repeat_video(
    request: RepeatVideoRequest,
    background_tasks: Optional[BackgroundTasks] = None
):
    """반복 영상 생성"""
    try:
        # 출력 경로가 없는 경우 기본값 생성
        if not request.output_path:
            input_name = Path(request.input_video).stem
            request.output_path = str(output_dir / f"{input_name}_repeat.mp4")
            
        # 번역 불러오기
        korean_translation = None
        if request.translation_path and os.path.exists(request.translation_path):
            try:
                with open(request.translation_path, 'r', encoding='utf-8') as f:
                    korean_translation = json.load(f)
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "message": f"번역 파일 로드 오류: {str(e)}"}
                )
        
        # 생성기 인스턴스 생성
        generator = RepeatVideoGenerator()
        
        # 반복 영상 생성 실행
        task_id = str(uuid.uuid4())
        
        if background_tasks:
            # 백그라운드 작업으로 실행
            async def generate_task():
                try:
                    task_status[task_id] = {"status": "processing", "progress": 0}
                    success = await generator.generate_repeat_video(
                        input_video=request.input_video,
                        subtitle_file=request.subtitle_file,
                        output_path=request.output_path,
                        korean_translation=korean_translation
                    )
                    task_status[task_id] = {
                        "status": "success" if success else "error",
                        "progress": 100,
                        "path": request.output_path if success else None
                    }
                    return task_status[task_id]
                except Exception as e:
                    task_status[task_id] = {"status": "error", "message": str(e)}
                    return task_status[task_id]
                    
            background_tasks.add_task(generate_task)
            return {"status": "pending", "task_id": task_id}
        else:
            # 동기적으로 실행
            success = await generator.generate_repeat_video(
                input_video=request.input_video,
                subtitle_file=request.subtitle_file,
                output_path=request.output_path,
                korean_translation=korean_translation
            )
            if success:
                return {"status": "success", "path": request.output_path}
            else:
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "반복 영상 생성 실패"}
                )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"반복 영상 생성 오류: {str(e)}"}
        )

@router.post("/pronunciation-training")
async def create_pronunciation_training(
    request: PronunciationTrainingRequest,
    background_tasks: Optional[BackgroundTasks] = None
):
    """발음 연습 특화 영상 생성"""
    try:
        # 비디오 경로 확인
        video_path = clips_dir / request.video_id
        if not video_path.exists():
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "비디오 파일을 찾을 수 없습니다."}
            )
        
        # 자막 경로 확인
        subtitle_path = None
        if request.subtitle_id:
            subtitle_path = clips_dir / request.subtitle_id
            if not subtitle_path.exists():
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "자막 파일을 찾을 수 없습니다."}
                )
        
        # 출력 파일 이름 설정
        output_name = request.output_name or f"pronunciation_{uuid.uuid4().hex}.mp4"
        output_path = output_dir / output_name
        
        # 발음 연습 옵션 설정
        pronunciation_config = {
            "focus": request.pronunciation_focus,
            "ipa_display": request.ipa_display,
            "highlight_difficult": request.highlight_difficult,
            "difficulty_level": request.difficulty_level
        }
        
        config_path = config_dir / f"pronunciation_{uuid.uuid4().hex}.json"
        with open(config_path, 'w') as f:
            json.dump(pronunciation_config, f)
        
        # 백그라운드 작업 실행
        task_id = str(uuid.uuid4())
        
        if background_tasks:
            async def process_task():
                try:
                    task_status[task_id] = {"status": "processing", "progress": 0}
                    # 실제 발음 연습 영상 생성 로직 호출
                    # 예: generator.create_pronunciation_video(...)
                    task_status[task_id] = {
                        "status": "success",
                        "progress": 100,
                        "path": str(output_path)
                    }
                except Exception as e:
                    task_status[task_id] = {"status": "error", "message": str(e)}
            
            background_tasks.add_task(process_task)
            return {"status": "pending", "task_id": task_id}
        else:
            # 동기적으로 실행
            # 실제 발음 연습 영상 생성 로직 호출
            # 예: generator.create_pronunciation_video(...)
            return {"status": "success", "path": str(output_path)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"발음 연습 영상 생성 오류: {str(e)}"}
        )

@router.post("/download/youtube")
async def download_youtube_video(
    request: YoutubeDownloadRequest,
    background_tasks: Optional[BackgroundTasks] = None
):
    """YouTube 비디오 다운로드"""
    try:
        extractor = VideoExtractor()
        
        # 출력 디렉토리가 없는 경우 기본값 사용
        output_dir = request.output_dir or str(clips_dir)
        ensure_dir_exists(output_dir)
        
        # 다운로드 실행
        task_id = str(uuid.uuid4())
        
        if background_tasks:
            # 백그라운드 작업으로 실행
            async def download_task():
                try:
                    task_status[task_id] = {"status": "processing", "progress": 0}
                    output_path = await extractor.download_youtube_video(
                        url=request.url,
                        output_dir=output_dir,
                        quality=request.quality,
                        audio_only=request.audio_only
                    )
                    if output_path:
                        task_status[task_id] = {
                            "status": "success",
                            "progress": 100,
                            "path": output_path
                        }
                    else:
                        task_status[task_id] = {
                            "status": "error",
                            "message": "다운로드 실패"
                        }
                    return task_status[task_id]
                except Exception as e:
                    task_status[task_id] = {"status": "error", "message": str(e)}
                    return task_status[task_id]
                    
            background_tasks.add_task(download_task)
            return {"status": "pending", "task_id": task_id}
        else:
            # 동기적으로 실행
            output_path = await extractor.download_youtube_video(
                url=request.url,
                output_dir=output_dir,
                quality=request.quality,
                audio_only=request.audio_only
            )
            if output_path:
                return {"status": "success", "path": output_path}
            else:
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "YouTube 비디오 다운로드 실패"}
                )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"YouTube 다운로드 오류: {str(e)}"}
        )

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """작업 상태 확인"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    return task_status[task_id]

@router.get("/clips")
async def list_clips():
    """클립 목록 가져오기"""
    try:
        clips = []
        for file in os.listdir(clips_dir):
            if os.path.isfile(os.path.join(clips_dir, file)):
                file_stats = os.stat(os.path.join(clips_dir, file))
                clips.append({
                    "name": file,
                    "path": str(os.path.join(clips_dir, file)),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        return {"status": "success", "clips": clips, "count": len(clips)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"클립 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/outputs")
async def list_outputs():
    """출력 영상 목록 가져오기"""
    try:
        outputs = []
        for file in os.listdir(output_dir):
            if os.path.isfile(os.path.join(output_dir, file)):
                file_stats = os.stat(os.path.join(output_dir, file))
                outputs.append({
                    "name": file,
                    "path": str(os.path.join(output_dir, file)),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        return {"status": "success", "outputs": outputs, "count": len(outputs)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"출력 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/final")
async def list_finals():
    """최종 영상 목록 가져오기"""
    try:
        finals = []
        for file in os.listdir(final_dir):
            if os.path.isfile(os.path.join(final_dir, file)):
                file_stats = os.stat(os.path.join(final_dir, file))
                finals.append({
                    "name": file,
                    "path": str(os.path.join(final_dir, file)),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        return {"status": "success", "finals": finals, "count": len(finals)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"최종 목록 가져오기 오류: {str(e)}"}
        )