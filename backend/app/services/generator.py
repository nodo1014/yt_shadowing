#!/usr/bin/env python3
"""
File: generator.py
Description: 반복 영상 및 썸네일 생성을 위한 코어 모듈
"""

import os
import json
import pysrt
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

from app.common.utils import setup_logger, ensure_dir_exists, get_temp_file

logger = setup_logger('generator_core', 'generator_core.log')

# 프로젝트 루트 디렉토리 기준 상대 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FONTS_DIR = PROJECT_ROOT / "data" / "fonts"

# 시스템 폰트와 커스텀 폰트 정의
DEFAULT_FONTS = {
    "en": str(FONTS_DIR / "NotoSansMono-Regular.ttf"),
    "en_bold": str(FONTS_DIR / "NotoSansMono-Bold.ttf"),
    "ko": str(FONTS_DIR / "NotoSansMono-Regular.ttf"),
    "ko_bold": str(FONTS_DIR / "NotoSansMono-Bold.ttf"),
}

# 시스템 폰트 대체
SYSTEM_FONTS = {
    "Arial": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Arial Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "Roboto": "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    "Roboto Bold": "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
}

# 폰트 로드 함수
def get_font_path(font_name="default", language="en", bold=False):
    """
    폰트 이름에 따라 적절한 폰트 파일 경로 반환
    
    Args:
        font_name: 폰트 이름
        language: 언어 코드 (en, ko)
        bold: 굵게 표시 여부
        
    Returns:
        폰트 파일 경로
    """
    # 시스템 폰트 확인
    if font_name in SYSTEM_FONTS:
        font_path = SYSTEM_FONTS[font_name]
        if bold and font_name + " Bold" in SYSTEM_FONTS:
            font_path = SYSTEM_FONTS[font_name + " Bold"]
        if os.path.exists(font_path):
            return font_path
    
    # 기본 폰트 사용
    if font_name == "default" or not os.path.exists(FONTS_DIR):
        key = language
        if bold:
            key += "_bold"
        
        # 기본 폰트 디렉토리 확인 및 생성
        if not os.path.exists(FONTS_DIR):
            os.makedirs(FONTS_DIR, exist_ok=True)
            logger.warning(f"폰트 디렉토리가 없어 생성함: {FONTS_DIR}")
        
        # 폰트 파일 존재 확인
        if key in DEFAULT_FONTS and os.path.exists(DEFAULT_FONTS[key]):
            return DEFAULT_FONTS[key]
        else:
            # 폰트 파일이 없으면 시스템 폰트 사용
            logger.warning(f"폰트 파일이 없어 시스템 폰트 사용: {DEFAULT_FONTS.get(key)}")
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    # 커스텀 폰트 사용
    font_path = str(FONTS_DIR / font_name)
    if os.path.exists(font_path):
        return font_path
    
    # 확장자 추가해서 확인
    for ext in ['.ttf', '.otf']:
        font_path_with_ext = font_path + ext
        if os.path.exists(font_path_with_ext):
            return font_path_with_ext
    
    # 모든 시도 실패 시 기본 시스템 폰트 반환
    logger.warning(f"요청한 폰트를 찾을 수 없음: {font_name}. 기본 폰트 사용")
    return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

