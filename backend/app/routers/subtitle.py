#!/usr/bin/env python3
"""
File: subtitle.py
Description: 자막 관련 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import json
from pathlib import Path
import pysrt

from app.config import settings
from app.common.utils import setup_logger, get_project_root
from app.services.subtitle import SubtitleProcessor

# 라우터 설정
router = APIRouter(
    prefix="/api/subtitle",
    tags=["subtitle"],
    responses={404: {"description": "Not found"}},
)

# 로거 설정
logger = setup_logger("subtitle_router", "subtitle_router.log")

# 자막 처리기 인스턴스
subtitle_processor = SubtitleProcessor()

# 번역 요청 모델
class TranslationRequest(BaseModel):
    video_path: str
    subtitle_index: int
    text: str
    translation: str

# 번역 결과 모델
class TranslationResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

@router.post("/translate", response_model=TranslationResponse)
async def translate_subtitle(request: TranslationRequest):
    """
    자막 번역을 저장합니다.
    
    Args:
        request: 번역 요청 데이터
        
    Returns:
        TranslationResponse: 번역 결과
    """
    try:
        logger.info(f"자막 번역 요청 - 비디오: {request.video_path}, 인덱스: {request.subtitle_index}")
        
        # 경로 처리 - 비디오 경로가 상대 경로인 경우 프로젝트 루트 기준 절대 경로로 변환
        video_path = request.video_path
        if not os.path.isabs(video_path):
            # 'clips/' 또는 'data/clips/'로 시작하는 경로 처리
            if video_path.startswith('clips/'):
                video_path = f"data/{video_path}"
            elif not video_path.startswith('data/'):
                video_path = f"data/clips/{video_path}"
            
            # 절대 경로로 변환
            project_root = get_project_root()
            video_path = str(project_root / "backend" / video_path)
            
        logger.debug(f"변환된 비디오 경로: {video_path}")
        
        # 자막 파일 경로 찾기
        subtitle_file = None
        video_dir = os.path.dirname(video_path)
        video_name = os.path.basename(video_path)
        video_name_without_ext = os.path.splitext(video_name)[0]
        
        # 가능한 자막 파일 확장자 목록
        subtitle_exts = ['.en.srt', '.en.vtt', '.srt', '.vtt']
        
        for ext in subtitle_exts:
            potential_path = os.path.join(video_dir, f"{video_name_without_ext}{ext}")
            if os.path.exists(potential_path):
                subtitle_file = potential_path
                break
        
        if not subtitle_file:
            logger.error(f"자막 파일을 찾을 수 없습니다: {video_path}")
            raise HTTPException(status_code=404, detail="자막 파일을 찾을 수 없습니다.")
        
        logger.debug(f"자막 파일 경로: {subtitle_file}")
        
        # 자막 파일에서 내용 로드
        subtitles = []
        try:
            subs = pysrt.open(subtitle_file)
            for sub in subs:
                subtitles.append({
                    "index": sub.index,
                    "start_time": str(sub.start),
                    "end_time": str(sub.end),
                    "text": sub.text.strip()
                })
        except Exception as e:
            logger.error(f"자막 파일 로드 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"자막 파일 로드 오류: {str(e)}")
        
        if not subtitles or request.subtitle_index < 0 or request.subtitle_index >= len(subtitles):
            logger.error(f"잘못된 자막 인덱스: {request.subtitle_index}, 자막 수: {len(subtitles) if subtitles else 0}")
            raise HTTPException(status_code=400, detail="잘못된 자막 인덱스입니다.")
        
        # 번역 정보 저장 (별도의 번역 파일 사용)
        translations_file = os.path.join(video_dir, f"{video_name_without_ext}.translations.json")
        
        # 기존 번역 정보 로드 또는 새로 생성
        translations = {}
        if os.path.exists(translations_file):
            try:
                with open(translations_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"번역 파일 형식 오류, 새로 생성합니다: {translations_file}")
                translations = {}
        
        # 번역 정보 업데이트
        translations[str(request.subtitle_index)] = request.translation
        
        # 번역 정보 저장
        with open(translations_file, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
        
        logger.info(f"자막 번역 저장 완료 - 비디오: {request.video_path}, 인덱스: {request.subtitle_index}")
        
        return TranslationResponse(
            status="success",
            message="번역이 성공적으로 저장되었습니다.",
            data={"index": request.subtitle_index, "translation": request.translation}
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"자막 번역 저장 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"자막 번역 저장 중 오류가 발생했습니다: {str(e)}") 