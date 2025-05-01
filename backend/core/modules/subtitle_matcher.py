#!/usr/bin/env python3
"""
파일: subtitle_matcher.py
설명: 영어 자막을 한국어 번역과 매칭하고 언어 학습을 위한 이중 자막을 생성합니다
입력: SRT 자막 파일, 번역 옵션
출력: 영어-한국어 자막 쌍이 포함된 JSON 파일
라이브러리: pysrt, openai, translators, json, os, pathlib
업데이트: 
  - 2025-05-01: 초기 버전

이 모듈은 영어 자막 파일을 처리하여 각 문장에 대한 한국어 번역을 생성하고 
결과 이중 자막을 JSON 형식으로 저장합니다. 여러 번역 서비스(OpenAI, Google, Papago)를
지원하여 번역 품질을 최적화합니다.
"""

import os
import re
import json
import time
import pysrt
import logging
import argparse
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("subtitle_matcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 선택적 써드파티 임포트
try:
    import translators as ts
    TRANSLATORS_AVAILABLE = True
except ImportError:
    logger.warning("translators 패키지를 찾을 수 없습니다. Google/Papago 번역을 사용할 수 없습니다")
    TRANSLATORS_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("openai 패키지를 찾을 수 없습니다. OpenAI/ChatGPT 번역을 사용할 수 없습니다")
    OPENAI_AVAILABLE = False

class SubtitleMatcher:
    """자막 처리 및 번역 클래스"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        SubtitleMatcher 초기화
        
        인자:
            config_path: 설정 파일 경로 (선택 사항)
        """
        self.config = {
            "translation_service": "openai",  # openai, google, papago
            "openai_model": "gpt-3.5-turbo",
            "batch_size": 10,  # 일괄 번역할 자막 수
            "max_retries": 3,
            "retry_delay": 5,  # 초 단위
            "temperature": 0.3,
            "translate_all": False  # 기존 번역이 있어도 모두 번역
        }
        
        # 설정 파일에서 로드
        if config_path:
            self._load_config(config_path)
        
        # API 키 환경 변수 확인
        self._init_api_keys()
    
    def _load_config(self, config_path: str) -> None:
        """
        YAML 파일에서 설정 로드
        
        인자:
            config_path: 설정 파일 경로
        """
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 번역기 설정 업데이트
            if 'matcher' in config:
                self.config.update(config['matcher'])
            elif 'translation' in config:
                self.config.update(config['translation'])
            else:
                self.config.update(config)
                
            logger.info(f"설정을 로드함: {config_path}")
            
        except ImportError:
            logger.warning("PyYAML 패키지를 찾을 수 없습니다. 기본 설정을 사용합니다")
        except Exception as e:
            logger.error(f"설정 파일 로드 중 오류 발생: {str(e)}")
    
    def _init_api_keys(self) -> None:
        """환경 변수에서 API 키 초기화"""
        # OpenAI API 키
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        if OPENAI_AVAILABLE and self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        # Papago API 키
        self.papago_client_id = os.environ.get('PAPAGO_CLIENT_ID', '')
        self.papago_client_secret = os.environ.get('PAPAGO_CLIENT_SECRET', '')
    
    def clean_text(self, text: str) -> str:
        """
        HTML 태그 제거 및 자막 텍스트 정리
        
        인자:
            text: 원본 자막 텍스트
            
        반환:
            정리된 텍스트
        """
        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', text)
        # 공백 정리
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
    
    def process_subtitle_file(self, subtitle_path: str) -> List[Dict[str, Any]]:
        """
        SRT 자막 파일을 처리하고 자막 항목 추출
        
        인자:
            subtitle_path: SRT 파일 경로
            
        반환:
            타임스탬프와 텍스트가 있는 자막 항목 목록
        """
        try:
            logger.info(f"자막 파일 처리 중: {subtitle_path}")
            subs = pysrt.open(subtitle_path, encoding='utf-8')
            
            subtitle_items = []
            for sub in subs:
                text = self.clean_text(sub.text)
                if not text:  # 빈 자막 건너뛰기
                    continue
                
                start_time = sub.start.to_time()
                end_time = sub.end.to_time()
                
                subtitle_items.append({
                    "index": sub.index,
                    "start": str(start_time),
                    "end": str(end_time),
                    "text": text,
                    "translation": ""
                })
            
            logger.info(f"{len(subtitle_items)}개의 자막 항목 처리됨")
            return subtitle_items
            
        except Exception as e:
            logger.error(f"자막 파일 처리 중 오류 발생: {str(e)}")
            return []
    
    def translate_with_openai(self, texts: List[str], target_language: str = "한국어") -> List[str]:
        """
        OpenAI API를 사용하여 텍스트 번역
        
        인자:
            texts: 번역할 텍스트 목록
            target_language: 대상 언어
            
        반환:
            번역된 텍스트 목록
        """
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI 패키지가 설치되지 않음")
            return [""] * len(texts)
            
        if not self.openai_api_key:
            logger.error("OpenAI API 키가 설정되지 않음")
            return [""] * len(texts)
        
        try:
            logger.info(f"{len(texts)}개 자막을 OpenAI로 번역 중...")
            
            # 번역을 위한 명령
            system_prompt = f"""영어 자막을 {target_language}로 번역하십시오. 
자연스럽고 정확한 번역을 제공하고, 공식적인 번역 톤을 유지하십시오. 
문화적 뉘앙스를 고려하고 필요한 경우 영어 표현에 맞는 적절한 대상 언어 구절을 사용하십시오.
입력 줄의 수와 정확히 같은 수의 번역된 줄을 반환하십시오."""
            
            # 일반적인 오류를 방지하기 위해 텍스트를 일괄 처리하는 방법 지정
            prompt = "\n".join([f"{i+1}. {text}" for i, text in enumerate(texts)])
            
            response = openai.chat.completions.create(
                model=self.config["openai_model"],
                temperature=self.config["temperature"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 응답 처리
            result = response.choices[0].message.content
            
            # 결과에서 개별 번역 추출
            translations = []
            lines = result.strip().split('\n')
            
            for line in lines:
                # 번호 접두사 제거 (예: "1. 번역된 텍스트" → "번역된 텍스트")
                match = re.match(r'^\d+\.\s*(.*)', line)
                if match:
                    translations.append(match.group(1))
                else:
                    translations.append(line)
            
            # 입력 텍스트 수와 일치하도록 조정
            while len(translations) < len(texts):
                translations.append("")
            
            return translations[:len(texts)]
            
        except Exception as e:
            logger.error(f"OpenAI 번역 중 오류 발생: {str(e)}")
            return [""] * len(texts)
    
    def translate_with_google(self, texts: List[str], target_language: str = "ko") -> List[str]:
        """
        Google 번역 API를 사용하여 텍스트 번역
        
        인자:
            texts: 번역할 텍스트 목록
            target_language: 대상 언어 코드
            
        반환:
            번역된 텍스트 목록
        """
        if not TRANSLATORS_AVAILABLE:
            logger.error("translators 패키지가 설치되지 않음")
            return [""] * len(texts)
        
        try:
            logger.info(f"{len(texts)}개 자막을 Google 번역으로 번역 중...")
            translations = []
            
            for text in texts:
                for attempt in range(self.config["max_retries"]):
                    try:
                        translation = ts.google(text, from_language='en', to_language=target_language)
                        translations.append(translation)
                        break
                    except Exception as e:
                        logger.warning(f"Google 번역 시도 중 오류 발생({attempt+1}/{self.config['max_retries']}): {str(e)}")
                        if attempt < self.config["max_retries"] - 1:
                            time.sleep(self.config["retry_delay"])
                        else:
                            logger.error(f"최대 재시도 횟수를 초과하여 번역 실패: {text}")
                            translations.append("")
            
            return translations
            
        except Exception as e:
            logger.error(f"Google 번역 중 오류 발생: {str(e)}")
            return [""] * len(texts)
    
    def translate_with_papago(self, texts: List[str], target_language: str = "ko") -> List[str]:
        """
        Papago 번역 API를 사용하여 텍스트 번역
        
        인자:
            texts: 번역할 텍스트 목록
            target_language: 대상 언어 코드
            
        반환:
            번역된 텍스트 목록
        """
        if not TRANSLATORS_AVAILABLE:
            logger.error("translators 패키지가 설치되지 않음")
            return [""] * len(texts)
            
        if not self.papago_client_id or not self.papago_client_secret:
            logger.error("Papago API 자격 증명이 설정되지 않음")
            return self.translate_with_google(texts, target_language)  # Google로 폴백
        
        try:
            logger.info(f"{len(texts)}개 자막을 Papago로 번역 중...")
            translations = []
            
            for text in texts:
                for attempt in range(self.config["max_retries"]):
                    try:
                        translation = ts.papago(
                            text, 
                            from_language='en', 
                            to_language=target_language,
                            client_id=self.papago_client_id,
                            secret_key=self.papago_client_secret
                        )
                        translations.append(translation)
                        break
                    except Exception as e:
                        logger.warning(f"Papago 번역 시도 중 오류 발생({attempt+1}/{self.config['max_retries']}): {str(e)}")
                        if attempt < self.config["max_retries"] - 1:
                            time.sleep(self.config["retry_delay"])
                        else:
                            logger.error(f"최대 재시도 횟수를 초과하여 번역 실패: {text}")
                            translations.append("")
            
            return translations
            
        except Exception as e:
            logger.error(f"Papago 번역 중 오류 발생: {str(e)}")
            # Google로 폴백
            logger.info("Google 번역으로 폴백합니다")
            return self.translate_with_google(texts, target_language)
    
    def batch_translate(self, subtitle_items: List[Dict[str, Any]], 
                       existing_translations: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        자막 항목 일괄 번역
        
        인자:
            subtitle_items: 자막 항목 목록
            existing_translations: 기존 번역(있는 경우)
            
        반환:
            번역된 텍스트가 포함된 자막 항목 목록
        """
        # 기존 번역이 있으면 먼저 로드
        if existing_translations and not self.config["translate_all"]:
            logger.info("기존 번역 적용 중")
            for i, item in enumerate(subtitle_items):
                index_str = str(item["index"])
                if index_str in existing_translations:
                    subtitle_items[i]["translation"] = existing_translations[index_str]
        
        # 번역이 필요한 항목만 필터링
        to_translate = [item for item in subtitle_items if not item["translation"]]
        
        if not to_translate:
            logger.info("번역이 필요한 자막이 없습니다")
            return subtitle_items
            
        logger.info(f"{len(to_translate)}개 자막 번역 필요")
        
        # 일괄 처리 크기
        batch_size = self.config["batch_size"]
        translated_items = []
        
        # 번역할 텍스트 배치 처리
        for i in range(0, len(to_translate), batch_size):
            batch = to_translate[i:i+batch_size]
            texts = [item["text"] for item in batch]
            
            # 선택한 서비스로 번역
            if self.config["translation_service"] == "openai":
                translations = self.translate_with_openai(texts)
            elif self.config["translation_service"] == "papago":
                translations = self.translate_with_papago(texts)
            else:  # 기본값은 google
                translations = self.translate_with_google(texts)
            
            # 번역 결과 적용
            for j, translation in enumerate(translations):
                if i + j < len(to_translate):
                    batch[j]["translation"] = translation
                    
            translated_items.extend(batch)
            
            # API 제한 초과를 방지하기 위한 짧은 대기
            if i + batch_size < len(to_translate):
                time.sleep(1)
        
        # 전체 자막 항목 업데이트
        translated_dict = {item["index"]: item for item in translated_items}
        
        for i, item in enumerate(subtitle_items):
            if item["index"] in translated_dict:
                subtitle_items[i]["translation"] = translated_dict[item["index"]]["translation"]
        
        return subtitle_items
    
    def save_translations(self, subtitle_items: List[Dict[str, Any]], output_path: str) -> bool:
        """
        번역된 자막을 JSON 파일로 저장
        
        인자:
            subtitle_items: 번역된 자막 항목 목록
            output_path: 출력 JSON 파일 경로
            
        반환:
            성공 시 True, 실패 시 False
        """
        try:
            # 출력 디렉토리 생성
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 출력 데이터 구성
            output_data = {
                str(item["index"]): item["translation"] for item in subtitle_items
            }
            
            # JSON 파일로 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"번역이 다음 위치에 저장됨: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"번역 저장 중 오류 발생: {str(e)}")
            return False
    
    def load_existing_translations(self, json_path: str) -> Dict[str, str]:
        """
        기존 번역 JSON 파일 로드
        
        인자:
            json_path: 기존 번역 JSON 파일 경로
            
        반환:
            자막 인덱스를 키로, 번역을 값으로 하는 사전
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"기존 번역 로드 중 오류 발생: {str(e)}")
            return {}
    
    def process_subtitles(self, subtitle_path: str, output_path: str) -> bool:
        """
        자막 파일을 처리하고 번역
        
        인자:
            subtitle_path: SRT 자막 파일 경로
            output_path: 출력 JSON 파일 경로
            
        반환:
            성공 시 True, 실패 시 False
        """
        try:
            # 기존 번역 확인
            existing_translations = {}
            if Path(output_path).exists() and not self.config["translate_all"]:
                logger.info(f"기존 번역 파일 로드 중: {output_path}")
                existing_translations = self.load_existing_translations(output_path)
            
            # 자막 처리
            subtitle_items = self.process_subtitle_file(subtitle_path)
            if not subtitle_items:
                logger.error("처리할 자막 항목 없음")
                return False
                
            # 번역
            translated_items = self.batch_translate(subtitle_items, existing_translations)
            
            # 결과 저장
            return self.save_translations(translated_items, output_path)
            
        except Exception as e:
            logger.error(f"자막 처리 중 오류 발생: {str(e)}")
            return False

def main():
    """명령줄에서 자막 매처 실행"""
    parser = argparse.ArgumentParser(description='영어 자막에 한국어 번역 매칭')
    parser.add_argument('--subtitle', '-s', type=str, required=True,
                       help='입력 SRT 자막 파일 경로')
    parser.add_argument('--output', '-o', type=str, required=True,
                       help='출력 JSON 파일 경로')
    parser.add_argument('--config', '-c', type=str,
                       help='설정 파일 경로')
    parser.add_argument('--service', type=str, choices=['openai', 'google', 'papago'],
                       help='사용할 번역 서비스')
    parser.add_argument('--translate-all', action='store_true',
                       help='기존 번역을 무시하고 모든 자막 번역')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='일괄 번역할 자막 수')
    
    args = parser.parse_args()
    
    # 매처 초기화
    matcher = SubtitleMatcher(args.config)
    
    # 명령줄 인수로 설정 업데이트
    if args.service:
        matcher.config["translation_service"] = args.service
    if args.translate_all:
        matcher.config["translate_all"] = True
    if args.batch_size:
        matcher.config["batch_size"] = args.batch_size
    
    # 자막 처리
    success = matcher.process_subtitles(args.subtitle, args.output)
    
    if success:
        print(f"자막이 성공적으로 처리되어 다음 위치에 저장됨: {args.output}")
        return 0
    else:
        print("자막 처리 실패")
        return 1

if __name__ == "__main__":
    main()
