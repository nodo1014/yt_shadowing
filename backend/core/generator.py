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

from .utils import setup_logger, ensure_dir_exists, get_temp_file

logger = setup_logger('generator_core', 'generator_core.log')

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
    
    async def generate_repeat_video(self,
                              input_video: str,
                              subtitle_file: str,
                              output_path: str,
                              korean_translation: Optional[Dict[str, str]] = None) -> bool:
        """
        반복 영상 생성
        
        Args:
            input_video: 입력 비디오 클립 경로
            subtitle_file: 자막 파일 경로
            output_path: 출력 비디오 저장 경로
            korean_translation: 영어-한국어 번역을 매핑하는 사전 (옵션)
            
        Returns:
            성공 여부
        """
        try:
            logger.info(f"반복 영상 생성: {input_video}")
            input_path = Path(input_video)
            subtitle_path = Path(subtitle_file)
            output_path = Path(output_path)
            
            # 입력 파일 확인
            if not input_path.exists():
                logger.error(f"입력 비디오 파일이 존재하지 않음: {input_video}")
                return False
                
            if not subtitle_path.exists():
                logger.error(f"자막 파일이 존재하지 않음: {subtitle_file}")
                return False
            
            # 출력 디렉토리 생성
            ensure_dir_exists(str(output_path.parent))
            
            # 자막 읽기
            subs = pysrt.open(subtitle_path)
            
            # 반복 횟수 및 자막 모드 가져오기
            repeat_count = self.config.get("repeat_count", 3)
            subtitle_modes = self.config.get("subtitle_mode", ["no_subtitle", "en_ko", "en_ko"])
            
            # subtitle_modes에 충분한 요소가 있는지 확인
            while len(subtitle_modes) < repeat_count:
                subtitle_modes.append(subtitle_modes[-1])
            
            # 각 반복에 대한 세그먼트 생성
            segments = []
            
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
                    logger.error(f"세그먼트 {i} 생성 실패")
                
                # 마지막 세그먼트가 아닌 경우 세그먼트 사이에 집중 텍스트 추가
                if i < repeat_count - 1:
                    focus_path = await self._create_focus_segment(i)
                    if focus_path:
                        segments.append(focus_path)
            
            # 모든 세그먼트 연결
            if segments:
                success = await self._concatenate_segments(segments, output_path)
                if success:
                    logger.info(f"반복 영상 생성 완료: {output_path}")
                    return True
            
            logger.error("반복 영상 생성 실패")
            return False
            
        except Exception as e:
            logger.error(f"반복 영상 생성 오류: {str(e)}")
            return False
        finally:
            self.cleanup()
    
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
            segment_index: 세그먼트 인덱스
            korean_translation: 영어-한국어 번역 매핑 사전
            
        Returns:
            생성된 세그먼트 경로 또는 None
        """
        try:
            # 모드에 따라 자막 적용
            temp_output = Path(get_temp_file(suffix=f'.segment{segment_index}.mp4'))
            self.temp_files.append(str(temp_output))
            
            # 적절한 내용으로 임시 자막 파일 생성
            temp_subtitle = Path(get_temp_file(suffix=f'.segment{segment_index}.srt'))
            self.temp_files.append(str(temp_subtitle))
            
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
                    logger.error(f"FFmpeg 오류: {stderr.decode()}")
                    return None
            else:
                # 비디오에 자막 추가
                subtitle_style = self.config.get("subtitle_style", {})
                font = subtitle_style.get("font", "Arial")
                fontsize = subtitle_style.get("fontsize", 48)
                position = subtitle_style.get("position", {"x": 50, "y": 600})
                pos_x = position.get("x", 50)
                pos_y = position.get("y", 600)
                shadow = subtitle_style.get("shadow", True)
                bgcolor = subtitle_style.get("bgcolor", "#00000080")
                
                # 자막 필터 구성
                filter_complex = f"subtitles='{temp_subtitle}':force_style='FontName={font},FontSize={fontsize},"
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
                    logger.error(f"FFmpeg 오류: {stderr.decode()}")
                    return None
            
            # 필요한 경우 TTS 오디오 생성
            if segment_index == 0 and self.config.get("tts", {}).get("provider"):
                await self._add_tts_to_video(temp_output, subtitles, korean_translation)
            
            return temp_output
            
        except Exception as e:
            logger.error(f"세그먼트 생성 오류: {str(e)}")
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
            korean_translation: 영어-한국어 번역 매핑 사전
            
        Returns:
            성공 여부
        """
        try:
            if mode == "no_subtitle":
                # 빈 자막 파일 생성
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("")
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
            modified_subs.save(str(output_path), encoding='utf-8')
            return True
            
        except Exception as e:
            logger.error(f"자막 준비 오류: {str(e)}")
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
            focus_messages = self.config.get("practice_format", {}).get("focus_message", [
                "다시 집중!",
                "기억나나요?",
                "따라 말해보세요!",
                "이제 해볼까요?"
            ])
            
            if focus_messages:
                message = focus_messages[segment_index % len(focus_messages)]
            else:
                if segment_index % 2 == 0:
                    message = "다시 집중!"
                else:
                    message = "기억나나요?"
                
            # 텍스트와 함께 빈 비디오 생성
            temp_output = Path(get_temp_file(suffix=f'.focus{segment_index}.mp4'))
            self.temp_files.append(str(temp_output))
            
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
                logger.error(f"FFmpeg 오류: {stderr.decode()}")
                return None
                
            return temp_output
            
        except Exception as e:
            logger.error(f"집중 세그먼트 생성 오류: {str(e)}")
            return None
    
    async def _concatenate_segments(self, segments: List[Path], output_path: Path) -> bool:
        """
        비디오 세그먼트를 하나의 비디오로 연결
        
        Args:
            segments: 비디오 세그먼트 경로 목록
            output_path: 연결된 비디오를 저장할 경로
            
        Returns:
            성공 여부
        """
        try:
            # 연결 파일 생성
            concat_file = Path(get_temp_file(suffix='.txt'))
            self.temp_files.append(str(concat_file))
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for segment in segments:
                    f.write(f"file '{segment.absolute()}'\n")
            
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
                logger.error(f"FFmpeg 오류: {stderr.decode()}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"세그먼트 연결 오류: {str(e)}")
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
            korean_translation: 영어-한국어 번역 매핑 사전
            
        Returns:
            성공 여부
        """
        try:
            # 비디오에서 오디오 추출
            temp_audio = Path(get_temp_file(suffix='.audio.wav'))
            self.temp_files.append(str(temp_audio))
            
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
            else:
                logger.error(f"지원되지 않는 TTS 제공자: {provider}")
                return False
            
            if not success:
                return False
            
            # TTS 오디오와 비디오 병합
            temp_output = Path(get_temp_file(suffix='.tts_merged.mp4'))
            self.temp_files.append(str(temp_output))
            
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
                logger.error(f"FFmpeg 오류: {stderr.decode()}")
                return False
            
            # 원본 비디오를 병합된 비디오로 교체
            os.replace(str(temp_output), str(video_path))
            
            return True
            
        except Exception as e:
            logger.error(f"TTS 추가 오류: {str(e)}")
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
            성공 여부
        """
        try:
            import edge_tts
            
            # 음성 세그먼트 사이에 침묵이 있는 단일 오디오 파일 생성
            temp_dir = Path(tempfile.mkdtemp())
            segment_files = []
            
            # 비디오 길이 가져오기
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(video_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"FFprobe 오류: {stderr.decode()}")
                return False
                
            probe_result = json.loads(stdout.decode())
            video_duration = float(probe_result['format']['duration'])
            
            # 전체 길이에 대한 무음 오디오 생성
            silent_audio = Path(get_temp_file(suffix='.silent.wav'))
            self.temp_files.append(str(silent_audio))
            
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
                self.temp_files.append(str(segment_file))
                
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(segment_file))
                
                # 나중에 병합할 세그먼트 정보 생성
                segment_files.append({
                    'file': segment_file,
                    'start_time': start_time
                })
            
            # 모든 오디오 파일을 혼합하기 위한 필터 복합체 생성
            filter_complex = []
            input_args = ['-i', str(silent_audio)]
            
            for i, segment in enumerate(segment_files):
                input_args.extend(['-i', str(segment['file'])])
                filter_complex.append(f"[{i+1}]adelay={int(segment['start_time']*1000)}|{int(segment['start_time']*1000)}[s{i}]")
            
            # 기본 무음 트랙 추가
            filter_complex.append(f"[0]")
            
            # 모든 음성 세그먼트와 혼합
            for i in range(len(segment_files)):
                filter_complex.append(f"[s{i}]")
            
            filter_complex.append(f"amix=inputs={len(segment_files)+1}:duration=first:dropout_transition=0")
            
            # 모든 오디오 병합
            cmd = ['ffmpeg', '-y', '-loglevel', 'error']
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
                logger.error(f"FFmpeg 오류: {stderr.decode()}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Edge TTS 생성 오류: {str(e)}")
            return False
    
    async def _generate_gtts(self,
                       video_path: Path,
                       subtitles: pysrt.SubRipFile,
                       output_audio: Path) -> bool:
        """
        Google Text-to-Speech를 사용하여 TTS 오디오 생성
        
        Args:
            video_path: 비디오 파일 경로
            subtitles: 자막 데이터
            output_audio: 생성된 오디오를 저장할 경로
            
        Returns:
            성공 여부
        """
        try:
            from gtts import gTTS
            
            # 구현 필요
            logger.warning("Google TTS 지원은 아직 구현되지 않았습니다")
            return False
            
        except Exception as e:
            logger.error(f"Google TTS 생성 오류: {str(e)}")
            return False


