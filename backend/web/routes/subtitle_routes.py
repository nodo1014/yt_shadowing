#!/usr/bin/env python3
"""
File: subtitle_routes.py
Description: 자막 관련 API 라우트
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
from yt_shadowing.core.subtitle import SubtitleIndexer, SubtitleMatcher
from yt_shadowing.core.extractor import VideoExtractor

router = APIRouter()

# 데이터 모델
class SubtitleSearchRequest(BaseModel):
    query: str
    limit: int = 10

class SubtitleIndexRequest(BaseModel):
    video_id: str
    subtitle_path: str

class TranslationRequest(BaseModel):
    source_text: str
    translated_text: str

# 경로 설정
subtitles_dir = get_project_root() / "subtitles"
ensure_dir_exists(subtitles_dir)

translations_dir = get_project_root() / "translations"
ensure_dir_exists(translations_dir)

# 인덱서 및 매처 인스턴스
subtitle_indexer = SubtitleIndexer()
subtitle_matcher = SubtitleMatcher()

@router.post("/search")
async def search_subtitles(request: SubtitleSearchRequest):
    """자막 검색"""
    try:
        results = subtitle_indexer.search_subtitles(request.query, request.limit)
        return {"status": "success", "results": results, "count": len(results)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"검색 오류: {str(e)}"}
        )

@router.post("/index")
async def index_subtitle(request: SubtitleIndexRequest):
    """자막 인덱싱"""
    try:
        result = subtitle_indexer.index_subtitle(request.subtitle_path, request.video_id)
        subtitle_indexer.save_index()
        return {"status": "success", "indexed": result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"인덱싱 오류: {str(e)}"}
        )

@router.post("/upload")
async def upload_subtitle(
    file: UploadFile = File(...),
    video_id: str = Form(...),
    auto_index: bool = Form(False)
):
    """자막 파일 업로드"""
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in [".srt", ".vtt", ".ass"]:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "지원되지 않는 자막 형식입니다"}
            )
            
        # 저장 경로 생성
        safe_video_id = video_id.replace("/", "_").replace("\\", "_")
        subtitle_path = subtitles_dir / f"{safe_video_id}_subtitle{file_ext}"
        
        # 파일 저장
        content = await file.read()
        with open(subtitle_path, "wb") as f:
            f.write(content)
        
        # 자동 인덱싱
        result = {"path": str(subtitle_path)}
        if auto_index:
            indexed = subtitle_indexer.index_subtitle(str(subtitle_path), video_id)
            subtitle_indexer.save_index()
            result["indexed"] = indexed
        
        return {"status": "success", "result": result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"업로드 오류: {str(e)}"}
        )

@router.get("/extract")
async def extract_subtitle(
    video_path: str,
    output_path: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """비디오에서 자막 추출"""
    try:
        extractor = VideoExtractor()
        
        # 출력 경로가 없는 경우 기본값 생성
        if not output_path:
            video_name = Path(video_path).stem
            output_path = str(subtitles_dir / f"{video_name}_subtitle.srt")
        
        # 자막 추출 실행
        task_id = str(uuid.uuid4())
        
        if background_tasks:
            # 백그라운드 작업으로 실행
            async def extract_task():
                try:
                    success = await extractor.extract_subtitle(video_path, output_path)
                    return {"status": "success" if success else "error", "path": output_path}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
                    
            background_tasks.add_task(extract_task)
            return {"status": "pending", "task_id": task_id}
        else:
            # 동기적으로 실행
            success = await extractor.extract_subtitle(video_path, output_path)
            if success:
                return {"status": "success", "path": output_path}
            else:
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": "자막 추출 실패"}
                )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"자막 추출 오류: {str(e)}"}
        )

@router.post("/translate")
async def translate_subtitle(
    subtitle_path: str = Form(...),
    output_path: Optional[str] = Form(None)
):
    """자막 파일 번역"""
    try:
        # 출력 경로가 없는 경우 기본값 생성
        if not output_path:
            subtitle_name = Path(subtitle_path).stem
            output_path = str(translations_dir / f"{subtitle_name}_translation.json")
            
        # 번역 수행
        matcher = SubtitleMatcher(output_path)
        translations = matcher.translate_subtitles(subtitle_path, output_path)
        
        return {"status": "success", "path": output_path, "count": len(translations)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"자막 번역 오류: {str(e)}"}
        )

@router.post("/add_translation")
async def add_translation(request: TranslationRequest):
    """번역 추가"""
    try:
        # 번역 파일이 없으면 생성
        if not subtitle_matcher.translation_path:
            subtitle_matcher.translation_path = str(translations_dir / "translations.json")
            
        # 번역 추가
        subtitle_matcher.add_translation(request.source_text, request.translated_text)
        subtitle_matcher.save_translations()
        
        return {"status": "success", "source": request.source_text, "translation": request.translated_text}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"번역 추가 오류: {str(e)}"}
        )

@router.get("/translations/{video_id}")
async def get_translations(video_id: str):
    """비디오 ID에 해당하는 번역 가져오기"""
    try:
        # 번역 파일 경로
        translation_path = translations_dir / f"{video_id}_translation.json"
        
        if not translation_path.exists():
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "번역 파일을 찾을 수 없습니다"}
            )
            
        # 번역 로드
        with open(translation_path, "r", encoding="utf-8") as f:
            translations = json.load(f)
            
        return {"status": "success", "translations": translations, "count": len(translations)}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"번역 가져오기 오류: {str(e)}"}
        )