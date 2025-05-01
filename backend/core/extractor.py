#!/usr/bin/env python3
"""
File: extractor.py
Description: 비디오 클립 추출을 위한 코어 모듈
"""

import os
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple

from .utils import setup_logger, ensure_dir_exists, is_supported_video_format, get_temp_file

logger = setup_logger('extractor_core', 'extractor_core.log')

class VideoExtractor:
    """비디오 클립 추출을 위한 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        VideoExtractor 초기화
        
        Args:
            config: 설정 (옵션)
        """
        self.config = config or {}
        self.temp_files = []
    
    def cleanup(self) -> None:
        """임시 파일 정리"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"임시 파일 제거됨: {file_path}")
            except Exception as e:
                logger.warning(f"임시 파일 제거 실패 {file_path}: {str(e)}")
    
    async def extract_clip(self, 
                     input_path: str, 
                     output_path: str,
                     start_time: str,
                     end_time: str,
                     audio_only: bool = False,
                     high_quality: bool = False) -> bool:
        """
        비디오 클립 추출
        
        Args:
            input_path: 입력 비디오 파일 경로
            output_path: 출력 클립 저장 경로
            start_time: 시작 시간 (HH:MM:SS.mmm)
            end_time: 종료 시간 (HH:MM:SS.mmm)
            audio_only: 오디오만 추출할지 여부
            high_quality: 고품질로 인코딩할지 여부
            
        Returns:
            성공 여부
        """
        try:
            input_file = Path(input_path)
            output_file = Path(output_path)
            
            # 출력 디렉토리 생성
            ensure_dir_exists(str(output_file.parent))
            
            # 입력 파일 확인
            if not input_file.exists():
                logger.error(f"입력 파일이 존재하지 않음: {input_path}")
                return False
                
            # 비디오 형식 검사
            if not is_supported_video_format(input_path):
                logger.warning(f"지원되지 않는 비디오 형식일 수 있음: {input_file.suffix}")
            
            # FFmpeg 명령 구성
            cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-ss', start_time]
            
            # 입력 파일 지정
            cmd.extend(['-i', str(input_file)])
            
            # 끝 시간 지정
            cmd.extend(['-to', end_time])
            
            # 인코딩 설정
            if audio_only:
                cmd.extend(['-vn', '-c:a', 'aac', '-b:a', '192k'])
                
                # 출력 파일 확장자 확인 및 조정
                if output_file.suffix.lower() not in ['.mp3', '.aac', '.m4a', '.wav']:
                    output_file = output_file.with_suffix('.mp3')
                    logger.info(f"오디오 출력 파일 확장자 변경: {output_file}")
            else:
                if high_quality:
                    # x265 고품질 설정
                    cmd.extend([
                        '-c:v', 'libx265', '-crf', '18', '-preset', 'slow',
                        '-c:a', 'aac', '-b:a', '192k'
                    ])
                else:
                    # 기본 x264 설정
                    cmd.extend([
                        '-c:v', 'libx264', '-crf', '23', '-preset', 'medium',
                        '-c:a', 'aac', '-b:a', '192k'
                    ])
            
            # 출력 파일 지정
            cmd.append(str(output_file))
            
            logger.info(f"클립 추출 시작: {start_time} - {end_time}")
            
            # FFmpeg 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg 오류: {stderr.decode()}")
                return False
            
            logger.info(f"클립 추출 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"클립 추출 오류: {str(e)}")
            return False
        finally:
            self.cleanup()
    
    def extract_clip_sync(self,
                      input_path: str, 
                      output_path: str,
                      start_time: str,
                      end_time: str,
                      audio_only: bool = False,
                      high_quality: bool = False) -> bool:
        """
        비디오 클립 동기적으로 추출 (비동기 함수의 동기 래퍼)
        
        Args:
            input_path: 입력 비디오 파일 경로
            output_path: 출력 클립 저장 경로
            start_time: 시작 시간 (HH:MM:SS.mmm)
            end_time: 종료 시간 (HH:MM:SS.mmm)
            audio_only: 오디오만 추출할지 여부
            high_quality: 고품질로 인코딩할지 여부
            
        Returns:
            성공 여부
        """
        try:
            return asyncio.run(self.extract_clip(
                input_path=input_path,
                output_path=output_path,
                start_time=start_time,
                end_time=end_time,
                audio_only=audio_only,
                high_quality=high_quality
            ))
        except Exception as e:
            logger.error(f"동기 클립 추출 오류: {str(e)}")
            return False
    
    async def extract_subtitle(self, input_path: str, output_path: str) -> bool:
        """
        비디오 파일에서 자막 추출
        
        Args:
            input_path: 입력 비디오 파일 경로
            output_path: 출력 자막 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            input_file = Path(input_path)
            output_file = Path(output_path)
            
            # 출력 디렉토리 생성
            ensure_dir_exists(str(output_file.parent))
            
            # 입력 파일 확인
            if not input_file.exists():
                logger.error(f"입력 파일이 존재하지 않음: {input_path}")
                return False
            
            # FFmpeg 명령 구성
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-i', str(input_file),
                '-map', '0:s:0',  # 첫 번째 자막 스트림 선택
                '-c:s', 'text',   # 텍스트 형식으로 변환
                str(output_file)
            ]
            
            # FFmpeg 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"자막 추출 FFmpeg 오류: {stderr.decode()}")
                return False
            
            # 자막 파일 존재 확인
            if not output_file.exists() or output_file.stat().st_size == 0:
                logger.warning(f"자막 파일이 생성되지 않음: {output_path}")
                return False
                
            logger.info(f"자막 추출 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"자막 추출 오류: {str(e)}")
            return False
    
    async def download_youtube_video(self, 
                               url: str, 
                               output_dir: str,
                               quality: str = 'best',
                               audio_only: bool = False) -> Optional[str]:
        """
        YouTube 비디오 다운로드
        
        Args:
            url: YouTube URL
            output_dir: 출력 디렉토리
            quality: 비디오 품질 ('best', '720p', '480p', '360p', 'worst')
            audio_only: 오디오만 다운로드할지 여부
            
        Returns:
            다운로드된 파일 경로 또는 None
        """
        try:
            # 출력 디렉토리 생성
            ensure_dir_exists(output_dir)
            
            # 임시 출력 파일명
            temp_output = get_temp_file(suffix='.%(ext)s')
            self.temp_files.append(temp_output)
            
            # yt-dlp 명령 구성
            cmd = ['yt-dlp']
            
            if audio_only:
                cmd.extend(['-x', '--audio-format', 'mp3', '--audio-quality', '0'])
            else:
                # 품질 설정
                if quality == 'best':
                    cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
                elif quality == '720p':
                    cmd.extend(['-f', 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best'])
                elif quality == '480p':
                    cmd.extend(['-f', 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best'])
                elif quality == '360p':
                    cmd.extend(['-f', 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best'])
                elif quality == 'worst':
                    cmd.extend(['-f', 'worst[ext=mp4]/worst'])
                    
            # 출력 파일 설정
            cmd.extend(['--output', temp_output])
            
            # YouTube URL
            cmd.append(url)
            
            logger.info(f"YouTube 다운로드 시작: {url}")
            
            # yt-dlp 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"YouTube 다운로드 오류: {stderr.decode()}")
                return None
            
            # 다운로드된 파일 찾기
            # temp_output은 템플릿이므로 실제 파일 경로를 찾아야 함
            downloaded_file = None
            temp_prefix = temp_output.split('.')[0]
            
            for file in os.listdir(tempfile.gettempdir()):
                if file.startswith(os.path.basename(temp_prefix)):
                    downloaded_file = os.path.join(tempfile.gettempdir(), file)
                    break
            
            if not downloaded_file:
                logger.error("다운로드된 파일을 찾을 수 없음")
                return None
            
            # 최종 출력 파일 경로
            final_output = os.path.join(output_dir, os.path.basename(downloaded_file))
            
            # 파일 이동
            os.rename(downloaded_file, final_output)
            logger.info(f"YouTube 다운로드 완료: {final_output}")
            
            return final_output
            
        except Exception as e:
            logger.error(f"YouTube 다운로드 오류: {str(e)}")
            return None