#!/usr/bin/env python3
"""
File: merge_final_video.py
Description: Merge all video components into a final video with intro, segments, and outro
Input: Configuration, video segments, intro/outro templates
Output: Final merged video for upload
Libraries: ffmpeg-python, yaml, os, pathlib
Updates: 
  - 2025-05-01: Initial version
  - 2025-05-01: Added support for MKV file format

This module combines all shadowing video components (intro, segments, outro)
into a final polished video ready for upload.
"""

import os
import sys
import yaml
import json
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import subprocess

# Third-party imports
import ffmpeg

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("merge_video.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoMerger:
    """Class for merging video segments into a final video"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the VideoMerger
        
        Args:
            config_path: Optional path to config.yaml for default settings
        """
        self.config = {}
        self.temp_files = []
        
        # Default config
        self.default_config = {
            "output_format": "mp4",
            "video_codec": "libx264",
            "audio_codec": "aac",
            "video_bitrate": "3M",
            "audio_bitrate": "192k",
            "resolution": "1920x1080",
            "transition": {
                "type": "fade",
                "duration": 0.5
            },
            "intro": {
                "enabled": True,
                "duration": 3,
                "template": "basic"
            },
            "outro": {
                "enabled": True,
                "duration": 5,
                "template": "basic"
            }
        }
        
        if config_path:
            self.load_config(config_path)
        else:
            self.config = self.default_config
    
    def load_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to config.yaml file
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                loaded_config = yaml.safe_load(file)
            
            # Extract merger-specific settings if available
            if "merger" in loaded_config:
                merger_config = loaded_config["merger"]
            else:
                merger_config = loaded_config
            
            # Merge with default config
            for key, default_value in self.default_config.items():
                if key not in merger_config:
                    merger_config[key] = default_value
                elif isinstance(default_value, dict) and isinstance(merger_config[key], dict):
                    # For nested dictionaries, add any missing keys
                    for nested_key, nested_value in default_value.items():
                        if nested_key not in merger_config[key]:
                            merger_config[key][nested_key] = nested_value
            
            self.config = merger_config
            logger.info(f"Loaded configuration from: {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            self.config = self.default_config
    
    async def merge_videos(self, 
                     video_segments: List[str], 
                     output_path: str,
                     title: str = "",
                     subtitle: Optional[str] = None,
                     add_intro: bool = True,
                     add_outro: bool = True) -> bool:
        """
        Merge multiple video segments into one final video
        
        Args:
            video_segments: List of paths to video segments
            output_path: Path to save the final merged video
            title: Video title for intro/outro
            subtitle: Optional subtitle for intro/outro
            add_intro: Whether to add intro
            add_outro: Whether to add outro
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Merging {len(video_segments)} video segments")
            
            if not video_segments:
                logger.error("No video segments provided")
                return False
            
            processed_segments = []
            
            # Create intro if enabled
            if add_intro and self.config.get("intro", {}).get("enabled", True):
                intro_path = await self._create_intro(title, subtitle)
                if intro_path:
                    processed_segments.append(intro_path)
            
            # Process each segment
            for i, segment in enumerate(video_segments):
                segment_path = Path(segment)
                if not segment_path.exists():
                    logger.warning(f"Segment not found: {segment_path}")
                    continue
                
                # Add segment to the list
                processed_segments.append(str(segment_path))
                
                # Add transitions between segments if needed
                if i < len(video_segments) - 1 and self.config.get("transition", {}).get("type") != "none":
                    transition_path = await self._create_transition()
                    if transition_path:
                        processed_segments.append(transition_path)
            
            # Create outro if enabled
            if add_outro and self.config.get("outro", {}).get("enabled", True):
                outro_path = await self._create_outro(title, subtitle)
                if outro_path:
                    processed_segments.append(outro_path)
            
            # Merge all processed segments
            if not processed_segments:
                logger.error("No processed segments to merge")
                return False
                
            success = await self._concatenate_videos(processed_segments, output_path)
            if success:
                logger.info(f"Successfully merged videos to: {output_path}")
                return True
            else:
                logger.error("Failed to merge videos")
                return False
                
        except Exception as e:
            logger.error(f"Error merging videos: {str(e)}")
            return False
        finally:
            self._cleanup_temp_files()
    
    def merge_segments(self, segments: List[str], output_path: str, title: str = None, intro: str = None, 
                       outro: str = None, watermark: str = None, quality: str = 'high', 
                       format: str = 'video') -> bool:
        """
        Merge multiple video segments into one file and add metadata
        
        Args:
            segments: List of paths to video segments
            output_path: Path to save the output video
            title: Video title text (optional)
            intro: Path to intro video (optional)
            outro: Path to outro video (optional)
            watermark: Watermark text (optional)
            quality: Output quality (low, medium, high)
            format: Output format (video, audio_only)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Merging {len(segments)} segments into {output_path}")
            
            # Check if segments exist
            for segment in segments:
                if not Path(segment).exists():
                    logger.error(f"Segment not found: {segment}")
                    return False
            
            # Check supported video formats
            supported_formats = ['.mp4', '.mkv', '.avi', '.mov', '.webm']
            for segment in segments:
                segment_path = Path(segment)
                if segment_path.suffix.lower() not in supported_formats:
                    logger.warning(f"Segment file format may not be supported: {segment_path.suffix}")
            
            # Create output directory
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create concat file
            concat_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
            self.temp_files.append(concat_file.name)
            
            with open(concat_file.name, 'w', encoding='utf-8') as f:
                # Add intro file if provided
                if intro and Path(intro).exists():
                    f.write(f"file '{Path(intro).absolute()}'\n")
                
                # Add all segment files
                for segment in segments:
                    f.write(f"file '{Path(segment).absolute()}'\n")
                
                # Add outro file if provided
                if outro and Path(outro).exists():
                    f.write(f"file '{Path(outro).absolute()}'\n")
            
            # Set encoding parameters based on quality
            quality_params = self._get_quality_params(quality)
            
            # Set output parameters for video or audio-only
            if format == 'audio_only':
                output_ext = Path(output_path).suffix.lower()
                if output_ext not in ['.mp3', '.aac', '.wav', '.ogg']:
                    logger.warning(f"Audio-only mode but output format is not an audio format: {output_ext}")
                
                # Audio-only output
                cmd = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-f', 'concat', '-safe', '0',
                    '-i', concat_file.name,
                    '-c:a', 'aac', '-b:a', '192k',
                    output_path
                ]
            else:
                # Video output
                cmd = [
                    'ffmpeg', '-y', '-loglevel', 'error',
                    '-f', 'concat', '-safe', '0',
                    '-i', concat_file.name,
                    '-c:v', quality_params['codec'],
                    '-crf', str(quality_params['crf']),
                    '-preset', quality_params['preset'],
                    '-c:a', 'aac', '-b:a', '192k',
                ]
                
                # Add watermark if provided
                if watermark:
                    cmd.extend([
                        '-vf', f"drawtext=text='{watermark}':fontcolor=white@0.5:fontsize=24:"
                               f"x=w-tw-10:y=h-th-10:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    ])
                
                cmd.append(output_path)
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False
            
            logger.info(f"Successfully merged segments into {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging segments: {str(e)}")
            return False

    def _get_quality_params(self, quality: str) -> Dict[str, Any]:
        """
        Get encoding parameters based on quality
        
        Args:
            quality: Quality level (low, medium, high)
        
        Returns:
            Dictionary with encoding parameters
        """
        quality_map = {
            'low': {'codec': 'libx264', 'crf': 28, 'preset': 'ultrafast'},
            'medium': {'codec': 'libx264', 'crf': 23, 'preset': 'medium'},
            'high': {'codec': 'libx264', 'crf': 18, 'preset': 'slow'}
        }
        return quality_map.get(quality, quality_map['high'])

# The rest of the code remains unchanged
# ...
