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
from typing import Dict, Any, Optional, Union, Tuple, List

from app.common.utils import setup_logger, ensure_dir_exists, get_temp_file

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
    
    async def get_youtube_transcript(self, url: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        YouTube 영상의 트랜스크립트(자막) 가져오기
        
        Args:
            url: YouTube URL
            language: 자막 언어 코드 (기본값: 'en')
            
        Returns:
            트랜스크립트 목록 (텍스트, 시작 시간, 지속 시간 포함)
        """
        try:
            logger.info(f"YouTube 트랜스크립트 가져오기: {url}, 언어: {language}")
            
            # youtube_transcript_api 임포트
            from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
            
            # YouTube 영상 ID 추출
            video_id = None
            if "youtube.com/watch?v=" in url:
                video_id = url.split("watch?v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            
            if not video_id:
                logger.error("YouTube 영상 ID를 추출할 수 없음")
                return []
            
            # 직접 TranscriptApi.get_transcript 사용
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
                logger.info(f"{len(transcript_data)}개의 자막 항목을 찾았습니다.")
                
                return [
                    {
                        "text": item["text"],
                        "start": item["start"],
                        "duration": item["duration"]
                    }
                    for item in transcript_data
                ]
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logger.error(f"자막을 찾을 수 없음: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"YouTube 트랜스크립트 가져오기 오류: {str(e)}")
            return []
    
    async def download_youtube(self, 
                             url: str, 
                             output_dir: str, 
                             progress_callback=None,
                             subtitle_languages: List[str] = None) -> Optional[Path]:
        """
        YouTube 영상 다운로드
        
        Args:
            url: YouTube URL
            output_dir: 출력 디렉토리 경로
            progress_callback: 진행 상황을 보고할 콜백 함수 (progress: float, message: str)
            subtitle_languages: 다운로드할 자막 언어 목록 (기본값: ['en', 'en-US', 'en-GB', 'ko'])
            
        Returns:
            다운로드된 파일 경로 또는 None
        """
        try:
            logger.info(f"YouTube 영상 다운로드: {url}")
            output_dir_path = Path(output_dir)
            
            # 기본 자막 언어 설정
            if subtitle_languages is None:
                subtitle_languages = ['en', 'en-US', 'en-GB', 'ko']
            
            # 자막 언어 목록을 문자열로 변환
            sub_lang = ','.join(subtitle_languages)
            logger.info(f"자막 다운로드 언어 설정: {sub_lang}")
            
            # 출력 디렉토리 생성
            os.makedirs(output_dir_path, exist_ok=True)
            
            # 임시 로그 파일 생성
            tmp_log = get_temp_file(suffix=".log")
            self.temp_files.append(tmp_log)
            
            # yt-dlp 명령 설정
            cmd = [
                'yt-dlp',
                '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '-o', str(output_dir_path / '%(title)s.%(ext)s'),
                '--write-auto-sub',
                '--write-sub',
                '--sub-lang', sub_lang,
                '--progress-template', '%(progress.downloaded_bytes)s/%(progress.total_bytes)s - %(progress.eta)s - %(progress.speed)s',
                '--newline',
                url
            ]
            
            # yt-dlp 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            file_path = None
            downloaded_bytes = 0
            total_bytes = 0
            
            # 실시간으로 출력 처리
            async for line in process.stdout:
                line_str = line.decode('utf-8', errors='replace').strip()
                logger.debug(f"yt-dlp 출력: {line_str}")
                
                # 파일 경로 추출
                if '[download] Destination:' in line_str:
                    file_path = line_str.split('Destination: ')[1].strip()
                    if progress_callback:
                        await progress_callback(0.0, f"영상 다운로드 시작: {Path(file_path).name}")
                
                # 이미 다운로드된 파일 처리
                elif '[download] ' in line_str and ' has already been downloaded' in line_str:
                    file_path = line_str.split('[download] ')[1].split(' has already been downloaded')[0]
                    if progress_callback:
                        await progress_callback(1.0, f"이미 다운로드된 파일 사용: {Path(file_path).name}")
                
                # 진행률 추출 및 콜백 호출
                elif '/' in line_str and 'EiB' not in line_str and ' - ' in line_str:
                    try:
                        size_part = line_str.split(' - ')[0]
                        if '/' in size_part:
                            downloaded_str, total_str = size_part.split('/')
                            
                            # 숫자만 추출
                            downloaded_bytes = float(''.join(filter(lambda x: x.isdigit() or x == '.', downloaded_str)))
                            total_bytes = float(''.join(filter(lambda x: x.isdigit() or x == '.', total_str)))
                            
                            if total_bytes > 0:
                                progress = downloaded_bytes / total_bytes
                                speed_part = line_str.split(' - ')[-1]
                                if progress_callback:
                                    await progress_callback(progress, f"다운로드 중: {progress:.1%} ({speed_part})")
                    except Exception as e:
                        logger.error(f"진행률 파싱 오류: {str(e)}")
            
            # 오류 출력 확인
            stderr_data = await process.stderr.read()
            stderr_str = stderr_data.decode('utf-8', errors='replace')
            
            if process.returncode != 0:
                logger.error(f"YouTube 다운로드 오류: {stderr_str}")
                if progress_callback:
                    await progress_callback(0.0, f"다운로드 실패: {stderr_str[:100]}")
                return None
            
            # 파일 경로가 추출되지 않은 경우, 디렉토리에서 가장 최근 파일 반환
            if not file_path:
                files = list(output_dir_path.glob('*.mp4'))
                if files:
                    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    file_path = str(files[0])
            
            if file_path:
                if progress_callback:
                    await progress_callback(1.0, f"다운로드 완료: {Path(file_path).name}")
                return Path(file_path)
            
            logger.warning("다운로드된 파일을 찾을 수 없음")
            if progress_callback:
                await progress_callback(0.0, "다운로드된 파일을 찾을 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"YouTube 다운로드 오류: {str(e)}")
            if progress_callback:
                await progress_callback(0.0, f"다운로드 오류: {str(e)}")
            return None
            
    async def extract_subtitle(self, video_path: str, output_path: str) -> bool:
        """
        비디오에서 자막 추출
        
        Args:
            video_path: 비디오 파일 경로
            output_path: 출력 자막 파일 경로
            
        Returns:
            성공 여부
        """
        try:
            logger.info(f"자막 추출: {video_path} -> {output_path}")
            
            # 출력 디렉토리 확인
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # FFmpeg 명령 설정
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-f', 'srt',
                output_path,
                '-y'  # 기존 파일 덮어쓰기
            ]
            
            # FFmpeg 실행
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"자막 추출 오류: {stderr.decode()}")
                return False
            
            # 파일 확인
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"자막 추출 성공: {output_path}")
                return True
            else:
                logger.error(f"자막 파일이 생성되지 않았거나 비어 있음: {output_path}")
                return False
                
        except Exception as e:
            logger.error(f"자막 추출 오류: {str(e)}")
            return False 