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
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel

# 코어 모듈 임포트 (경로 수정)
from backend.core.utils import get_project_root, ensure_dir_exists, setup_logger
from backend.core.extractor import VideoExtractor
from backend.core.generator import RepeatVideoGenerator

router = APIRouter()

# 로거 설정
logger = setup_logger('video_routes', 'video_routes.log')

# 데이터 모델
class VideoExtractRequest(BaseModel):
    url: Optional[str] = None
    input_path: Optional[str] = None
    start: str
    end: str
    output_path: Optional[str] = None
    subtitle_only: bool = False

class RepeatVideoRequest(BaseModel):
    video_path: str
    subtitle_path: Optional[str] = None
    translation_path: Optional[str] = None
    output_path: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    
# 경로 설정 - 백엔드 데이터 디렉토리로 변경
data_dir = Path(__file__).parent.parent.parent / "data"
clips_dir = data_dir / "clips"
ensure_dir_exists(clips_dir)

output_dir = data_dir / "output"
ensure_dir_exists(output_dir)

final_dir = data_dir / "final"
ensure_dir_exists(final_dir)

# 진행 상태 추적용 딕셔너리
task_status = {}

@router.post("/extract")
async def extract_video(request: VideoExtractRequest, background_tasks: BackgroundTasks):
    """비디오 클립 추출"""
    try:
        logger.info("비디오 추출 요청")
        
        # 파라미터 검증
        if not request.url and not request.input_path:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "URL 또는 입력 경로가 필요합니다"}
            )
        
        # 추출기 초기화
        extractor = VideoExtractor()
        
        # 출력 경로 설정
        if not request.output_path:
            if request.url:
                # URL에서 비디오 ID 추출
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(request.url)
                video_id = "video"
                if 'youtube.com' in parsed_url.netloc:
                    query_params = parse_qs(parsed_url.query)
                    video_id = query_params.get('v', ['video'])[0]
                elif 'youtu.be' in parsed_url.netloc:
                    video_id = parsed_url.path.lstrip('/')
                    
                request.output_path = str(clips_dir / f"{video_id}_clip.mp4")
            else:
                input_name = Path(request.input_path).stem
                request.output_path = str(clips_dir / f"{input_name}_clip.mp4")
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "state": "PENDING",
            "progress": 0,
            "status": "비디오 추출 준비 중"
        }
        
        # 백그라운드 작업으로 처리
        async def extract_task():
            try:
                task_status[task_id]["state"] = "PROGRESS"
                task_status[task_id]["status"] = "비디오 다운로드 중"
                task_status[task_id]["progress"] = 10
                
                if request.url:
                    # URL에서 추출
                    temp_path = await extractor.download_youtube(request.url)
                    task_status[task_id]["status"] = "비디오 추출 중"
                    task_status[task_id]["progress"] = 40
                    
                    if request.subtitle_only:
                        # 자막만 추출
                        subtitle_path = await extractor.extract_subtitle(temp_path)
                        task_status[task_id]["status"] = "완료"
                        task_status[task_id]["progress"] = 100
                        task_status[task_id]["state"] = "SUCCESS"
                        task_status[task_id]["result"] = {"subtitle_path": subtitle_path}
                    else:
                        # 비디오 클립 추출
                        clip_path = await extractor.extract_video_clip(
                            temp_path, request.start, request.end, request.output_path
                        )
                        task_status[task_id]["status"] = "완료"
                        task_status[task_id]["progress"] = 100
                        task_status[task_id]["state"] = "SUCCESS"
                        task_status[task_id]["result"] = {"clip_path": clip_path}
                else:
                    # 로컬 파일에서 추출
                    if request.subtitle_only:
                        # 자막만 추출
                        subtitle_path = await extractor.extract_subtitle(request.input_path)
                        task_status[task_id]["status"] = "완료"
                        task_status[task_id]["progress"] = 100
                        task_status[task_id]["state"] = "SUCCESS"
                        task_status[task_id]["result"] = {"subtitle_path": subtitle_path}
                    else:
                        # 비디오 클립 추출
                        task_status[task_id]["status"] = "비디오 추출 중"
                        task_status[task_id]["progress"] = 40
                        
                        clip_path = await extractor.extract_video_clip(
                            request.input_path, request.start, request.end, request.output_path
                        )
                        task_status[task_id]["status"] = "완료"
                        task_status[task_id]["progress"] = 100
                        task_status[task_id]["state"] = "SUCCESS"
                        task_status[task_id]["result"] = {"clip_path": clip_path}
            except Exception as e:
                logger.error(f"비디오 추출 작업 오류: {str(e)}")
                task_status[task_id]["state"] = "FAILURE"
                task_status[task_id]["status"] = f"오류: {str(e)}"
                task_status[task_id]["error"] = str(e)
                
        background_tasks.add_task(extract_task)
        
        return {"status": "pending", "task_id": task_id}
    except Exception as e:
        logger.error(f"비디오 추출 요청 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"비디오 추출 오류: {str(e)}"}
        )

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """작업 상태 확인"""
    if task_id not in task_status:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "작업을 찾을 수 없습니다"}
        )
    return task_status[task_id]