class RepeatVideoGenerator:
    """반복 영상 생성 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        RepeatVideoGenerator 초기화
        
        Args:
            config: 설정 (옵션)
        """
        self.config = config or {}
        self.temp_files = []
        
        # 기본 설정
        self.default_config = {
            "repeat_count": 3,
            "subtitle_mode": ["no_subtitle", "en_ko", "en_ko"],
            "subtitle_style": {
                "font": "Arial",
                "fontsize": 48,
                "position": {"x": 50, "y": 600},
                "shadow": True,
                "bgcolor": "#00000080"
            },
            "tts": {
                "provider": "edge-tts",
                "voice": "en-US-GuyNeural",
                "speed": 1.0,
                "pitch": 0
            }
        }
        
        # 기본 설정에 사용자 설정 병합
        self._merge_config()
    
    def _merge_config(self) -> None:
        """설정 병합"""
        for key, default_value in self.default_config.items():
            if key not in self.config:
                self.config[key] = default_value
            elif isinstance(default_value, dict) and isinstance(self.config[key], dict):
                # 중첩 사전 병합
                for nested_key, nested_default in default_value.items():
                    if nested_key not in self.config[key]:
                        self.config[key][nested_key] = nested_default
    
    def cleanup(self) -> None:
        """임시 파일 정리"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"임시 파일 제거됨: {file_path}")
            except Exception as e:
                logger.warning(f"임시 파일 제거 실패 {file_path}: {str(e)}")
    
    async def generate_repeat_video(
        self, 
        video_path: str, 
        start_time: str, 
        end_time: str, 
        output_path: str,
        repeat_count: int = None,
        progress_callback = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        지정된 구간의 비디오를 여러 번 반복하는 영상 생성
        
        Args:
            video_path: 원본 비디오 경로
            start_time: 시작 시간 (00:00:00,000 형식)
            end_time: 종료 시간 (00:00:00,000 형식)
            output_path: 출력 파일 경로
            repeat_count: 반복 횟수 (기본값: 설정에서 가져옴)
            progress_callback: 진행률 콜백 함수
            
        Returns:
            (성공 여부, 결과 정보)
        """
        try:
            logger.info(f"반복 영상 생성 시작: {video_path}, {start_time} ~ {end_time}")
            
            if repeat_count is None:
                repeat_count = self.config.get("repeat_count", 3)
            
            # 입력 파일 존재 확인
            if not os.path.exists(video_path):
                logger.error(f"입력 파일이 존재하지 않습니다: {video_path}")
                return False, {"error": f"입력 파일이 존재하지 않습니다: {video_path}"}
            
            # 출력 디렉토리 확인 및 생성
            output_dir = os.path.dirname(output_path)
            ensure_dir_exists(output_dir)
            
            # 시간 형식 변환 (콤마를 점으로 변경)
            start_time_fixed = start_time.replace(',', '.')
            end_time_fixed = end_time.replace(',', '.')
            
            # 임시 파일 경로
            temp_segment = get_temp_file(prefix="segment_", suffix=".mp4")
            self.temp_files.append(temp_segment)
            
            # 반복할 구간 추출
            extract_cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ss", start_time_fixed,
                "-to", end_time_fixed,
                "-c:v", "libx264", "-c:a", "aac",
                "-preset", "fast",
                temp_segment
            ]
            
            logger.debug(f"구간 추출 명령: {' '.join(extract_cmd)}")
            
            if progress_callback:
                await progress_callback(0.1, "반복할 구간 추출 중...")
            
            # 셸 주입 공격 방지를 위해 쉘을 사용하지 않고 직접 실행
            subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
            
            if not os.path.exists(temp_segment) or os.path.getsize(temp_segment) == 0:
                logger.error("추출된 구간 파일이 생성되지 않았습니다")
                return False, {"error": "추출된 구간 파일이 생성되지 않았습니다"}
            
            # 파일 목록 생성
            list_file = get_temp_file(prefix="filelist_", suffix=".txt")
            self.temp_files.append(list_file)
            
            with open(list_file, 'w') as f:
                for _ in range(repeat_count):
                    # 경로에 작은따옴표가 아닌 큰따옴표 사용 (FFmpeg concat 요구사항)
                    normalized_path = temp_segment.replace('\\', '/')
                    f.write(f"file '{normalized_path}'\n")
            
            if progress_callback:
                await progress_callback(0.4, f"반복 영상 생성 중... ({repeat_count}회 반복)")
            
            # 반복 영상 생성
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                output_path
            ]
            
            logger.debug(f"영상 합치기 명령: {' '.join(concat_cmd)}")
            subprocess.run(concat_cmd, check=True, capture_output=True, text=True)
            
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error("최종 반복 영상 파일이 생성되지 않았습니다")
                return False, {"error": "최종 반복 영상 파일이 생성되지 않았습니다"}
            
            # 임시 파일 정리
            self.cleanup()
            
            if progress_callback:
                await progress_callback(1.0, "반복 영상 생성 완료")
            
            logger.info(f"반복 영상 생성 완료: {output_path}")
            return True, {
                "output_path": output_path, 
                "repeat_count": repeat_count,
                "duration": self._get_video_duration(output_path)
            }
            
        except Exception as e:
            logger.error(f"반복 영상 생성 실패: {str(e)}", exc_info=True)
            # 임시 파일 정리
            self.cleanup()
            return False, {"error": str(e)}
    
    def _get_video_duration(self, video_path: str) -> float:
        """
        비디오 파일의 재생 시간을 초 단위로 반환
        
        Args:
            video_path: 비디오 파일 경로
            
        Returns:
            재생 시간 (초)
        """
        try:
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "json", 
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except Exception as e:
            logger.error(f"비디오 재생 시간 확인 실패: {str(e)}")
            return 0.0
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        시간 문자열을 초로 변환
        
        Args:
            time_str: 시간 문자열 (00:00:00,000 형식)
            
        Returns:
            초 단위 시간
        """
        try:
            h, m, s = time_str.replace(',', '.').split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)
        except Exception as e:
            logger.error(f"시간 변환 실패: {str(e)}")
            return 0.0
    
class ThumbnailGenerator:
    """썸네일 생성 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        ThumbnailGenerator 초기화
        
        Args:
            config: 설정 (옵션)
        """
        self.config = config or {}
        
        # 기본 설정
        self.default_config = {
            "width": 1280,
            "height": 720,
            "background_color": "#000000",
            "text_color": "#FFFFFF",
            "subtitle_color": "#DDDDDD",
            "font": get_font_path("default", "en"),
            "font_ko": get_font_path("default", "ko"),
            "font_size": 72,
            "subtitle_size": 36,
            "margin": 40,
            "line_spacing": 20,
            "shadow": {
                "enabled": True,
                "color": "#000000",
                "offset": [2, 2],
                "blur": 5
            },
            "templates": {
                "basic": {
                    "background_color": "#000000",
                    "text_color": "#FFFFFF",
                    "text_position": [0.5, 0.4]
                },
                "title": {
                    "background_color": "#0F1829",
                    "text_color": "#FFFFFF",
                    "accent_color": "#FF4B4B",
                    "text_position": [0.5, 0.5]
                },
                # 영어 학습용 새 템플릿 추가
                "english_vocab": {
                    "background_color": "#2C3E50",
                    "text_color": "#ECF0F1",
                    "subtitle_color": "#E74C3C",
                    "accent_color": "#3498DB",
                    "text_position": [0.5, 0.4],
                    "font_size": 80,
                    "subtitle_size": 48
                },
                "shadowing": {
                    "background_color": "#34495E",
                    "text_color": "#F1C40F",
                    "subtitle_color": "#BDC3C7",
                    "border": {
                        "enabled": True,
                        "color": "#F39C12",
                        "width": 4
                    },
                    "text_position": [0.5, 0.5],
                    "text_align": "center"
                },
                "conversation": {
                    "background_color": "#1E3A8A",
                    "text_color": "#FFFFFF",
                    "subtitle_color": "#FBBF24",
                    "speech_bubble": True,
                    "bubble_color": "#3B82F6",
                    "text_position": [0.5, 0.45]
                },
                "pronunciation": {
                    "background_color": "#481449",
                    "gradient": True,
                    "gradient_end": "#27104E",
                    "text_color": "#FFFFFF",
                    "subtitle_color": "#F472B6",
                    "text_position": [0.5, 0.35],
                    "phonetic": True,
                    "phonetic_color": "#38BDF8"
                },
                "quiz": {
                    "background_color": "#065F46",
                    "text_color": "#FFFFFF",
                    "subtitle_color": "#A7F3D0",
                    "box": {
                        "enabled": True,
                        "color": "#047857",
                        "padding": 20,
                        "radius": 10
                    },
                    "text_position": [0.5, 0.4]
                }
            }
        }
        
        # 기본 설정에 사용자 설정 병합
        self._merge_config()
        
    def _merge_config(self) -> None:
        """설정 병합"""
        for key, default_value in self.default_config.items():
            if key not in self.config:
                self.config[key] = default_value
            elif isinstance(default_value, dict) and isinstance(self.config[key], dict):
                # 중첩 사전 병합
                for nested_key, nested_default in default_value.items():
                    if nested_key not in self.config[key]:
                        self.config[key][nested_key] = nested_default
    
    def generate_thumbnail(
        self, 
        video_path: str, 
        time_pos: str, 
        output_path: str,
        text: Optional[str] = None,
        subtitle: Optional[str] = None,
        template: str = "basic"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        비디오에서 지정된 시간 위치의 썸네일 생성
        
        Args:
            video_path: 비디오 파일 경로
            time_pos: 썸네일 추출 시간 위치 (00:00:00 형식)
            output_path: 출력 이미지 파일 경로
            text: 오버레이할 텍스트 (옵션)
            subtitle: 하단에 표시할 자막 텍스트 (옵션)
            template: 사용할 템플릿 이름
            
        Returns:
            (성공 여부, 결과 정보)
        """
        try:
            logger.info(f"썸네일 생성 시작: {video_path}, 위치: {time_pos}, 템플릿: {template}")
            
            # 입력 파일 존재 확인
            if not os.path.exists(video_path):
                logger.error(f"입력 파일이 존재하지 않습니다: {video_path}")
                return False, {"error": f"입력 파일이 존재하지 않습니다: {video_path}"}
            
            # 출력 디렉토리 확인 및 생성
            output_dir = os.path.dirname(output_path)
            ensure_dir_exists(output_dir)
            
            # 시간 형식 변환 (콤마를 점으로 변경)
            time_pos_fixed = time_pos.replace(',', '.')
            
            # 템플릿 설정 가져오기
            if template not in self.config["templates"]:
                logger.warning(f"템플릿 '{template}'이(가) 없습니다. 기본 템플릿을 사용합니다.")
                template = "basic"
                
            template_config = self.config["templates"][template]
            
            # 영어 텍스트용 폰트와 한글 텍스트용 폰트 설정
            en_font = self.config['font']
            ko_font = self.config.get('font_ko', self.config['font'])
            
            # FFmpeg 명령 구성
            temp_frame = get_temp_file(prefix="thumbnail_frame_", suffix=".jpg")
            
            # 프레임 추출
            extract_cmd = [
                "ffmpeg", "-y",
                "-ss", time_pos_fixed,
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={self.config['width']}:{self.config['height']}",
                temp_frame
            ]
            
            logger.debug(f"프레임 추출 명령: {' '.join(extract_cmd)}")
            subprocess.run(extract_cmd, check=True, capture_output=True, text=True)
            
            if not os.path.exists(temp_frame) or os.path.getsize(temp_frame) == 0:
                logger.error("프레임 추출에 실패했습니다")
                return False, {"error": "프레임 추출에 실패했습니다"}
            
            # 임시 파일에 복합 필터 구성
            filter_file = get_temp_file(prefix="filter_", suffix=".txt")
            
            # 기본 필터: 배경에 약간의 어두움 추가
            filter_complex = [
                f"[0:v]format=rgb24,boxblur=20,setsar=1[bg]",
                f"[bg]colorlevels=rimax=0.7:gimax=0.7:bimax=0.7[darken]"
            ]
            
            # 템플릿에 따른 배경 필터 추가
            bg_color = template_config.get('background_color', self.config['background_color'])
            
            # 그라데이션 배경 처리
            if template_config.get('gradient', False):
                gradient_end = template_config.get('gradient_end', '#000000')
                filter_complex.append(
                    f"color=c={bg_color}:s={self.config['width']}x{self.config['height']},"
                    f"gradients=s={self.config['width']}x{self.config['height']}:c0={bg_color}:c1={gradient_end}:"
                    f"x0=0:y0=0:x1={self.config['width']}:y1={self.config['height']}[bg_gradient]"
                )
                filter_complex.append(f"[darken][bg_gradient]overlay=format=auto:alpha=0.9[base]")
            else:
                # 단색 배경
                filter_complex.append(
                    f"color=c={bg_color}:s={self.config['width']}x{self.config['height']}[bg_color]"
                )
                filter_complex.append(f"[darken][bg_color]overlay=format=auto:alpha=0.85[base]")
            
            # 텍스트와 자막 추가
            if text:
                # 텍스트 위치 계산
                text_pos = template_config.get('text_position', [0.5, 0.4])
                text_x = f"(w-text_w)*{text_pos[0]}"
                text_y = f"(h-text_h)*{text_pos[0]}"
                
                # 폰트 크기
                font_size = template_config.get('font_size', self.config['font_size'])
                
                # 텍스트 색상
                text_color = template_config.get('text_color', self.config['text_color'])
                
                # 한글 감지 및 적절한 폰트 선택 (간단한 한글 감지)
                has_korean = any('\uAC00' <= char <= '\uD7A3' for char in text)
                font_path = ko_font if has_korean else en_font
                
                # 텍스트에서 특수 문자 이스케이프
                escaped_text = text.replace("'", "\\'").replace(":", "\\:")
                
                # 그림자 추가
                if self.config["shadow"]["enabled"]:
                    shadow_offset_x = self.config["shadow"]["offset"][0]
                    shadow_offset_y = self.config["shadow"]["offset"][1]
                    shadow_color = self.config["shadow"]["color"]
                    
                    filter_complex.append(
                        f"[base]drawtext=text='{escaped_text}':fontsize={font_size}:"
                        f"fontcolor={shadow_color}:fontfile='{font_path}':"
                        f"x={text_x}+{shadow_offset_x}:y={text_y}+{shadow_offset_y}[shadow]"
                    )
                    
                    # 상자 배경이 있는 경우
                    if template_config.get('box', {}).get('enabled', False):
                        box_color = template_config['box']['color']
                        box_padding = template_config['box']['padding']
                        box_radius = template_config['box'].get('radius', 0)
                        
                        filter_complex.append(
                            f"[shadow]drawbox=x={text_x}-{box_padding}-text_w/2:"
                            f"y={text_y}-{box_padding}-text_h/2:"
                            f"w=text_w+{box_padding*2}:h=text_h+{box_padding*2}:"
                            f"color={box_color}:t=fill:r={box_radius}[box_bg]"
                        )
                        filter_complex.append(
                            f"[box_bg]drawtext=text='{escaped_text}':fontsize={font_size}:"
                            f"fontcolor={text_color}:fontfile='{font_path}':"
                            f"x={text_x}:y={text_y}[main_text]"
                        )
                    else:
                        filter_complex.append(
                            f"[shadow]drawtext=text='{escaped_text}':fontsize={font_size}:"
                            f"fontcolor={text_color}:fontfile='{font_path}':"
                            f"x={text_x}:y={text_y}[main_text]"
                        )
                else:
                    # 상자 배경이 있는 경우
                    if template_config.get('box', {}).get('enabled', False):
                        box_color = template_config['box']['color']
                        box_padding = template_config['box']['padding']
                        box_radius = template_config['box'].get('radius', 0)
                        
                        filter_complex.append(
                            f"[base]drawbox=x={text_x}-{box_padding}-text_w/2:"
                            f"y={text_y}-{box_padding}-text_h/2:"
                            f"w=text_w+{box_padding*2}:h=text_h+{box_padding*2}:"
                            f"color={box_color}:t=fill:r={box_radius}[box_bg]"
                        )
                        filter_complex.append(
                            f"[box_bg]drawtext=text='{escaped_text}':fontsize={font_size}:"
                            f"fontcolor={text_color}:fontfile='{font_path}':"
                            f"x={text_x}:y={text_y}[main_text]"
                        )
                    else:
                        filter_complex.append(
                            f"[base]drawtext=text='{escaped_text}':fontsize={font_size}:"
                            f"fontcolor={text_color}:fontfile='{font_path}':"
                            f"x={text_x}:y={text_y}[main_text]"
                        )
                
                last_filter = "main_text"
            else:
                last_filter = "base"
            
            # 자막 텍스트 추가
            if subtitle:
                # 자막 폰트 크기
                subtitle_size = template_config.get('subtitle_size', self.config['subtitle_size'])
                
                # 자막 색상
                subtitle_color = template_config.get('subtitle_color', self.config['subtitle_color'])
                
                # 자막 위치 (하단)
                subtitle_y = f"h-th-{self.config['margin']}"
                
                # 한글 감지 및 적절한 폰트 선택
                has_korean_sub = any('\uAC00' <= char <= '\uD7A3' for char in subtitle)
                sub_font_path = ko_font if has_korean_sub else en_font
                
                # 자막에서 특수 문자 이스케이프
                escaped_subtitle = subtitle.replace("'", "\\'").replace(":", "\\:")
                
                # 테두리가 있는 경우
                if template_config.get('border', {}).get('enabled', False):
                    border_color = template_config['border']['color']
                    border_width = template_config['border']['width']
                    
                    filter_complex.append(
                        f"[{last_filter}]drawtext=text='{escaped_subtitle}':fontsize={subtitle_size}:"
                        f"bordercolor={border_color}:borderw={border_width}:"
                        f"fontcolor={subtitle_color}:fontfile='{sub_font_path}':"
                        f"x=(w-text_w)/2:y={subtitle_y}[final]"
                    )
                else:
                    # 그림자 처리
                    if self.config["shadow"]["enabled"]:
                        shadow_offset_x = self.config["shadow"]["offset"][0]
                        shadow_offset_y = self.config["shadow"]["offset"][1]
                        shadow_color = self.config["shadow"]["color"]
                        
                        filter_complex.append(
                            f"[{last_filter}]drawtext=text='{escaped_subtitle}':fontsize={subtitle_size}:"
                            f"fontcolor={shadow_color}:fontfile='{sub_font_path}':"
                            f"x=(w-text_w)/2+{shadow_offset_x}:y={subtitle_y}+{shadow_offset_y}[sub_shadow]"
                        )
                        
                        filter_complex.append(
                            f"[sub_shadow]drawtext=text='{escaped_subtitle}':fontsize={subtitle_size}:"
                            f"fontcolor={subtitle_color}:fontfile='{sub_font_path}':"
                            f"x=(w-text_w)/2:y={subtitle_y}[final]"
                        )
                    else:
                        filter_complex.append(
                            f"[{last_filter}]drawtext=text='{escaped_subtitle}':fontsize={subtitle_size}:"
                            f"fontcolor={subtitle_color}:fontfile='{sub_font_path}':"
                            f"x=(w-text_w)/2:y={subtitle_y}[final]"
                        )
                
                last_filter = "final"
            
            # 필터 파일 작성
            with open(filter_file, 'w') as f:
                f.write(';\n'.join(filter_complex))
            
            # 최종 이미지 생성
            cmd = [
                "ffmpeg", "-y",
                "-i", temp_frame,
                "-filter_complex_script", filter_file,
                "-map", f"[{last_filter}]",
                "-frames:v", "1",
                output_path
            ]
            
            logger.debug(f"썸네일 생성 명령: {' '.join(cmd)}")
            
            # 셸 주입 공격 방지를 위해 쉘을 사용하지 않고 직접 실행
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # 임시 파일 정리
            for temp_file in [temp_frame, filter_file]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error("썸네일 파일이 생성되지 않았습니다")
                return False, {"error": "썸네일 파일이 생성되지 않았습니다"}
            
            logger.info(f"썸네일 생성 완료: {output_path}")
            return True, {"output_path": output_path}
            
        except Exception as e:
            logger.error(f"썸네일 생성 실패: {str(e)}", exc_info=True)
            # 임시 파일 정리
            for temp_file in [temp_frame, filter_file]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            return False, {"error": str(e)}


# ClipGenerator 클래스 추가
class ClipGenerator:
    """자막 기반 클립 생성 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = setup_logger("clip_generator", "clip_generator.log")

    def generate_clip(self, video_path: str, start: float, end: float, output_path: str) -> bool:
        """
        FFmpeg를 사용하여 클립 생성

        Args:
            video_path: 원본 영상 경로
            start: 시작 시간 (초)
            end: 종료 시간 (초)
            output_path: 출력 파일 경로

        Returns:
            성공 여부
        """
        try:
            ensure_dir_exists(os.path.dirname(output_path))
            command = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-ss", str(start),
                "-to", str(end),
                "-c:v", "copy",
                "-c:a", "copy",
                output_path
            ]
            subprocess.run(command, check=True)
            self.logger.info(f"클립 생성 성공: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"클립 생성 실패: {e}")
            return False