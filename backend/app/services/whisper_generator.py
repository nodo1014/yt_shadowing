#!/usr/bin/env python3
"""
File: whisper_generator.py
Description: OpenAI Whisper를 사용한 자막 생성 기능
"""

import os
import asyncio
import tempfile
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple

from app.common.utils import setup_logger, ensure_dir_exists

logger = setup_logger('whisper_generator', 'whisper_generator.log')

class WhisperGenerator:
    """Whisper를 이용한 자막 생성 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        WhisperGenerator 초기화
        
        Args:
            config: 설정 (옵션)
        """
        self.config = config or {}
        self.available_models = ["tiny", "base", "small", "medium", "large"]
        self.model_sizes = {
            "tiny": "39M",
            "base": "74M",
            "small": "244M",
            "medium": "769M",
            "large": "1.5GB"
        }
        self.model_processing_speed = {
            "tiny": "32x",
            "base": "16x",
            "small": "6x",
            "medium": "2x",
            "large": "1x"
        }
    
    async def generate_subtitle(self, 
                               video_path: str, 
                               output_path: str, 
                               model: str = "tiny",
                               language: str = "en") -> Tuple[bool, Dict[str, Any]]:
        """
        영상에서 자막 파일 생성
        
        Args:
            video_path: 비디오 파일 경로
            output_path: 출력 자막 파일 경로
            model: Whisper 모델 크기 ('tiny', 'base', 'small', 'medium', 'large')
            language: 자막 언어 코드 ('en', 'ko', 등)
            
        Returns:
            성공 여부, 처리 정보(모델, 처리 시간 등)
        """
        if model not in self.available_models:
            model = "tiny"
            
        try:
            logger.info(f"Whisper 자막 생성 시작: {video_path}, 모델: {model}")
            start_time = time.time()
            
            # 출력 디렉토리 확인
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # whisper 명령 설정
            cmd = [
                'whisper',
                video_path,
                '--model', model,
                '--language', language,
                '--output_dir', output_dir,
                '--output_format', 'srt'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 진행 상황을 5초마다 기록
            while process.returncode is None:
                await asyncio.sleep(5)
                logger.info(f"Whisper 자막 생성 중... (모델: {model})")
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Whisper 자막 생성 오류: {stderr.decode()}")
                return False, {
                    "model": model,
                    "error": stderr.decode(),
                    "duration": time.time() - start_time
                }
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 출력 파일명 수정이 필요한 경우 (whisper는 자체 파일명 규칙을 사용함)
            video_filename = Path(video_path).stem
            whisper_output = Path(output_dir) / f"{video_filename}.srt"
            
            if whisper_output.exists() and str(whisper_output) != output_path:
                # whisper 생성 파일을 원하는 경로로 이동
                os.rename(str(whisper_output), output_path)
            
            logger.info(f"Whisper 자막 생성 완료: {output_path} (소요시간: {duration:.1f}초)")
            
            return True, {
                "model": model,
                "model_size": self.model_sizes.get(model, "unknown"),
                "processing_speed": self.model_processing_speed.get(model, "unknown"),
                "duration": duration,
                "output_path": output_path,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Whisper 자막 생성 오류: {str(e)}")
            return False, {
                "model": model,
                "error": str(e),
                "duration": time.time() - start_time if 'start_time' in locals() else 0
            }
    
    async def estimate_processing_time(self, 
                                     video_path: str, 
                                     model: str = "tiny") -> Dict[str, Any]:
        """
        비디오 처리 시간 예상
        
        Args:
            video_path: 비디오 파일 경로
            model: Whisper 모델 ('tiny', 'base', 'small', 'medium', 'large')
            
        Returns:
            예상 처리 시간 정보
        """
        if model not in self.available_models:
            model = "tiny"
            
        try:
            # 비디오 길이 확인
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                video_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"비디오 길이 확인 오류: {stderr.decode()}")
                return {
                    "model": model,
                    "error": "비디오 길이를 확인할 수 없습니다.",
                    "estimated_seconds": 0
                }
            
            # 비디오 길이(초)
            try:
                video_duration = float(stdout.decode().strip())
            except (ValueError, TypeError):
                video_duration = 0
            
            # 모델별 처리 속도 계수 (대략적인 값)
            speed_factors = {
                "tiny": 32,
                "base": 16,
                "small": 6,
                "medium": 2,
                "large": 1
            }
            
            # 예상 처리 시간 계산 (비디오 길이 / 속도 계수)
            estimated_seconds = video_duration / speed_factors.get(model, 32)
            
            return {
                "model": model,
                "model_size": self.model_sizes.get(model, "unknown"),
                "processing_speed": self.model_processing_speed.get(model, "unknown"),
                "video_duration": video_duration,
                "estimated_seconds": estimated_seconds,
                "human_estimate": self._format_time(estimated_seconds)
            }
            
        except Exception as e:
            logger.error(f"처리 시간 예상 오류: {str(e)}")
            return {
                "model": model,
                "error": str(e),
                "estimated_seconds": 0
            }
    
    def _format_time(self, seconds: float) -> str:
        """초를 읽기 쉬운 시간 형식으로 변환"""
        if seconds < 60:
            return f"{seconds:.1f}초"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}분"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}시간" 