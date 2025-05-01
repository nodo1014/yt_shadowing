#!/usr/bin/env python3
"""
File: thumbnail_routes.py
Description: 썸네일 생성 관련 API 라우트
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, File, Form, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# 코어 모듈 임포트 경로 수정
from backend.core.utils import get_project_root, ensure_dir_exists, setup_logger
from backend.core.generator import ThumbnailGenerator

router = APIRouter()

# 로거 설정
logger = setup_logger('thumbnail_routes', 'thumbnail_routes.log')

# 데이터 모델
class ThumbnailRequest(BaseModel):
    text: str
    subtitle: Optional[str] = None
    template: str = "basic"
    output_path: Optional[str] = None

# 경로 설정
data_dir = Path(__file__).parent.parent.parent / "data"
thumbnails_dir = data_dir / "thumbnails"
ensure_dir_exists(thumbnails_dir)

# 진행 상태 추적용 딕셔너리
task_status = {}

@router.post("/generate")
async def generate_thumbnail(
    text: str = Form(...),
    subtitle: Optional[str] = Form(None),
    template: str = Form("basic"),
    output_path: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None
):
    """썸네일 생성"""
    try:
        logger.info(f"썸네일 생성 요청: {text} (template: {template})")
        
        # 썸네일 생성기 초기화
        generator = ThumbnailGenerator()
        
        # 출력 경로 설정
        if not output_path:
            safe_text = text[:20].replace(' ', '_').replace('/', '_').replace('\\', '_')
            output_path = str(thumbnails_dir / f"{safe_text}_{uuid.uuid4().hex[:8]}.jpg")
        
        # 작업 ID 생성
        task_id = str(uuid.uuid4())
        task_status[task_id] = {
            "state": "PENDING",
            "progress": 0,
            "status": "썸네일 생성 준비 중"
        }
        
        # 백그라운드 작업으로 처리
        async def generate_task():
            try:
                task_status[task_id]["state"] = "PROGRESS"
                task_status[task_id]["status"] = "썸네일 생성 중"
                task_status[task_id]["progress"] = 30
                
                # 썸네일 생성
                result = await generator.generate_thumbnail(
                    text, subtitle, template, output_path
                )
                
                if result:
                    task_status[task_id]["state"] = "SUCCESS"
                    task_status[task_id]["status"] = "완료"
                    task_status[task_id]["progress"] = 100
                    task_status[task_id]["result"] = {"thumbnail_path": output_path}
                else:
                    task_status[task_id]["state"] = "FAILURE"
                    task_status[task_id]["status"] = "썸네일 생성 실패"
                    task_status[task_id]["error"] = "썸네일 생성 중 오류가 발생했습니다"
            except Exception as e:
                logger.error(f"썸네일 생성 작업 오류: {str(e)}")
                task_status[task_id]["state"] = "FAILURE"
                task_status[task_id]["status"] = f"오류: {str(e)}"
                task_status[task_id]["error"] = str(e)
                
        if background_tasks:
            # 백그라운드 작업으로 처리
            background_tasks.add_task(generate_task)
            return {"status": "pending", "task_id": task_id}
        else:
            # 동기적으로 처리
            result = await generator.generate_thumbnail(text, subtitle, template, output_path)
            if result:
                logger.info(f"썸네일 생성 성공: {output_path}")
                return {"status": "success", "thumbnail_path": output_path}
            else:
                logger.error("썸네일 생성 실패")
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "썸네일 생성 실패"}
                )
    except Exception as e:
        logger.error(f"썸네일 생성 요청 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"썸네일 생성 오류: {str(e)}"}
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

@router.post("/upload-custom")
async def upload_custom_thumbnail(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None)
):
    """커스텀 썸네일 업로드"""
    try:
        logger.info(f"커스텀 썸네일 업로드: {file.filename}")
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png"]:
            logger.warning(f"지원되지 않는 이미지 형식: {file_ext}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "지원되지 않는 이미지 형식입니다"}
            )
            
        # 저장 경로 생성
        if name:
            safe_name = name.replace('/', '_').replace('\\', '_')
            thumbnail_path = thumbnails_dir / f"{safe_name}{file_ext}"
        else:
            thumbnail_path = thumbnails_dir / f"custom_{uuid.uuid4().hex[:8]}{file_ext}"
        
        # 파일 저장
        content = await file.read()
        with open(thumbnail_path, "wb") as f:
            f.write(content)
        
        logger.info(f"썸네일 저장됨: {thumbnail_path}")
        
        return {"status": "success", "thumbnail_path": str(thumbnail_path)}
    except Exception as e:
        logger.error(f"썸네일 업로드 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"썸네일 업로드 오류: {str(e)}"}
        )

@router.get("/list")
async def list_thumbnails():
    """썸네일 목록 가져오기"""
    try:
        logger.info("썸네일 목록 요청")
        thumbnails = []
        
        for file in os.listdir(thumbnails_dir):
            file_path = os.path.join(thumbnails_dir, file)
            if (os.path.isfile(file_path) and 
                file.lower().endswith(('.jpg', '.jpeg', '.png'))):
                
                file_stats = os.stat(file_path)
                thumbnails.append({
                    "id": os.path.splitext(file)[0],
                    "name": file,
                    "path": str(file_path),
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
        
        logger.info(f"썸네일 목록 로드 완료: {len(thumbnails)} 항목")
        return {"status": "success", "thumbnails": thumbnails, "count": len(thumbnails)}
    except Exception as e:
        logger.error(f"썸네일 목록 가져오기 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"썸네일 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/view/{file_path:path}")
async def view_thumbnail(file_path: str):
    """썸네일 이미지 보기"""
    try:
        logger.info(f"썸네일 보기 요청: {file_path}")
        
        # 파일 경로 검증
        if not os.path.exists(file_path):
            # thumbnails_dir에서 찾기 시도
            thumb_file_path = thumbnails_dir / file_path
            if not thumb_file_path.exists():
                return JSONResponse(
                    status_code=404,
                    content={"status": "error", "message": "파일을 찾을 수 없습니다"}
                )
            file_path = str(thumb_file_path)
        
        # 이미지 파일 전송
        return FileResponse(
            file_path, 
            media_type="image/jpeg"
        )
    except Exception as e:
        logger.error(f"썸네일 보기 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"썸네일 보기 오류: {str(e)}"}
        )