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
import asyncio
import datetime

from app.common.utils import setup_logger, ensure_dir_exists, get_project_root
from app.services.extractor import VideoExtractor
from app.config import settings

logger = setup_logger('subtitle_core', 'subtitle_core.log')

class SubtitleIndexer:
    """자막 인덱싱 및 검색을 위한 클래스"""
    
    def __init__(self, output_path: Optional[str] = None):
        """
        SubtitleIndexer 초기화
        
        Args:
            output_path: 인덱스 파일 저장 경로 (기본값: data/subtitles/index.json)
        """
        project_root = get_project_root()
        default_index_path = project_root / "backend" / settings.DEFAULT_SUBTITLE_DIR / "index.json"
        self.output_path = output_path or str(default_index_path)
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
        
        # 초기 인덱스 구조 생성
        return {
            "meta": {
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "version": "1.0.0"
            },
            "subtitles": {}
        }
    
    def save_index(self) -> None:
        """인덱스를 파일에 저장"""
        ensure_dir_exists(os.path.dirname(self.output_path))
        
        # 업데이트 시각 갱신
        self.index["meta"]["updated_at"] = datetime.datetime.now().isoformat()
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
        logger.info(f"인덱스가 저장되었습니다: {self.output_path}")
    
    def index_subtitle(self, subtitle_path: str, video_id: str, video_path: Optional[str] = None) -> Dict[str, Any]:
        """
        자막 파일 인덱싱
        
        Args:
            subtitle_path: SRT 파일 경로
            video_id: 비디오 ID 또는 이름
            video_path: 연결된 비디오 파일 경로 (옵션)
            
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
            
            # 자막 메타데이터 추가
            subtitle_meta = {
                "path": subtitle_path,
                "video_path": video_path,
                "count": len(subtitle_data),
                "indexed_at": datetime.datetime.now().isoformat(),
                "data": subtitle_data
            }
            
            self.index["subtitles"][video_id] = subtitle_meta
            
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
                data = json.load(f)
                # 구버전 형식(단순 사전) 지원
                if isinstance(data, dict) and not any(k in data for k in ["meta", "translations"]):
                    self.translations = data
                else:
                    self.translations = data.get("translations", {})
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
        
        # 개선된 JSON 구조로 저장
        translation_data = {
            "meta": {
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "language": "ko",  # 기본값, 추후 확장 가능
                "count": len(self.translations)
            },
            "translations": self.translations
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(translation_data, f, ensure_ascii=False, indent=2)
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

    def translate_subtitles(self, subtitle_path: str, output_path: Optional[str] = None) -> Dict[str, str]:
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
            
            # 표준 디렉토리 구조 사용 (없으면 기본값)
            if output_path is None:
                video_id = Path(subtitle_path).stem
                project_root = get_project_root()
                translations_dir = project_root / "backend" / settings.DEFAULT_SUBTITLE_DIR / "translations"
                ensure_dir_exists(str(translations_dir))
                output_path = str(translations_dir / f"{video_id}_translations.json")
            
            # 새 번역 저장
            self.translation_path = output_path
            self.translations = translations
            self.save_translations()
            
            return translations
            
        except Exception as e:
            logger.error(f"자막 번역 오류: {str(e)}")
            raise

class SubtitleProcessor:
    """자막 전처리, 클립 추출 등의 기능을 포함하는 고수준 인터페이스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        SubtitleProcessor 초기화
        
        Args:
            config: 설정 (옵션)
        """
        self.config = config or {}
        self.indexer = SubtitleIndexer()
        self.matcher = SubtitleMatcher()
        # 영어 자막 파일 확장자들 (우선순위 순)
        self.en_subtitle_extensions = ['.en.srt', '.en.vtt', '.srt', '.vtt']

    async def get_subtitles(self, video_path: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        비디오 파일의 자막 가져오기
        
        Args:
            video_path: 비디오 파일 경로
            language: 자막 언어 (옵션, 지정 시 해당 언어 자막 우선 처리)
            
        Returns:
            자막 항목 목록 (텍스트, 시작 시간, 종료 시간 포함)
        """
        video_path = Path(video_path)
        logger.info(f"자막 가져오기: {video_path}, 언어: {language}")
        
        # 지원되는 언어 코드 목록
        lang_codes = ['en', 'en-US', 'en-GB', 'ko', 'ja', 'zh-CN', 'zh-TW', 'fr', 'de', 'es']
        
        # 자막 파일 찾기
        subtitle_files = []
        
        # 1. 우선 지정된 언어의 자막 파일 확인
        if language:
            # 언어 코드 정리 (파일명으로 사용 가능하게)
            file_lang = language.replace('-', '_').lower()
            
            for ext in [f'.{file_lang}.srt', f'.{file_lang}.vtt']:
                subtitle_path = video_path.with_suffix(ext)
                if subtitle_path.exists():
                    logger.info(f"지정 언어 자막 발견: {subtitle_path}")
                    subtitle_files.append(subtitle_path)
        
        # 2. 언어별 자막 파일 확인 (지정 언어가 없거나 못 찾은 경우)
        if not subtitle_files:
            for lang in lang_codes:
                file_lang = lang.replace('-', '_').lower()
                
                for ext in [f'.{file_lang}.srt', f'.{file_lang}.vtt']:
                    subtitle_path = video_path.with_suffix(ext)
                    if subtitle_path.exists():
                        logger.info(f"언어별 자막 발견: {subtitle_path}")
                        subtitle_files.append(subtitle_path)
        
        # 3. 기본 자막 파일 확인 (언어별 자막이 없는 경우)
        if not subtitle_files:
            for ext in ['.srt', '.vtt']:
                subtitle_path = video_path.with_suffix(ext)
                if subtitle_path.exists():
                    logger.info(f"기본 자막 발견: {subtitle_path}")
                    subtitle_files.append(subtitle_path)
        
        if not subtitle_files:
            logger.warning(f"자막 파일을 찾을 수 없음: {video_path}")
            return []
        
        # 가장 우선순위가 높은 자막 파일 사용
        subtitle_path = subtitle_files[0]
        
        try:
            # 자막 파일 형식에 따라 처리
            if subtitle_path.suffix.lower() == '.srt':
                return await self._parse_srt(str(subtitle_path))
            elif subtitle_path.suffix.lower() == '.vtt':
                return await self._parse_vtt(str(subtitle_path))
            else:
                logger.warning(f"지원되지 않는 자막 형식: {subtitle_path.suffix}")
                return []
        except Exception as e:
            logger.error(f"자막 파싱 오류: {str(e)}", exc_info=True)
            return []
    
    async def _parse_srt(self, subtitle_path: str) -> List[Dict[str, Any]]:
        """
        SRT 파일 파싱
        
        Args:
            subtitle_path: SRT 파일 경로
            
        Returns:
            자막 데이터 리스트
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
            
            # 자막 메타데이터 추가
            video_id = Path(subtitle_path).stem
            self.indexer.index_subtitle(subtitle_path, video_id)
            self.indexer.save_index()
            
            logger.info(f"자막 {len(subtitle_data)}개 로드 완료: {subtitle_path}")
            return subtitle_data
            
        except Exception as e:
            logger.error(f"SRT 파일 파싱 오류: {str(e)}")
            return []
    
    async def _parse_vtt(self, subtitle_path: str) -> List[Dict[str, Any]]:
        """
        VTT 파일 파싱
        
        Args:
            subtitle_path: VTT 파일 경로
            
        Returns:
            자막 데이터 리스트
        """
        try:
            # VTT 파일을 SRT로 변환 후 처리
            srt_path = subtitle_path.with_suffix('.srt')
            await self._convert_vtt_to_srt(subtitle_path, srt_path)
            if srt_path.exists():
                return await self._parse_srt(str(srt_path))
            else:
                logger.warning(f"VTT에서 SRT로 변환 실패: {subtitle_path}")
                return []
            
        except Exception as e:
            logger.error(f"VTT 파일 파싱 오류: {str(e)}")
            return []
    
    async def _convert_vtt_to_srt(self, vtt_path: str, srt_path: str) -> bool:
        """
        VTT 자막 파일을 SRT 형식으로 변환
        
        Args:
            vtt_path: VTT 파일 경로
            srt_path: 출력 SRT 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            # FFmpeg로 변환
            cmd = [
                'ffmpeg',
                '-i', vtt_path,
                srt_path,
                '-y'  # 기존 파일 덮어쓰기
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"VTT에서 SRT 변환 오류: {stderr.decode()}")
                return False
                
            logger.info(f"VTT에서 SRT 변환 성공: {vtt_path} -> {srt_path}")
            return True
            
        except Exception as e:
            logger.error(f"VTT 변환 오류: {str(e)}")
            return False

    def index_and_translate(self, subtitle_path: str, video_id: str, video_path: Optional[str] = None, translation_output: Optional[str] = None) -> Dict[str, Any]:
        """
        자막 인덱싱과 번역을 함께 수행
        
        Args:
            subtitle_path: SRT 파일 경로
            video_id: 비디오 식별자
            video_path: 비디오 파일 경로 (옵션)
            translation_output: 번역 저장 경로 (옵션)
        
        Returns:
            인덱싱된 자막 데이터
        """
        # 인덱싱
        indexed = self.indexer.index_subtitle(subtitle_path, video_id, video_path)
        
        # 번역 경로 생성 (기본값)
        if translation_output is None:
            project_root = get_project_root()
            translations_dir = project_root / "backend" / settings.DEFAULT_SUBTITLE_DIR / "translations"
            ensure_dir_exists(str(translations_dir))
            translation_output = str(translations_dir / f"{video_id}_translations.json")
        
        # 번역 처리
        self.matcher.translate_subtitles(subtitle_path, output_path=translation_output)
        self.indexer.save_index()
        return indexed