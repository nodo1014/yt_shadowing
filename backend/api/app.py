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
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 코어 모듈 임포트 (경로 수정)
from backend.core.utils import setup_logger, ensure_dir_exists, get_project_root, load_config
from backend.core.subtitle import SubtitleIndexer, SubtitleMatcher
from backend.core.extractor import VideoExtractor
from backend.core.generator import RepeatVideoGenerator, ThumbnailGenerator

# API 라우트 임포트 (경로 수정)
from backend.api.routes.subtitle_routes import router as subtitle_router
from backend.api.routes.video_routes import router as video_router
from backend.api.routes.thumbnail_routes import router as thumbnail_router

# 앱 생성
app = FastAPI(
    title="영어 쉐도잉 시스템",
    description="영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구",
    version="0.2.0"
)

# CORS 설정 추가 - 프론트엔드 연결을 위해 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시 보안을 위해 특정 도메인만 허용하는 것이 좋음
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# 정적 파일 디렉토리가 없으면 생성
ensure_dir_exists(static_dir)
ensure_dir_exists(templates_dir)

# 정적 파일 제공 설정
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# 백그라운드 작업 상태 추적
task_status = {}

# 설정 로드 - 경로 수정
config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
app_config = load_config(config_path)

# 로거 설정
logger = setup_logger('api', 'api.log')

# 라우터 등록
app.include_router(subtitle_router, prefix="/api/subtitle", tags=["자막"])
app.include_router(video_router, prefix="/api/video", tags=["비디오"])
app.include_router(thumbnail_router, prefix="/api/thumbnail", tags=["썸네일"])

@app.get("/")
async def index(request: Request):
    """메인 페이지 렌더링"""
    logger.info("메인 페이지 요청")
    # index.html 파일이 있는지 확인
    if (templates_dir / "index.html").exists():
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        return {"message": "API 서버가 실행 중입니다. API 문서는 /docs에서 확인할 수 있습니다."}

@app.get("/config")
async def get_config():
    """현재 설정 가져오기"""
    logger.info("설정 요청")
    return {"config": app_config}

@app.post("/config")
async def update_config(config: Dict[str, Any]):
    """설정 업데이트"""
    global app_config
    logger.info("설정 업데이트")
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

@app.get("/api/health")
async def health_check():
    """API 서버 상태 확인"""
    return {"status": "healthy", "version": "0.2.0"}

# 에러 핸들러 추가
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리기"""
    logger.error(f"예외 발생: {str(exc)}")
    return JSONResponse(
        status_code=500, 
        content={"status": "error", "message": f"내부 서버 오류: {str(exc)}"}
    )

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)