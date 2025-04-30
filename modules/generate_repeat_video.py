#!/usr/bin/env python3
"""
File: generate_repeat_video.py
Description: 쉐도잉 연습을 위한 사용자 정의 자막 표시가 포함된 반복 비디오 클립 생성
Input: 비디오 클립, 자막, config.yaml
Output: 설정에 따라 렌더링된 자막이 포함된 반복 비디오 클립
Libraries: ffmpeg-python, pysrt, yaml, edge-tts, openai, google-cloud-texttospeech
Updates: 
  - 2025-05-01: 초기 버전
  - 2025-05-01: MKV 확장자 파일 지원 추가

이 모듈은 서로 다른 자막 구성과 선택적 TTS 오디오 가이드를 사용하여
클립을 여러 번 반복함으로써 쉐도잉 연습 비디오를 만듭니다.
"""

import os
import sys
import json
import yaml
import uuid
import pysrt
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

# Third-party imports
import ffmpeg
import aiofiles
import edge_tts
from gtts import gTTS
from openai import OpenAI
from google.cloud import texttospeech

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("repeat_video.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RepeatVideoGenerator:
    """반복 클립이 포함된 쉐도잉 연습 비디오 생성을 위한 클래스"""
    
    def __init__(self, config_path: str):
        """
        RepeatVideoGenerator 초기화
        
        Args:
            config_path: config.yaml 파일 경로
        """
        self.config = self._load_config(config_path)
        self.temp_files = []
        
    def _load_config(self, config_path: str) -> Dict:
        """
        YAML 파일에서 설정 불러오기
        
        Args:
            config_path: config.yaml 파일 경로
            
        Returns:
            설정 사전
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            logger.info(f"Loaded configuration from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            # Return default config
            return {
                "repeat_count": 3,
                "subtitle_mode": ["no_subtitle", "en_ko", "en_ko"],
                "subtitle_style": {
                    "font": "Pretendard-Bold", 
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
    
    async def generate_repeat_video(self, 
                              input_video: str, 
                              subtitle_file: str, 
                              output_path: str,
                              korean_translation: Optional[Dict[str, str]] = None) -> bool:
        """
        반복 클립과 다양한 자막 구성이 포함된 비디오 생성
        
        Args:
            input_video: 입력 비디오 클립 경로 (mp4, mkv 등 ffmpeg 지원 형식)
            subtitle_file: 자막 파일 경로 (SRT)
            output_path: 출력 비디오 저장 경로
            korean_translation: 영어-한국어 번역을 매핑하는 선택적 사전
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            logger.info(f"Generating repeat video for: {input_video}")
            input_path = Path(input_video)
            subtitle_path = Path(subtitle_file)
            output_path = Path(output_path)
            
            # 지원되는 비디오 형식 확인
            supported_formats = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
            if input_path.suffix.lower() not in supported_formats:
                logger.warning(f"입력 파일 형식이 지원되지 않을 수 있음: {input_path.suffix}")
            
            # 출력 디렉토리가 존재하는지 확인
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 자막 읽기
            subs = pysrt.open(subtitle_path)
            
            # 각 반복에 대한 세그먼트 생성
            segments = []
            repeat_count = self.config.get("repeat_count", 3)
            subtitle_modes = self.config.get("subtitle_mode", ["no_subtitle", "en_ko", "en_ko"])
            
            # subtitle_modes에 충분한 요소가 있는지 확인
            while len(subtitle_modes) < repeat_count:
                subtitle_modes.append(subtitle_modes[-1])
            
            # 각 반복에 대한 세그먼트 생성
            for i in range(repeat_count):
                mode = subtitle_modes[i] if i < len(subtitle_modes) else "en_ko"
                
                segment_path = await self._create_segment(
                    input_video=input_path,
                    subtitles=subs,
                    mode=mode,
                    segment_index=i,
                    korean_translation=korean_translation
                )
                
                if segment_path:
                    segments.append(segment_path)
                else:
                    logger.error(f"Failed to create segment {i}")
                
                # 마지막 세그먼트가 아닌 경우 세그먼트 사이에 집중 텍스트 추가
                if i < repeat_count - 1:
                    focus_path = await self._create_focus_segment(i)
                    if focus_path:
                        segments.append(focus_path)
            
            # 모든 세그먼트 연결
            if segments:
                success = await self._concatenate_segments(segments, output_path)
                if success:
                    logger.info(f"Successfully generated repeat video: {output_path}")
                    return True
            
            logger.error("Failed to generate repeat video")
            return False
            
        except Exception as e:
            logger.error(f"Error generating repeat video: {str(e)}")
            return False
        finally:
            # 임시 파일 정리
            self._cleanup_temp_files()
    
    async def _create_segment(self, 
                        input_video: Path, 
                        subtitles: pysrt.SubRipFile,
                        mode: str,
                        segment_index: int,
                        korean_translation: Optional[Dict[str, str]] = None) -> Optional[Path]:
        """
        특정 자막 구성으로 비디오 세그먼트 생성
        
        Args:
            input_video: 입력 비디오 클립 경로
            subtitles: 자막 데이터
            mode: 자막 모드 (no_subtitle, en, ko, en_ko)
            segment_index: 파일 이름 지정을 위한 세그먼트 인덱스
            korean_translation: 영어-한국어 번역을 매핑하는 사전
            
        Returns:
            생성된 세그먼트 경로 또는 오류 시 None
        """
        try:
            # 모드에 따라 자막 적용
            temp_output = Path(tempfile.mktemp(suffix=f'.segment{segment_index}.mp4'))
            self.temp_files.append(temp_output)
            
            # 적절한 내용으로 임시 자막 파일 생성
            temp_subtitle = Path(tempfile.mktemp(suffix=f'.segment{segment_index}.srt'))
            self.temp_files.append(temp_subtitle)
            
            # 모드에 따라 자막 준비
            await self._prepare_subtitles(subtitles, temp_subtitle, mode, korean_translation)
            
            # 자막과 함께 비디오 렌더링
            if mode == "no_subtitle":
                # 자막 없이 비디오만 복사
                cmd = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-i', str(input_video),
                    '-c', 'copy',
                    str(temp_output)
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {stderr.decode()}")
                    return None
            else:
                # 비디오에 자막 추가
                subtitle_style = self.config.get("subtitle_style", {})
                font = subtitle_style.get("font", "Pretendard-Bold")
                fontsize = subtitle_style.get("fontsize", 48)
                position = subtitle_style.get("position", {"x": 50, "y": 600})
                pos_x = position.get("x", 50)
                pos_y = position.get("y", 600)
                shadow = subtitle_style.get("shadow", True)
                bgcolor = subtitle_style.get("bgcolor", "#00000080")
                
                # 자막 필터 구성
                filter_complex = f"subtitles={temp_subtitle.name.replace(':', '\\:')}:"
                filter_complex += f"force_style='FontName={font},FontSize={fontsize},"
                filter_complex += f"PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                filter_complex += f"BorderStyle=1,Outline=1,Shadow={1 if shadow else 0},"
                filter_complex += f"BackColour={bgcolor.replace('#', '&H')},"
                filter_complex += f"Alignment=2,MarginL={pos_x},MarginV={pos_y}'"
                
                cmd = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-i', str(input_video),
                    '-vf', filter_complex,
                    '-c:a', 'copy',
                    str(temp_output)
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {stderr.decode()}")
                    return None
            
            # 필요한 경우 TTS 오디오 생성
            if segment_index == 0 and self.config.get("tts", {}).get("provider"):
                await self._add_tts_to_video(temp_output, subtitles, korean_translation)
            
            return temp_output
            
        except Exception as e:
            logger.error(f"Error creating segment: {str(e)}")
            return None
    
    async def _prepare_subtitles(self, 
                          subtitles: pysrt.SubRipFile, 
                          output_path: Path, 
                          mode: str,
                          korean_translation: Optional[Dict[str, str]] = None) -> bool:
        """
        지정된 모드에 따라 자막 준비
        
        Args:
            subtitles: 자막 데이터
            output_path: 수정된 자막을 저장할 경로
            mode: 자막 모드 (no_subtitle, en, ko, en_ko)
            korean_translation: 영어-한국어 번역을 매핑하는 사전
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            if mode == "no_subtitle":
                # 빈 자막 파일 생성
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write("")
                return True
            
            modified_subs = pysrt.SubRipFile()
            
            for sub in subtitles:
                new_sub = pysrt.SubRipItem(
                    index=sub.index,
                    start=sub.start,
                    end=sub.end,
                    text=sub.text
                )
                
                english_text = sub.text.strip()
                
                if mode == "en":
                    # 영어만 유지
                    new_sub.text = english_text
                elif mode == "ko":
                    # 가능한 경우 한국어만
                    if korean_translation and english_text in korean_translation:
                        new_sub.text = korean_translation[english_text]
                    else:
                        new_sub.text = english_text
                elif mode == "en_ko":
                    # 영어와 한국어
                    if korean_translation and english_text in korean_translation:
                        korean_text = korean_translation[english_text]
                        new_sub.text = f"{english_text}\n{korean_text}"
                    else:
                        new_sub.text = english_text
                
                modified_subs.append(new_sub)
            
            # 수정된 자막 저장
            modified_subs.save(output_path, encoding='utf-8')
            return True
            
        except Exception as e:
            logger.error(f"Error preparing subtitles: {str(e)}")
            return False
    
    async def _create_focus_segment(self, segment_index: int) -> Optional[Path]:
        """
        "다시 집중!" 또는 "기억나나요?"와 같은 텍스트가 있는 집중 세그먼트 생성
        
        Args:
            segment_index: 메시지를 번갈아 표시하기 위한 세그먼트 인덱스
            
        Returns:
            생성된 집중 세그먼트 경로 또는 오류 시 None
        """
        try:
            # 번갈아 나오는 메시지
            if segment_index % 2 == 0:
                message = "다시 집중!"
            else:
                message = "기억나나요?"
                
            # 텍스트와 함께 빈 비디오 생성
            temp_output = Path(tempfile.mktemp(suffix=f'.focus{segment_index}.mp4'))
            self.temp_files.append(temp_output)
            
            # 텍스트가 있는 2초 길이의 빈 비디오 생성
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'lavfi', '-i', 'color=c=black:s=1920x1080:d=2', 
                '-vf', f"drawtext=text='{message}':fontcolor=white:fontsize=72:x=(w-tw)/2:y=(h-th)/2:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-shortest',
                str(temp_output)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return None
                
            return temp_output
            
        except Exception as e:
            logger.error(f"Error creating focus segment: {str(e)}")
            return None
    
    async def _concatenate_segments(self, segments: List[Path], output_path: Path) -> bool:
        """
        비디오 세그먼트를 하나의 비디오로 연결
        
        Args:
            segments: 비디오 세그먼트 경로 목록
            output_path: 연결된 비디오를 저장할 경로
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 연결 파일 생성
            concat_file = Path(tempfile.mktemp(suffix='.txt'))
            self.temp_files.append(concat_file)
            
            async with aiofiles.open(concat_file, 'w', encoding='utf-8') as f:
                for segment in segments:
                    await f.write(f"file '{segment.absolute()}'\n")
            
            # 비디오 연결
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error concatenating segments: {str(e)}")
            return False
    
    async def _add_tts_to_video(self, 
                         video_path: Path, 
                         subtitles: pysrt.SubRipFile,
                         korean_translation: Optional[Dict[str, str]] = None) -> bool:
        """
        자막을 기반으로 비디오에 TTS 오디오 추가
        
        Args:
            video_path: 비디오 파일 경로
            subtitles: 자막 데이터
            korean_translation: 영어-한국어 번역을 매핑하는 사전
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 비디오에서 오디오 추출
            temp_audio = Path(tempfile.mktemp(suffix='.audio.wav'))
            self.temp_files.append(temp_audio)
            
            # 각 자막에 대한 TTS 오디오 생성
            tts_config = self.config.get("tts", {})
            provider = tts_config.get("provider", "edge-tts")
            voice = tts_config.get("voice", "en-US-GuyNeural")
            speed = tts_config.get("speed", 1.0)
            pitch = tts_config.get("pitch", 0)
            
            if provider == "edge-tts":
                success = await self._generate_edge_tts(
                    video_path, subtitles, temp_audio, voice, speed, pitch
                )
            elif provider == "gtts":
                success = await self._generate_gtts(
                    video_path, subtitles, temp_audio
                )
            elif provider == "openai-tts":
                success = await self._generate_openai_tts(
                    video_path, subtitles, temp_audio, voice
                )
            elif provider == "google-cloud-tts":
                success = await self._generate_google_tts(
                    video_path, subtitles, temp_audio, voice, speed, pitch
                )
            else:
                logger.error(f"Unsupported TTS provider: {provider}")
                return False
            
            if not success:
                return False
            
            # TTS 오디오와 비디오 병합
            temp_output = Path(tempfile.mktemp(suffix='.tts_merged.mp4'))
            self.temp_files.append(temp_output)
            
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-i', str(video_path),
                '-i', str(temp_audio),
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-c:v', 'copy',
                '-c:a', 'aac', '-b:a', '192k',
                str(temp_output)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False
            
            # 원본 비디오를 병합된 비디오로 교체
            import shutil
            shutil.move(str(temp_output), str(video_path))
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding TTS: {str(e)}")
            return False
    
    async def _generate_edge_tts(self, 
                          video_path: Path, 
                          subtitles: pysrt.SubRipFile, 
                          output_audio: Path,
                          voice: str,
                          speed: float,
                          pitch: int) -> bool:
        """
        Microsoft Edge TTS를 사용하여 TTS 오디오 생성
        
        Args:
            video_path: 비디오 파일 경로
            subtitles: 자막 데이터
            output_audio: 생성된 오디오를 저장할 경로
            voice: 음성 ID
            speed: 말하기 속도
            pitch: 음성 피치 조정
            
        Returns:
            성공 시 True, 실패 시 False
        """
        try:
            # 음성 세그먼트 사이에 침묵이 있는 단일 오디오 파일 생성
            temp_dir = Path(tempfile.mkdtemp())
            segment_files = []
            
            # 비디오 길이 가져오기
            probe = ffmpeg.probe(str(video_path))
            video_duration = float(probe['format']['duration'])
            
            # 전체 길이에 대한 무음 오디오 생성
            silent_audio = Path(tempfile.mktemp(suffix='.silent.wav'))
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error',
                '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo:d={video_duration}',
                '-c:a', 'pcm_s16le',
                str(silent_audio)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            # 각 자막에 대한 음성 생성
            for i, sub in enumerate(subtitles):
                # 말할 텍스트 가져오기
                text = sub.text.strip()
                
                # 초 단위로 시간 계산
                start_time = (sub.start.hours * 3600 + sub.start.minutes * 60 + 
                             sub.start.seconds + sub.start.milliseconds / 1000)
                
                # 음성 파일 생성
                segment_file = temp_dir / f"segment_{i:04d}.wav"
                
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(segment_file))
                
                # 나중에 병합할 세그먼트 정보 생성
                segment_files.append({
                    'file': segment_file,
                    'start_time': start_time
                })
            
            # Create a filter complex to mix all audio files
            filter_complex = []
            input_args = ['-i', str(silent_audio)]
            
            for i, segment in enumerate(segment_files):
                input_args.extend(['-i', str(segment['file'])])
                filter_complex.append(f"[{i+1}]adelay={int(segment['start_time']*1000)}|{int(segment['start_time']*1000)}[s{i}]")
            
            # Add the base silent track
            filter_complex.append(f"[0]")
            
            # Mix with all speech segments
            for i in range(len(segment_files)):
                filter_complex.append(f"[s{i}]")
            
            filter_complex.append(f"amix=inputs={len(segment_files)+1}:duration=first:dropout_transition=0")
            
            # Merge all audio
            cmd = [
                'ffmpeg', '-y', '-loglevel', 'error'
            ]
            cmd.extend(input_args)
            cmd.extend([
                '-filter_complex', ''.join(filter_complex),
                '-c:a', 'pcm_s16le',
                str(output_audio)
            ])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating Edge TTS: {str(e)}")
            return False
    
    def _cleanup_temp_files(self) -> None:
        """임시 파일 정리"""
        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {file_path}: {str(e)}")

async def main():
    """반복 비디오 생성기를 실행하는 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='반복 클립이 포함된 쉐도잉 연습 비디오 생성')
    parser.add_argument('--video', '-v', type=str, required=True, 
                        help='입력 비디오 클립 경로')
    parser.add_argument('--subtitle', '-s', type=str, required=True, 
                        help='자막 파일 경로 (SRT)')
    parser.add_argument('--output', '-o', type=str, required=True, 
                        help='출력 비디오 경로')
    parser.add_argument('--config', '-c', type=str, required=True,
                        help='config.yaml 파일 경로')
    parser.add_argument('--translation', '-t', type=str,
                        help='번역 JSON 파일 경로 (영어-한국어)')
    
    args = parser.parse_args()
    
    # 번역 로드 (제공된 경우)
    korean_translation = None
    if args.translation:
        try:
            with open(args.translation, 'r', encoding='utf-8') as f:
                korean_translation = json.load(f)
            logger.info(f"Loaded translation from: {args.translation}")
        except Exception as e:
            logger.error(f"Error loading translation: {str(e)}")
    
    generator = RepeatVideoGenerator(args.config)
    success = await generator.generate_repeat_video(
        input_video=args.video,
        subtitle_file=args.subtitle,
        output_path=args.output,
        korean_translation=korean_translation
    )
    
    if success:
        print(f"Successfully generated repeat video: {args.output}")
        return 0
    else:
        print("Failed to generate repeat video")
        return 1

if __name__ == "__main__":
    asyncio.run(main())
