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
import sys
from datetime import datetime

from app.config import settings

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
    
def get_temp_file(prefix: str = "", suffix: str = ".tmp") -> str:
    """
    임시 파일 생성
    
    Args:
        prefix: 파일 이름 접두사
        suffix: 파일 확장자
        
    Returns:
        임시 파일 경로
    """
    temp_file = tempfile.mktemp(prefix=prefix, suffix=suffix)
    return temp_file

def get_project_root() -> Path:
    """
    프로젝트 루트 디렉토리 반환
    
    Returns:
        프로젝트 루트 경로
    """
    # 현재 파일(__file__)의 위치:   /project_root/backend/app/common/utils.py
    # 따라서 3단계 상위 디렉토리가 프로젝트 루트
    return Path(__file__).parent.parent.parent.parent

def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO):
    """
    로거를 설정하고 반환합니다.
    
    Args:
        name: 로거 이름
        log_file: 로그 파일 이름 (상대 경로, 기본값: None)
        level: 로깅 레벨 (기본값: logging.INFO)
        
    Returns:
        설정된 Logger 객체
    """
    # 로거 인스턴스 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 이미 핸들러가 설정되어 있으면 중복 방지를 위해 추가하지 않음
    if logger.handlers:
        return logger
    
    # 로그 형식 설정
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 로그 파일 핸들러 추가 (파일명이 지정된 경우)
    if log_file:
        try:
            # 로그 디렉토리 설정 (settings에서 가져오거나 기본값 사용)
            log_dir_path = getattr(settings, 'LOG_DIR', 'data/logs')
            
            # 프로젝트 루트 기준으로 절대 경로 생성
            project_root = get_project_root()
            backend_dir = project_root / "backend"
            log_dir = backend_dir / log_dir_path
            log_dir.mkdir(exist_ok=True, parents=True)
            
            # 로그 파일 경로 설정 (로그 파일에 날짜 접두사 추가)
            today = datetime.now().strftime('%Y%m%d')
            log_path = log_dir / f"{today}_{log_file}"
            
            # 파일 핸들러 추가
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # 로깅 설정 실패 시 콘솔에만 출력
            logger.error(f"로그 파일 설정 실패: {str(e)}")
    
    return logger

def format_file_size(size_bytes: int) -> str:
    """
    바이트 단위의 파일 크기를 읽기 쉬운 형태로 변환합니다.
    
    Args:
        size_bytes: 바이트 단위의 파일 크기
        
    Returns:
        읽기 쉬운 형태의 파일 크기 문자열 (예: "1.23 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def is_valid_url(url: str) -> bool:
    """
    문자열이 유효한 URL인지 확인합니다.
    
    Args:
        url: 확인할 URL 문자열
        
    Returns:
        유효한 URL인 경우 True, 그렇지 않으면 False
    """
    import re
    
    # URL 정규식 패턴
    url_pattern = re.compile(
        r'^(https?:\/\/)?(www\.)?'  # http://, https://, www.
        r'([a-zA-Z0-9][-a-zA-Z0-9]{0,62}\.)+[a-zA-Z]{2,63}'  # 도메인
        r'(:\d{1,5})?'  # 포트
        r'(\/[-a-zA-Z0-9%_.~#+]*)*'  # 경로
        r'(\?[;&a-zA-Z0-9%_.~+=-]*)?'  # 쿼리 문자열
        r'(#[-a-zA-Z0-9%_&=]*)?$'  # 앵커
    )
    
    return bool(url_pattern.match(url))

def get_youtube_id(url: str) -> Optional[str]:
    """
    YouTube URL에서 동영상 ID를 추출합니다.
    
    Args:
        url: YouTube URL
        
    Returns:
        추출된 YouTube 동영상 ID 또는 None (추출 실패 시)
    """
    import re
    
    # YouTube 동영상 ID 패턴
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # v=xxxx 또는 /xxxx 형식
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',  # embed/xxxx, v/xxxx 또는 youtu.be/xxxx 형식
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'  # watch?v=xxxx 형식
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

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

def get_temp_file_path(prefix: str = "", suffix: str = ".tmp") -> str:
    """
    임시 파일 경로 생성 (실제 파일은 생성하지 않음)
    
    Args:
        prefix: 파일 이름 접두사
        suffix: 파일 확장자
        
    Returns:
        임시 파일 경로
    """
    return get_temp_file(prefix=prefix, suffix=suffix) 