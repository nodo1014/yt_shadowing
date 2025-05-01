#!/usr/bin/env python3
"""
File: subtitle.py
Description: 자막 인덱싱 및 처리를 위한 코어 모듈
"""

import os
import json
import pysrt
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from .utils import setup_logger, ensure_dir_exists, get_project_root

logger = setup_logger('subtitle_core', 'subtitle_core.log')

class SubtitleIndexer:
    """자막 인덱싱 및 검색을 위한 클래스"""
    
    def __init__(self, output_path: Optional[str] = None):
        """
        SubtitleIndexer 초기화
        
        Args:
            output_path: 인덱스 파일 저장 경로 (기본값: subtitle_index.json)
        """
        self.output_path = output_path or str(get_project_root() / "subtitle_index.json")
        self.index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """
        기존 인덱스 파일 로드
        
        Returns:
            인덱스 데이터
        """
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"인덱스 로드 오류: {str(e)}")
        return {"subtitles": {}}
    
    def save_index(self) -> None:
        """인덱스를 파일에 저장"""
        ensure_dir_exists(os.path.dirname(self.output_path))
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
        logger.info(f"인덱스가 저장되었습니다: {self.output_path}")
    
    def index_subtitle(self, subtitle_path: str, video_id: str) -> Dict[str, Any]:
        """
        자막 파일 인덱싱
        
        Args:
            subtitle_path: SRT 파일 경로
            video_id: 비디오 ID 또는 이름
            
        Returns:
            인덱싱된 자막 데이터
        """
        try:
            subs = pysrt.open(subtitle_path)
            subtitle_data = []
            
            for sub in subs:
                subtitle_data.append({
                    "index": sub.index,
                    "start_time": str(sub.start),
                    "end_time": str(sub.end),
                    "duration": (sub.end.ordinal - sub.start.ordinal) / 1000,  # 초 단위
                    "text": sub.text.strip()
                })
            
            self.index["subtitles"][video_id] = {
                "path": subtitle_path,
                "data": subtitle_data,
                "count": len(subtitle_data)
            }
            
            logger.info(f"자막 인덱싱 완료: {video_id} ({len(subtitle_data)} 항목)")
            return self.index["subtitles"][video_id]
            
        except Exception as e:
            logger.error(f"자막 인덱싱 오류: {str(e)}")
            raise
    
    def search_subtitles(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        자막 검색
        
        Args:
            query: 검색 키워드
            limit: 결과 최대 개수
            
        Returns:
            검색 결과 목록
        """
        results = []
        
        for video_id, subtitle_info in self.index["subtitles"].items():
            for item in subtitle_info["data"]:
                if query.lower() in item["text"].lower():
                    results.append({
                        "video_id": video_id,
                        "subtitle_item": item,
                        "subtitle_path": subtitle_info["path"]
                    })
                    
                    if len(results) >= limit:
                        break
        
        logger.info(f"검색 결과: {len(results)} 항목 (키워드: '{query}')")
        return results
    
    def get_subtitle_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        비디오 ID로 자막 데이터 검색
        
        Args:
            video_id: 비디오 ID 또는 이름
            
        Returns:
            자막 데이터 또는 None
        """
        return self.index["subtitles"].get(video_id)

class SubtitleMatcher:
    """자막과 번역을 매칭하는 클래스"""
    
    def __init__(self, translation_path: Optional[str] = None):
        """
        SubtitleMatcher 초기화
        
        Args:
            translation_path: 번역 파일 저장 경로
        """
        self.translation_path = translation_path
        self.translations = {}
        if translation_path and os.path.exists(translation_path):
            self._load_translations()
    
    def _load_translations(self) -> None:
        """기존 번역 파일 로드"""
        try:
            with open(self.translation_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            logger.info(f"번역 로드 완료: {len(self.translations)} 항목")
        except Exception as e:
            logger.error(f"번역 로드 오류: {str(e)}")
    
    def save_translations(self, output_path: Optional[str] = None) -> None:
        """
        번역을 파일에 저장
        
        Args:
            output_path: 저장할 파일 경로
        """
        save_path = output_path or self.translation_path
        if not save_path:
            logger.error("저장 경로가 지정되지 않았습니다")
            return
            
        ensure_dir_exists(os.path.dirname(save_path))
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.translations, f, ensure_ascii=False, indent=2)
        logger.info(f"번역이 저장되었습니다: {save_path}")
    
    def add_translation(self, source_text: str, translated_text: str) -> None:
        """
        번역 추가
        
        Args:
            source_text: 원본 텍스트
            translated_text: 번역된 텍스트
        """
        if source_text.strip():
            self.translations[source_text.strip()] = translated_text.strip()
    
    def get_translation(self, source_text: str) -> Optional[str]:
        """
        번역 가져오기
        
        Args:
            source_text: 원본 텍스트
            
        Returns:
            번역된 텍스트 또는 None
        """
        return self.translations.get(source_text.strip())

    def translate_subtitles(self, subtitle_path: str, output_path: str) -> Dict[str, str]:
        """
        자막 파일의 모든 텍스트 번역
        
        Args:
            subtitle_path: 자막 파일 경로
            output_path: 번역 저장 파일 경로
            
        Returns:
            번역 맵 (원본 -> 번역)
        """
        try:
            subs = pysrt.open(subtitle_path)
            translations = {}
            
            # 기존 번역 적용
            for sub in subs:
                text = sub.text.strip()
                if text in self.translations:
                    translations[text] = self.translations[text]
            
            # 새 번역 저장
            self.translation_path = output_path
            self.translations = translations
            self.save_translations()
            
            return translations
            
        except Exception as e:
            logger.error(f"자막 번역 오류: {str(e)}")
            raise