@router.post("/generate-repeat")
async def generate_repeat_video(
    video_path: str = Form(...),
    subtitle_path: Optional[str] = Form(None),
    translation_path: Optional[str] = Form(None),
    output_path: Optional[str] = Form(None),
    repeat_count: int = Form(3),
    background_tasks: BackgroundTasks = None
):
    """반복 영상 생성"""
    try:
        logger.info(f"반복 영상 생성 요청: {video_path}")
        
        # 반복 비디오 생성기 초기화
        generator = RepeatVideoGenerator()
        
        # 출력 경로 설정
        if not output_path:
            video_name = Path(video_path).stem
            output_path = str(output_dir / f"{video_name}_repeat.mp4")
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "state": "PENDING",
            "progress": 0,
            "status": "반복 영상 생성 준비 중"
        }
        
        # 백그라운드 작업으로 처리
        async def generate_task():
            try:
                task_status[task_id]["state"] = "PROGRESS"
                task_status[task_id]["status"] = "설정 로드 중"
                task_status[task_id]["progress"] = 5
                
                # 설정 로드
                config = generator.load_config()
                
                # 반복 횟수 설정
                config["repeat_count"] = repeat_count
                
                task_status[task_id]["status"] = "반복 영상 생성 중"
                task_status[task_id]["progress"] = 20
                
                # 반복 영상 생성
                result = await generator.generate_repeat_video(
                    video_path, subtitle_path, translation_path, output_path, config
                )
                
                if result:
                    task_status[task_id]["state"] = "SUCCESS"
                    task_status[task_id]["status"] = "완료"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["result"] = {"output_path": output_path}
                else:
                    task_status[task_id]["state"] = "FAILURE"
                    task_status[task_id]["status"] = "반복 영상 생성 실패"
                    task_status[task_id]["error"] = "영상 생성 중 오류가 발생했습니다"
            except Exception as e:
                logger.error(f"반복 영상 생성 작업 오류: {str(e)}")
                task_status[task_id]["state"] = "FAILURE"
                task_status[task_id]["status"] = f"오류: {str(e)}"
                task_status[task_id]["error"] = str(e)
                
        background_tasks.add_task(generate_task)
        
        return {"status": "pending", "task_id": task_id}
    except Exception as e:
        logger.error(f"반복 영상 생성 요청 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"반복 영상 생성 오류: {str(e)}"}
        )

