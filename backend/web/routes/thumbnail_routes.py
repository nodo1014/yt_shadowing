#!/usr/bin/env python3
"""
File: thumbnail_routes.py
Description: 썸네일 관련 API 라우트
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from yt_shadowing.core.utils import get_project_root, ensure_dir_exists
from yt_shadowing.core.generator import ThumbnailGenerator

router = APIRouter()

# 데이터 모델
class ThumbnailRequest(BaseModel):
    main_text: str
    subtitle_text: Optional[str] = None
    background_image: Optional[str] = None
    output_path: Optional[str] = None
    
class TemplateRequest(BaseModel):
    template_name: str
    main_text: str
    subtitle_text: Optional[str] = None
    output_path: Optional[str] = None

# 경로 설정
thumbnails_dir = get_project_root() / "thumbnails"
ensure_dir_exists(thumbnails_dir)

# 썸네일 생성기 인스턴스
thumbnail_generator = ThumbnailGenerator()

@router.post("/generate")
async def generate_thumbnail(request: ThumbnailRequest):
    """썸네일 이미지 생성"""
    try:
        # 출력 경로가 없는 경우 기본값 생성
        if not request.output_path:
            # 파일명에 사용할 수 있는 텍스트 생성
            safe_text = request.main_text[:20].replace(" ", "_").lower()
            request.output_path = str(thumbnails_dir / f"{safe_text}_thumbnail.jpg")
            
        # 썸네일 생성
        try:
            output_path = thumbnail_generator.generate_thumbnail(
                main_text=request.main_text,
                subtitle_text=request.subtitle_text,
                background_image=request.background_image,
                output_path=request.output_path
            )
            return {"status": "success", "path": output_path}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"썸네일 생성 실패: {str(e)}"}
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"썸네일 생성 오류: {str(e)}"}
        )

@router.post("/template")
async def apply_template(request: TemplateRequest):
    """템플릿 적용하여 썸네일 생성"""
    try:
        # 출력 경로가 없는 경우 기본값 생성
        if not request.output_path:
            # 파일명에 사용할 수 있는 텍스트 생성
            safe_text = request.main_text[:20].replace(" ", "_").lower()
            template_name = request.template_name.lower()
            request.output_path = str(thumbnails_dir / f"{safe_text}_{template_name}_thumbnail.jpg")
            
        # 템플릿 적용
        try:
            output_path = thumbnail_generator.apply_template(
                template_name=request.template_name,
                main_text=request.main_text,
                subtitle_text=request.subtitle_text,
                output_path=request.output_path
            )
            return {"status": "success", "path": output_path, "template": request.template_name}
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"템플릿 적용 실패: {str(e)}"}
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"템플릿 적용 오류: {str(e)}"}
        )

@router.post("/upload/background")
async def upload_background(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None)
):
    """배경 이미지 업로드"""
    try:
        # 파일 확장자 확인
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "지원되지 않는 이미지 형식입니다"}
            )
            
        # 저장 경로 생성
        backgrounds_dir = thumbnails_dir / "backgrounds"
        ensure_dir_exists(backgrounds_dir)
        
        # 파일명 생성
        if name:
            safe_name = name.replace(" ", "_").lower()
            output_path = backgrounds_dir / f"{safe_name}{file_ext}"
        else:
            output_path = backgrounds_dir / file.filename
            
        # 파일 저장
        content = await file.read()
        with open(output_path, "wb") as f:
            f.write(content)
            
        return {"status": "success", "path": str(output_path)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"배경 이미지 업로드 오류: {str(e)}"}
        )

@router.get("/backgrounds")
async def list_backgrounds():
    """배경 이미지 목록 가져오기"""
    try:
        backgrounds_dir = thumbnails_dir / "backgrounds"
        if not backgrounds_dir.exists():
            ensure_dir_exists(backgrounds_dir)
            return {"status": "success", "backgrounds": [], "count": 0}
            
        backgrounds = []
        for file in os.listdir(backgrounds_dir):
            file_path = backgrounds_dir / file
            if file_path.is_file() and file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                backgrounds.append({
                    "name": file,
                    "path": str(file_path)
                })
                
        return {"status": "success", "backgrounds": backgrounds, "count": len(backgrounds)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"배경 이미지 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/templates")
async def list_templates():
    """사용 가능한 템플릿 목록 가져오기"""
    try:
        templates = thumbnail_generator.config.get("templates", {})
        return {"status": "success", "templates": list(templates.keys())}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"템플릿 목록 가져오기 오류: {str(e)}"}
        )

@router.get("/thumbnails")
async def list_thumbnails():
    """생성된 썸네일 목록 가져오기"""
    try:
        thumbnails = []
        for file in os.listdir(thumbnails_dir):
            file_path = os.path.join(thumbnails_dir, file)
            if (os.path.isfile(file_path) and 
                os.path.splitext(file_path)[1].lower() in [".jpg", ".jpeg", ".png"]):
                
                file_stats = os.stat(file_path)
                thumbnails.append({
                    "name": file,
                    "path": file_path,
                    "size": file_stats.st_size,
                    "modified": file_stats.st_mtime
                })
                
        return {"status": "success", "thumbnails": thumbnails, "count": len(thumbnails)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"썸네일 목록 가져오기 오류: {str(e)}"}
        )