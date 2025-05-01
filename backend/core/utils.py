#!/usr/bin/env python3
"""
File: utils.py
Description: 쉐도잉 시스템에서 공통으로 사용되는 유틸리티 함수들
"""

import os
import yaml
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List

def load_config(config_path: str, default_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    YAML 설정 파일을 로드하는 함수
    
    Args:
        config_path: 설정 파일 경로
        default_config: 기본 설정 (옵션)
        
    Returns:
        설정 사전
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        logging.info(f"설정을 로드했습니다: {config_path}")
        return config
    except Exception as e:
        logging.error(f"설정 로드 오류: {str(e)}")
        return default_config if default_config is not None else {}

def ensure_dir_exists(dir_path: str) -> None:
    """
    디렉토리가 존재하는지 확인하고 없으면 생성
    
    Args:
        dir_path: 디렉토리 경로
    """
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    
def get_temp_file(suffix: str = ".tmp") -> str:
    """
    임시 파일 생성
    
    Args:
        suffix: 파일 확장자
        
    Returns:
        임시 파일 경로
    """
    temp_file = tempfile.mktemp(suffix=suffix)
    return temp_file

def get_project_root() -> Path:
    """
    프로젝트 루트 디렉토리 반환
    
    Returns:
        프로젝트 루트 경로
    """
    return Path(__file__).parent.parent.parent

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    로거 설정
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 경로
        level: 로깅 레벨
        
    Returns:
        설정된 로거
    """
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger

def supported_video_formats() -> List[str]:
    """
    지원되는 비디오 형식 목록 반환
    
    Returns:
        지원되는 비디오 확장자 목록
    """
    return ['.mp4', '.mkv', '.avi', '.mov', '.webm']

def is_supported_video_format(file_path: str) -> bool:
    """
    파일이 지원되는 비디오 형식인지 확인
    
    Args:
        file_path: 파일 경로
        
    Returns:
        지원 여부
    """
    ext = Path(file_path).suffix.lower()
    return ext in supported_video_formats()