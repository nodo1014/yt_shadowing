#!/usr/bin/env python3
"""
File: config.py
Description: 애플리케이션 설정 및 환경 변수 관리
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""
    
    # 기본 설정
    APP_NAME: str = "영어 쉐도잉 시스템"
    APP_VERSION: str = "0.3.0"
    DEBUG: bool = True
    
    # 서버 설정
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # CORS 설정
    CORS_ORIGINS: List[str] = ["*"]
    
    # 파일 경로 설정
    DATA_DIR: str = "data"
    CLIPS_DIR: str = "data/clips"
    CLIPS_OUTPUT_DIR: str = "data/clips_output"
    SUBTITLES_DIR: str = "data/subtitles"
    TEMP_DIR: str = "data/temp"
    LOG_DIR: str = "data/logs"
    
    # 기본 디렉토리 경로
    DEFAULT_CLIP_DIR: str = "data/clips"
    DEFAULT_CLIPS_OUTPUT_DIR: str = "data/clips_output"
    DEFAULT_SUBTITLE_DIR: str = "data/subtitles"
    DEFAULT_TEMP_DIR: str = "data/temp"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 설정 인스턴스 생성
settings = Settings()

# 프로젝트 루트 디렉토리 경로
def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 반환"""
    return Path(__file__).parent.parent.parent

# 필요한 디렉토리 생성
def ensure_directories():
    """필요한 디렉토리가 존재하는지 확인하고 없으면 생성"""
    root = get_project_root()
    dirs = [
        settings.DATA_DIR,
        settings.CLIPS_DIR,
        settings.CLIPS_OUTPUT_DIR,
        settings.SUBTITLES_DIR,
        settings.TEMP_DIR,
        settings.LOG_DIR,
        "app/static",
        "app/templates"
    ]
    
    print("필요한 디렉토리 생성 중...")
    for dir_path in dirs:
        full_path = root / "backend" / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  - 디렉토리 확인: {full_path}")
        
    print("디렉토리 생성 완료")
        
# 앱 시작 시 디렉토리 확인
ensure_directories() 