@router.post("/merge-final")
async def merge_final_video(
    segments_path: str = Form(...),
    output_path: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    watermark: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """최종 영상 병합"""
    try:
        logger.info(f"최종 영상 병합 요청: {segments_path}")
        
        # 출력 경로 설정
        if not output_path:
            segments_name = Path(segments_path).stem
            output_path = str(final_dir / f"{segments_name}_final.mp4")
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "state": "PENDING",
            "progress": 0,
            "status": "최종 영상 병합 준비 중"
        }
        
        # 백그라운드 작업으로 처리
        async def merge_task():
            try:
                from backend.core.generator import FinalVideoMerger
                
                task_status[task_id]["state"] = "PROGRESS"
                task_status[task_id]["status"] = "영상 병합 중"
                task_status[task_id]["progress"] = 20
                
                # 병합기 초기화
                merger = FinalVideoMerger()
                
                # 병합 수행
                result = await merger.merge_final_video(
                    segments_path, output_path, title, watermark
                )
                
                if result:
                    task_status[task_id]["state"] = "SUCCESS"
                    task_status[task_id]["status"] = "완료"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["result"] = {"output_path": output_path}
                else:
                    task_status[task_id]["state"] = "FAILURE"
                    task_status[task_id]["status"] = "영상 병합 실패"
                    task_status[task_id]["error"] = "영상 병합 중 오류가 발생했습니다"
            except Exception as e:
                logger.error(f"최종 영상 병합 작업 오류: {str(e)}")
                task_status[task_id]["state"] = "FAILURE"
                task_status[task_id]["status"] = f"오류: {str(e)}"
                task_status[task_id]["error"] = str(e)
                
        background_tasks.add_task(merge_task)
        
        return {"status": "pending", "task_id": task_id}
    except Exception as e:
        logger.error(f"최종 영상 병합 요청 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"최종 영상 병합 오류: {str(e)}"}
        )

@router.get("/stream/{file_path:path}")
async def stream_video(file_path: str):
    """비디오 스트리밍"""
    try:
        logger.info(f"비디오 스트리밍 요청: {file_path}")
        
        # 파일 경로 검증
        if not os.path.exists(file_path):
            # data_dir에서 찾기 시도
            data_file_path = data_dir / file_path
            if not data_file_path.exists():
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "파일을 찾을 수 없습니다"}
                )
            file_path = str(data_file_path)
        
        # 파일 스트리밍
        return FileResponse(
            file_path, 
            media_type="video/mp4",
            filename=os.path.basename(file_path)
        )
    except Exception as e:
        logger.error(f"비디오 스트리밍 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"비디오 스트리밍 오류: {str(e)}"}
        )

@router.get("/clips")
async def list_clips():
    """클립 목록 가져오기"""
    try:
        logger.info("클립 목록 요청")
        clips = []
        
        for file in os.listdir(clips_dir):
            file_path = os.path.join(clips_dir, file)
            if (os.path.isfile(file_path) and 
                file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))):
                
                file_stats = os.stat(file_path)
                clips.append({
                    "id": os.path.splitext(file)[0],
                    "name": file,
                    "path": str(file_path),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        
        logger.info(f"클립 목록 로드 완료: {len(clips)} 항목")
        return {"status": "success", "clips": clips, "count": len(clips)}
    except Exception as e:
        logger.error(f"클립 목록 가져오기 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"클립 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/outputs")
async def list_outputs():
    """출력 영상 목록 가져오기"""
    try:
        logger.info("출력 영상 목록 요청")
        outputs = []
        
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            if (os.path.isfile(file_path) and 
                file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))):
                
                file_stats = os.stat(file_path)
                outputs.append({
                    "id": os.path.splitext(file)[0],
                    "name": file,
                    "path": str(file_path),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        
        logger.info(f"출력 영상 목록 로드 완료: {len(outputs)} 항목")
        return {"status": "success", "outputs": outputs, "count": len(outputs)}
    except Exception as e:
        logger.error(f"출력 영상 목록 가져오기 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"출력 영상 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/finals")
async def list_finals():
    """최종 영상 목록 가져오기"""
    try:
        logger.info("최종 영상 목록 요청")
        finals = []
        
        for file in os.listdir(final_dir):
            file_path = os.path.join(final_dir, file)
            if (os.path.isfile(file_path) and 
                file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm'))):
                
                file_stats = os.stat(file_path)
                finals.append({
                    "id": os.path.splitext(file)[0],
                    "name": file,
                    "path": str(file_path),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        
        logger.info(f"최종 영상 목록 로드 완료: {len(finals)} 항목")
        return {"status": "success", "finals": finals, "count": len(finals)}
    except Exception as e:
        logger.error(f"최종 영상 목록 가져오기 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"최종 영상 목록 가져오기 오류: {str(e)}"}
        )