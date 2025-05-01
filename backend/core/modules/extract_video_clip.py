#!/usr/bin/env python3
"""
파일: extract_video_clip.py
설명: 전체 길이의 비디오에서 시작/종료 타임스탬프를 기반으로 비디오 클립을 추출합니다
입력: 전체 비디오 경로, 시작 시간, 종료 시간, 출력 경로
출력: 추출된 비디오 클립 파일
라이브러리: ffmpeg-python, os, pathlib
업데이트: 
  - 2025-05-01: 초기 버전
  - 2025-05-01: 자막 인덱스 검색 및 다중 클립 추출 기능 추가
  - 2025-05-01: MKV 확장자 파일 지원 추가
  - 2025-05-01: 다양한 미디어 파일 포맷 지원 및 영어 음성 트랙 추출 기능 추가

이 모듈은 ffmpeg를 사용하여 비디오에서 특정 클립을 추출하며, 품질 보존, 포맷 선택, 자막 삽입 옵션을 제공합니다.
또한 subtitle_index.json을 사용하여 특정 표현을 검색하고 해당 클립들을 추출할 수 있습니다.
다중 음성 트랙이 있는 경우 영어 트랙을 자동으로 선택하는 기능을 제공합니다.
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, Union, Tuple, List

# 3rd party imports
import ffmpeg

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("video_clip.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoClipper:
    """전체 길이의 비디오에서 비디오 클립을 추출하는 클래스"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        VideoClipper 초기화
        
        인자:
            config_path: 기본 설정을 위한 config.yaml 경로(선택 사항)
        """
        self.config = {}
        if config_path:
            self.load_config(config_path)
        
        # 지원하는 미디어 파일 확장자 정의
        self.supported_video_formats = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.3gp']
        self.supported_audio_formats = ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a', '.wma']
    
    def load_config(self, config_path: str) -> None:
        """
        YAML 파일에서 설정 로드
        
        인자:
            config_path: config.yaml 파일 경로
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            logger.info(f"설정이 로드됨: {config_path}")
        except Exception as e:
            logger.error(f"설정 로드 중 오류 발생: {str(e)}")
    
    def get_media_info(self, media_path: str) -> Dict[str, Any]:
        """
        미디어 파일의 정보를 가져옵니다 (스트림, 코덱, 언어 등)
        
        인자:
            media_path: 미디어 파일 경로
            
        반환:
            미디어 정보 딕셔너리
        """
        try:
            probe = ffmpeg.probe(media_path)
            return probe
        except Exception as e:
            logger.error(f"미디어 정보 가져오기 중 오류 발생: {str(e)}")
            return {}
            
    def get_english_audio_stream(self, media_path: str) -> Optional[int]:
        """
        미디어 파일에서 영어 오디오 스트림 인덱스를 찾습니다
        
        인자:
            media_path: 미디어 파일 경로
            
        반환:
            영어 오디오 스트림 인덱스 또는 없을 경우 None
        """
        try:
            probe = self.get_media_info(media_path)
            
            # 오디오 스트림만 필터링
            audio_streams = [s for s in probe.get('streams', []) if s.get('codec_type') == 'audio']
            
            if not audio_streams:
                logger.warning(f"미디어 파일에서 오디오 스트림을 찾을 수 없음: {media_path}")
                return None
                
            # 영어 오디오 스트림 찾기 (tags.language 속성 확인)
            for i, stream in enumerate(audio_streams):
                tags = stream.get('tags', {})
                language = tags.get('language', '').lower()
                title = tags.get('title', '').lower()
                
                # 영어 스트림 확인 - language 태그가 영어 또는 제목에 "english"/"eng" 포함
                if language in ['eng', 'en'] or 'english' in title or 'eng' in title:
                    logger.info(f"영어 오디오 스트림 발견 (인덱스: {stream['index']}): {title}")
                    return stream['index']
            
            # 영어 스트림이 없으면 첫 번째 오디오 스트림 사용
            logger.warning("영어 오디오 스트림을 찾을 수 없어 첫 번째 오디오 스트림 사용")
            return audio_streams[0]['index']
            
        except Exception as e:
            logger.error(f"영어 오디오 스트림 가져오기 중 오류 발생: {str(e)}")
            return None
    
    def extract_clip(self, 
                     input_video: str, 
                     start_time: str, 
                     end_time: str, 
                     output_path: str,
                     quality: str = 'medium',
                     include_subtitles: bool = False,
                     english_audio_only: bool = True,
                     use_x265: bool = False) -> bool:
        """
        ffmpeg를 사용하여 미디어 파일에서 클립 추출
        
        인자:
            input_video: 입력 미디어 파일 경로
            start_time: 시작 시간 (형식: HH:MM:SS.mmm 또는 초)
            end_time: 종료 시간 (형식: HH:MM:SS.mmm 또는 초)
            output_path: 출력 클립 저장 경로
            quality: 비디오 품질 (low, medium, high, original)
            include_subtitles: 클립에 기존 자막 포함 여부
            english_audio_only: 다중 음성 트랙이 있는 경우 영어 트랙만 추출
            use_x265: x265 코덱 사용 여부 (H.265/HEVC)
            
        반환:
            성공 시 True, 실패 시 False
        """
        try:
            logger.info(f"클립 추출 중: {input_video}")
            logger.info(f"시간 범위: {start_time} ~ {end_time}")
            
            # Path 객체로 변환
            input_path = Path(input_video)
            output_path = Path(output_path)
            
            # 입력 파일이 존재하는지 확인
            if not input_path.exists():
                logger.error(f"입력 파일이 존재하지 않음: {input_path}")
                return False
                
            # 파일 확장자 확인
            file_ext = input_path.suffix.lower()
            is_video = file_ext in self.supported_video_formats
            is_audio = file_ext in self.supported_audio_formats
            
            if not (is_video or is_audio):
                logger.warning(f"지원되지 않는 파일 형식: {file_ext}")
                logger.warning(f"지원되는 비디오 형식: {self.supported_video_formats}")
                logger.warning(f"지원되는 오디오 형식: {self.supported_audio_formats}")
            
            # 출력 디렉토리 확인 및 생성
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 영어 오디오 스트림 찾기 (필요한 경우)
            english_stream = None
            if english_audio_only:
                english_stream = self.get_english_audio_stream(str(input_path))
                if english_stream is not None:
                    logger.info(f"영어 오디오 스트림 선택됨: 스트림 #{english_stream}")
            
            # ffmpeg 명령 생성
            # 영어 스트림이 선택된 경우 해당 스트림만 매핑
            if english_stream is not None:
                input_options = {'ss': start_time, 'to': end_time}
                input_stream = ffmpeg.input(str(input_path), **input_options)
                
                if is_video:
                    video_stream = input_stream.video
                    audio_stream = input_stream['a:{}'.format(english_stream - 1)]  # ffmpeg 인덱싱 조정
                else:
                    # 오디오 전용 파일
                    audio_stream = input_stream['a:{}'.format(english_stream - 1)]  # ffmpeg 인덱싱 조정
                    video_stream = None
            else:
                # 기본 스트림 사용
                input_stream = ffmpeg.input(str(input_path), ss=start_time, to=end_time)
                
                if is_video:
                    video_stream = input_stream.video
                    audio_stream = input_stream.audio
                else:
                    # 오디오 전용 파일
                    audio_stream = input_stream.audio
                    video_stream = None
            
            # 코덱 선택
            video_codec = 'libx265' if use_x265 else 'libx264'
            
            # 품질 설정
            if quality == 'original':
                # 원본에 가장 가까운 품질
                video_args = {
                    'c:v': video_codec,
                    'crf': 16 if use_x265 else 18,  # x265는 x264보다 낮은 CRF 값 사용
                    'preset': 'slow',
                    'x265-params' if use_x265 else 'x264-params': 'keyint=60:min-keyint=30'
                }
            elif quality == 'high':
                # 고품질
                video_args = {
                    'c:v': video_codec,
                    'crf': 20 if use_x265 else 18,
                    'preset': 'slow'
                }
            elif quality == 'low':
                # 저품질
                video_args = {
                    'c:v': video_codec,
                    'crf': 28 if use_x265 else 26,
                    'preset': 'veryfast'
                }
            else:  # 'medium' 또는 기본값
                # 중간 품질
                video_args = {
                    'c:v': video_codec,
                    'crf': 24 if use_x265 else 23,
                    'preset': 'medium'
                }
            
            # 오디오 설정
            audio_args = {'c:a': 'aac', 'b:a': '192k' if quality in ('high', 'original') else '128k'}
            
            # 출력 포맷에 따라 다른 처리
            output_ext = output_path.suffix.lower()
            is_output_audio = output_ext in self.supported_audio_formats
            
            # 자막 처리
            subtitle_stream = None
            if include_subtitles and is_video:
                subtitle_path = input_path.with_suffix('.srt')
                if subtitle_path.exists():
                    subtitle_stream = ffmpeg.input(str(subtitle_path))
            
            # 출력 설정
            if is_output_audio:
                # 오디오 전용 출력
                if audio_stream:
                    output = ffmpeg.output(
                        audio_stream,
                        str(output_path),
                        **audio_args,
                        map_metadata=0
                    )
                else:
                    logger.error("오디오 스트림을 찾을 수 없음")
                    return False
            else:
                # 비디오 출력 (오디오 포함)
                if video_stream and audio_stream:
                    if subtitle_stream and include_subtitles:
                        output = ffmpeg.output(
                            video_stream, 
                            audio_stream,
                            subtitle_stream,
                            str(output_path),
                            **video_args,
                            **audio_args,
                            map_metadata=0
                        )
                    else:
                        output = ffmpeg.output(
                            video_stream, 
                            audio_stream,
                            str(output_path),
                            **video_args,
                            **audio_args,
                            map_metadata=0
                        )
                elif video_stream:
                    # 비디오만 있는 경우
                    output = ffmpeg.output(
                        video_stream,
                        str(output_path),
                        **video_args,
                        map_metadata=0
                    )
                elif audio_stream:
                    # 오디오만 있는 경우
                    output = ffmpeg.output(
                        audio_stream,
                        str(output_path),
                        **audio_args,
                        map_metadata=0
                    )
            # 실제 ffmpeg 실행
            ffmpeg.run(output, overwrite_output=True)
            logger.info(f"클립 추출 완료: {output_path}")
            return True
        except Exception as e:
            logger.error(f"클립 추출 중 오류 발생: {str(e)}")
            return False