class ThumbnailGenerator:
    """썸네일 이미지 생성 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        ThumbnailGenerator 초기화
        
        Args:
            config: 설정 (옵션)
        """
        self.config = config or {}
        
        # 기본 설정
        self.default_config = {
            "thumbnail": {
                "width": 1280,
                "height": 720,
                "background_color": "#000033",
                "text_color": "#FFFFFF",
                "highlight_color": "#FFD700",
                "font": "Arial",
                "title_size": 72,
                "subtitle_size": 48,
                "padding": 50,
                "shadow": True,
                "shadow_color": "#00000080",
                "overlay_opacity": 0.5
            },
            "templates": {
                "simple": {
                    "background_color": "#000033",
                    "text_color": "#FFFFFF",
                    "highlight_color": "#FFD700"
                },
                "professional": {
                    "background_color": "#1A2740", 
                    "text_color": "#FFFFFF",
                    "highlight_color": "#3498db"
                },
                "vibrant": {
                    "background_color": "#6A0DAD",
                    "text_color": "#FFFFFF", 
                    "highlight_color": "#FF4500"
                },
                "minimalist": {
                    "background_color": "#FFFFFF",
                    "text_color": "#000000",
                    "highlight_color": "#FF5733"
                },
                "dark": {
                    "background_color": "#121212",
                    "text_color": "#FFFFFF",
                    "highlight_color": "#00FF00"
                }
            }
        }
        
        # 기본 설정에 사용자 설정 병합
        self._merge_config()
        
        # 시스템 폰트 검색
        self.system_fonts = self._find_system_fonts()
    
    def _merge_config(self) -> None:
        """설정 병합"""
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = self.default_config["thumbnail"]
        else:
            for key, value in self.default_config["thumbnail"].items():
                if key not in self.config["thumbnail"]:
                    self.config["thumbnail"][key] = value
        
        if "templates" not in self.config:
            self.config["templates"] = self.default_config["templates"]
    
    def _find_system_fonts(self) -> Dict[str, str]:
        """
        시스템 폰트 디렉토리에서 사용 가능한 폰트 찾기
        
        Returns:
            폰트 이름을 경로에 매핑하는 사전
        """
        font_dirs = [
            "/usr/share/fonts/",
            "/usr/local/share/fonts/",
            os.path.expanduser("~/.local/share/fonts/"),
            os.path.expanduser("~/.fonts/"),
            "C:\\Windows\\Fonts\\",
            "/Library/Fonts/",
            "/System/Library/Fonts/",
            os.path.expanduser("~/Library/Fonts/")
        ]
        
        fonts = {}
        
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for root, _, files in os.walk(font_dir):
                    for file in files:
                        if file.endswith(('.ttf', '.otf', '.ttc')):
                            # 확장자 없는 폰트 이름 추출
                            font_name = os.path.splitext(file)[0]
                            fonts[font_name] = os.path.join(root, file)
                            
                            # 일반적인 폰트 이름 패턴도 추가
                            name_variants = [
                                font_name, 
                                font_name.replace('-', ''), 
                                font_name.replace(' ', ''),
                                font_name.lower(), 
                                font_name.upper()
                            ]
                            
                            for variant in name_variants:
                                if variant not in fonts:
                                    fonts[variant] = os.path.join(root, file)
        
        return fonts
    
    def find_font(self, font_name: str, fallback_sequence: Optional[List[str]] = None) -> str:
        """
        이름으로 폰트 파일 경로 찾기 (폴백 사용)
        
        Args:
            font_name: 원하는 폰트 이름
            fallback_sequence: 폴백 폰트 이름 목록
            
        Returns:
            폰트 파일 경로
        """
        # 폴백이 제공되지 않은 경우 일반적인 기본값 사용
        if fallback_sequence is None:
            fallback_sequence = [
                "Arial", "DejaVuSans", "NotoSans", "Roboto", 
                "OpenSans", "FreeSans", "LiberationSans"
            ]
        
        # 먼저 정확한 일치 시도
        if font_name in self.system_fonts:
            return self.system_fonts[font_name]
        
        # 대소문자 구분 없이 일치 시도
        for system_font in self.system_fonts:
            if font_name.lower() == system_font.lower():
                return self.system_fonts[system_font]
        
        # 부분 일치 시도
        for system_font in self.system_fonts:
            if font_name.lower() in system_font.lower():
                return self.system_fonts[system_font]
        
        # 폴백 시도
        for fallback in fallback_sequence:
            if fallback in self.system_fonts:
                logger.warning(f"폰트 '{font_name}'을(를) 찾을 수 없어 폴백 사용: {fallback}")
                return self.system_fonts[fallback]
        
        # 마지막 수단: 사용 가능한 아무 폰트나 반환
        if self.system_fonts:
            first_font = next(iter(self.system_fonts.values()))
            logger.warning(f"폰트 '{font_name}'과(와) 폴백을 찾을 수 없어 다음을 사용: {first_font}")
            return first_font
        
        raise ValueError("시스템에서 사용 가능한 폰트를 찾을 수 없습니다")
    
    def generate_thumbnail(self,
                       main_text: str,
                       subtitle_text: Optional[str] = None,
                       background_image: Optional[str] = None,
                       output_path: str = "thumbnail.png") -> str:
        """
        썸네일 이미지 생성
        
        Args:
            main_text: 표시할 주 텍스트
            subtitle_text: 표시할 부제목 텍스트 (옵션)
            background_image: 배경 이미지 경로 (옵션)
            output_path: 출력 이미지 저장 경로
            
        Returns:
            생성된 썸네일 경로
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap
            
            # 설정 가져오기
            thumbnail_config = self.config.get("thumbnail", {})
            width = thumbnail_config.get("width", 1280)
            height = thumbnail_config.get("height", 720)
            bg_color = thumbnail_config.get("background_color", "#000033")
            text_color = thumbnail_config.get("text_color", "#FFFFFF")
            highlight_color = thumbnail_config.get("highlight_color", "#FFD700")
            font_name = thumbnail_config.get("font", "Arial")
            title_size = thumbnail_config.get("title_size", 72)
            subtitle_size = thumbnail_config.get("subtitle_size", 48)
            padding = thumbnail_config.get("padding", 50)
            shadow = thumbnail_config.get("shadow", True)
            shadow_color = thumbnail_config.get("shadow_color", "#00000080")
            overlay_opacity = thumbnail_config.get("overlay_opacity", 0.5)
            
            # 이미지 생성
            if background_image and os.path.exists(background_image):
                # 제공된 배경 이미지 사용
                try:
                    img = Image.open(background_image).convert("RGBA")
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # 텍스트 가시성을 위한 어두운 오버레이 추가
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, int(255 * overlay_opacity)))
                    img = Image.alpha_composite(img, overlay)
                    
                except Exception as e:
                    logger.error(f"배경 이미지 처리 오류: {str(e)}")
                    # 색상 배경으로 폴백
                    img = Image.new('RGBA', (width, height), bg_color)
            else:
                # 단색 배경 사용
                img = Image.new('RGBA', (width, height), bg_color)
            
            # 폰트 파일 찾기
            try:
                title_font_path = self.find_font(font_name)
                title_font = ImageFont.truetype(title_font_path, title_size)
                subtitle_font = ImageFont.truetype(title_font_path, subtitle_size)
            except Exception as e:
                logger.error(f"폰트 로드 오류: {str(e)}")
                # 기본 폰트로 폴백
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
            
            # 드로잉 컨텍스트 생성
            draw = ImageDraw.Draw(img)
            
            # 주 텍스트 그리기
            main_text = main_text.strip()
            main_lines = textwrap.wrap(main_text, width=20)  # 글꼴 크기에 따라 너비 조정
            line_height = title_size * 1.2
            
            # 주 텍스트의 총 높이 계산
            total_main_height = len(main_lines) * line_height
            
            # 수직 위치 계산
            y_position = (height - total_main_height) // 2
            
            # 부제목이 있으면 수직 위치 조정
            if subtitle_text:
                subtitle_lines = textwrap.wrap(subtitle_text, width=30)
                subtitle_height = len(subtitle_lines) * (subtitle_size * 1.2)
                y_position = (height - (total_main_height + subtitle_height + 20)) // 2
            
            # 그림자가 활성화된 경우 주 텍스트 그리기
            for line in main_lines:
                text_width = draw.textlength(line, font=title_font)
                x_position = (width - text_width) // 2
                
                if shadow:
                    # 그림자 그리기
                    shadow_offset = 3
                    draw.text((x_position + shadow_offset, y_position + shadow_offset), 
                             line, font=title_font, fill=shadow_color)
                
                # 텍스트 그리기
                draw.text((x_position, y_position), line, font=title_font, fill=text_color)
                y_position += line_height
            
            # 부제목 그리기
            if subtitle_text:
                y_position += 20  # 주 텍스트와 부제목 사이 간격 추가
                subtitle_text = subtitle_text.strip()
                subtitle_lines = textwrap.wrap(subtitle_text, width=30)
                
                for line in subtitle_lines:
                    text_width = draw.textlength(line, font=subtitle_font)
                    x_position = (width - text_width) // 2
                    
                    if shadow:
                        # 그림자 그리기
                        shadow_offset = 2
                        draw.text((x_position + shadow_offset, y_position + shadow_offset), 
                                 line, font=subtitle_font, fill=shadow_color)
                    
                    # 텍스트 그리기
                    draw.text((x_position, y_position), line, font=subtitle_font, fill=highlight_color)
                    y_position += subtitle_size * 1.2
            
            # 이미지 저장
            output_file = Path(output_path)
            ensure_dir_exists(str(output_file.parent))
            
            # JPEG 또는 PNG로 저장하기 위해 RGB로 변환
            img = img.convert("RGB")
            img.save(output_file)
            
            logger.info(f"썸네일 생성됨: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"썸네일 생성 오류: {str(e)}")
            raise
    
    def apply_template(self,
                     template_name: str,
                     main_text: str,
                     subtitle_text: Optional[str] = None,
                     output_path: str = "thumbnail.png") -> str:
        """
        미리 정의된 템플릿을 적용하여 썸네일 생성
        
        Args:
            template_name: 템플릿 이름
            main_text: 표시할 주 텍스트
            subtitle_text: 표시할 부제목 텍스트 (옵션)
            output_path: 출력 이미지 저장 경로
            
        Returns:
            생성된 썸네일 경로
        """
        templates = self.config.get("templates", {})
        
        if template_name not in templates:
            logger.warning(f"템플릿 '{template_name}'을(를) 찾을 수 없어 기본값 사용")
            template_name = "simple"
        
        # 원본 설정 저장
        original_config = self.config.copy()
        
        # 템플릿 설정 적용
        template = templates[template_name]
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = {}
            
        for key, value in template.items():
            self.config["thumbnail"][key] = value
        
        # 템플릿 설정으로 썸네일 생성
        result_path = self.generate_thumbnail(
            main_text=main_text,
            subtitle_text=subtitle_text,
            output_path=output_path
        )
        
        # 원본 설정 복원
        self.config = original_config
        
        return result_path