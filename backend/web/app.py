#!/usr/bin/env python3
"""
File: app.py
Description: FastAPI 기반 웹 인터페이스 메인 애플리케이션
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# 코어 모듈 임포트
from yt_shadowing.core.utils import load_config, get_project_root
from yt_shadowing.core.subtitle import SubtitleIndexer, SubtitleMatcher
from yt_shadowing.core.extractor import VideoExtractor
from yt_shadowing.core.generator import RepeatVideoGenerator, ThumbnailGenerator

# API 라우트 임포트
from .routes.subtitle_routes import router as subtitle_router
from .routes.video_routes import router as video_router
from .routes.thumbnail_routes import router as thumbnail_router

# 앱 생성
app = FastAPI(
    title="영어 쉐도잉 시스템",
    description="영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구",
    version="0.1.0"
)

# 정적 파일 및 템플릿 설정
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# 백그라운드 작업 상태 추적
task_status = {}

# 설정 로드
config_path = get_project_root() / "config.yaml"
app_config = load_config(config_path)

# 라우터 등록
app.include_router(subtitle_router, prefix="/api/subtitle", tags=["자막"])
app.include_router(video_router, prefix="/api/video", tags=["비디오"])
app.include_router(thumbnail_router, prefix="/api/thumbnail", tags=["썸네일"])

@app.get("/")
async def index(request: Request):
    """메인 페이지 렌더링"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/config")
async def get_config():
    """현재 설정 가져오기"""
    return {"config": app_config}

@app.post("/config")
async def update_config(config: Dict[str, Any]):
    """설정 업데이트"""
    global app_config
    app_config.update(config)
    
    # 설정 파일에 저장
    with open(config_path, "w") as f:
        yaml.dump(app_config, f, default_flow_style=False, allow_unicode=True)
    
    return {"status": "success", "message": "설정이 업데이트되었습니다"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """백그라운드 작업 상태 확인"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다")
    return task_status[task_id]

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)