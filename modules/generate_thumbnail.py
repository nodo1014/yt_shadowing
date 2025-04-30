#!/usr/bin/env python3
"""
File: generate_thumbnail.py
Description: Generate thumbnail images for shadowing practice videos
Input: Text content, background image or color
Output: Thumbnail image file (.png, .jpg)
Libraries: pillow, yaml
Updates: 
  - 2025-05-01: Initial version

This module creates attractive thumbnails for shadowing practice videos
featuring the key expressions and custom backgrounds.
"""

import os
import yaml
import logging
import textwrap
import random
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Union

# Third-party imports
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("thumbnail_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    """Class for generating thumbnails for shadowing videos"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the ThumbnailGenerator
        
        Args:
            config_path: Optional path to config.yaml for settings
        """
        self.config = {}
        self.default_config = {
            "thumbnail": {
                "width": 1280,
                "height": 720,
                "background_color": "#000033",
                "text_color": "#FFFFFF",
                "highlight_color": "#FFD700",
                "font": "Pretendard-Bold",
                "title_size": 72,
                "subtitle_size": 48,
                "padding": 50,
                "shadow": True,
                "shadow_color": "#00000080",
                "overlay_opacity": 0.5
            }
        }
        
        if config_path:
            self.load_config(config_path)
        else:
            self.config = self.default_config

        # Initialize font paths
        self.system_fonts = self._find_system_fonts()

    def load_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to config.yaml file
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                loaded_config = yaml.safe_load(file)
            
            # Merge with default config, preserving default values not in loaded config
            if "thumbnail" not in loaded_config:
                loaded_config["thumbnail"] = {}
            
            for key, value in self.default_config["thumbnail"].items():
                if key not in loaded_config["thumbnail"]:
                    loaded_config["thumbnail"][key] = value
            
            self.config = loaded_config
            logger.info(f"Loaded thumbnail configuration from: {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            self.config = self.default_config
    
    def _find_system_fonts(self) -> Dict[str, str]:
        """
        Find available fonts in system directories
        
        Returns:
            Dictionary mapping font names to paths
        """
        font_dirs = [
            # Linux system fonts
            "/usr/share/fonts/",
            "/usr/local/share/fonts/",
            # User fonts on Linux
            os.path.expanduser("~/.local/share/fonts/"),
            os.path.expanduser("~/.fonts/"),
            # Windows fonts
            "C:\\Windows\\Fonts\\",
            # macOS fonts
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
                            # Extract font name without extension
                            font_name = os.path.splitext(file)[0]
                            fonts[font_name] = os.path.join(root, file)
                            
                            # Also add common font naming patterns
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
    
    def find_font(self, font_name: str, fallback_sequence: List[str] = None) -> str:
        """
        Find a font file path by name with fallbacks
        
        Args:
            font_name: Name of the desired font
            fallback_sequence: List of fallback font names
            
        Returns:
            Path to the font file
        """
        # If no fallback provided, use common defaults
        if fallback_sequence is None:
            fallback_sequence = [
                "Arial", "DejaVuSans", "NotoSans", "Roboto", 
                "OpenSans", "FreeSans", "LiberationSans"
            ]
        
        # First try exact match
        if font_name in self.system_fonts:
            return self.system_fonts[font_name]
        
        # Try case-insensitive match
        for system_font in self.system_fonts:
            if font_name.lower() == system_font.lower():
                return self.system_fonts[system_font]
        
        # Try partial match
        for system_font in self.system_fonts:
            if font_name.lower() in system_font.lower():
                return self.system_fonts[system_font]
        
        # Try fallbacks
        for fallback in fallback_sequence:
            if fallback in self.system_fonts:
                logger.warning(f"Font '{font_name}' not found, using fallback: {fallback}")
                return self.system_fonts[fallback]
        
        # Last resort: return any available font
        if self.system_fonts:
            first_font = next(iter(self.system_fonts.values()))
            logger.warning(f"Font '{font_name}' and fallbacks not found, using: {first_font}")
            return first_font
        
        raise ValueError("No usable fonts found in the system")
    
    def generate_thumbnail(self, 
                           main_text: str, 
                           subtitle_text: Optional[str] = None,
                           background_image: Optional[str] = None,
                           output_path: str = "thumbnail.png") -> str:
        """
        Generate a thumbnail image
        
        Args:
            main_text: Main text to display
            subtitle_text: Optional subtitle text
            background_image: Optional path to background image
            output_path: Path to save the output image
            
        Returns:
            Path to the generated thumbnail
        """
        try:
            # Get configuration
            thumbnail_config = self.config.get("thumbnail", {})
            width = thumbnail_config.get("width", 1280)
            height = thumbnail_config.get("height", 720)
            bg_color = thumbnail_config.get("background_color", "#000033")
            text_color = thumbnail_config.get("text_color", "#FFFFFF")
            highlight_color = thumbnail_config.get("highlight_color", "#FFD700")
            font_name = thumbnail_config.get("font", "Pretendard-Bold")
            title_size = thumbnail_config.get("title_size", 72)
            subtitle_size = thumbnail_config.get("subtitle_size", 48)
            padding = thumbnail_config.get("padding", 50)
            shadow = thumbnail_config.get("shadow", True)
            shadow_color = thumbnail_config.get("shadow_color", "#00000080")
            overlay_opacity = thumbnail_config.get("overlay_opacity", 0.5)
            
            # Create image
            if background_image and os.path.exists(background_image):
                # Use provided background image
                try:
                    img = Image.open(background_image).convert("RGBA")
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Add dark overlay for better text visibility
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, int(255 * overlay_opacity)))
                    img = Image.alpha_composite(img, overlay)
                    
                except Exception as e:
                    logger.error(f"Error processing background image: {str(e)}")
                    # Fall back to color background
                    img = Image.new('RGBA', (width, height), bg_color)
            else:
                # Use solid color background
                img = Image.new('RGBA', (width, height), bg_color)
            
            # Find font file
            try:
                title_font_path = self.find_font(font_name)
                title_font = ImageFont.truetype(title_font_path, title_size)
                subtitle_font = ImageFont.truetype(title_font_path, subtitle_size)
            except Exception as e:
                logger.error(f"Error loading font: {str(e)}")
                # Fall back to default font
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
            
            # Create draw context
            draw = ImageDraw.Draw(img)
            
            # Draw main text
            main_text = main_text.strip()
            main_lines = textwrap.wrap(main_text, width=20)  # Adjust width based on font size
            line_height = title_size * 1.2
            
            # Calculate total height of main text
            total_main_height = len(main_lines) * line_height
            
            # Calculate vertical positioning
            y_position = (height - total_main_height) // 2
            
            # If we have subtitle, adjust vertical position
            if subtitle_text:
                subtitle_lines = textwrap.wrap(subtitle_text, width=30)
                subtitle_height = len(subtitle_lines) * (subtitle_size * 1.2)
                y_position = (height - (total_main_height + subtitle_height + 20)) // 2
            
            # Draw main text with shadow if enabled
            for line in main_lines:
                text_width = draw.textlength(line, font=title_font)
                x_position = (width - text_width) // 2
                
                if shadow:
                    # Draw shadow
                    shadow_offset = 3
                    draw.text((x_position + shadow_offset, y_position + shadow_offset), 
                             line, font=title_font, fill=shadow_color)
                
                # Draw text
                draw.text((x_position, y_position), line, font=title_font, fill=text_color)
                y_position += line_height
            
            # Draw subtitle if provided
            if subtitle_text:
                y_position += 20  # Add spacing between main text and subtitle
                subtitle_text = subtitle_text.strip()
                subtitle_lines = textwrap.wrap(subtitle_text, width=30)
                
                for line in subtitle_lines:
                    text_width = draw.textlength(line, font=subtitle_font)
                    x_position = (width - text_width) // 2
                    
                    if shadow:
                        # Draw shadow
                        shadow_offset = 2
                        draw.text((x_position + shadow_offset, y_position + shadow_offset), 
                                 line, font=subtitle_font, fill=shadow_color)
                    
                    # Draw text
                    draw.text((x_position, y_position), line, font=subtitle_font, fill=highlight_color)
                    y_position += subtitle_size * 1.2
            
            # Save the image
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to RGB for saving as JPEG or PNG
            img = img.convert("RGB")
            img.save(output_path)
            
            logger.info(f"Generated thumbnail: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            raise
    
    def generate_thumbnail_grid(self,
                               texts: List[str],
                               output_path: str = "thumbnail_grid.png",
                               columns: int = 2,
                               background_color: Optional[str] = None) -> str:
        """
        Generate a grid of thumbnail designs for the same text
        
        Args:
            texts: List of text strings for thumbnails
            output_path: Path to save the output image
            columns: Number of columns in the grid
            background_color: Optional background color
            
        Returns:
            Path to the generated thumbnail grid
        """
        try:
            thumbnail_config = self.config.get("thumbnail", {})
            single_width = thumbnail_config.get("width", 1280)
            single_height = thumbnail_config.get("height", 720)
            
            # Scale down for the grid
            scale = 0.5
            thumb_width = int(single_width * scale)
            thumb_height = int(single_height * scale)
            
            # Calculate grid dimensions
            num_texts = len(texts)
            rows = (num_texts + columns - 1) // columns  # Ceiling division
            
            # Create a big canvas for the grid
            grid_width = thumb_width * columns
            grid_height = thumb_height * rows
            
            bg_color = background_color or "#222222"
            grid_img = Image.new('RGB', (grid_width, grid_height), bg_color)
            
            # Generate a thumbnail for each text
            for i, text in enumerate(texts):
                row = i // columns
                col = i % columns
                
                # Create a temporary file for this thumbnail
                temp_output = f"temp_thumb_{i}.png"
                
                try:
                    # Generate the thumbnail
                    thumb_path = self.generate_thumbnail(
                        main_text=text,
                        output_path=temp_output
                    )
                    
                    # Load and paste into the grid
                    thumb = Image.open(thumb_path).resize((thumb_width, thumb_height))
                    grid_img.paste(thumb, (col * thumb_width, row * thumb_height))
                    
                    # Clean up temp file
                    os.remove(temp_output)
                    
                except Exception as e:
                    logger.error(f"Error generating thumbnail {i}: {str(e)}")
            
            # Save the grid
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            grid_img.save(output_path)
            
            logger.info(f"Generated thumbnail grid: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating thumbnail grid: {str(e)}")
            raise

    def extract_frame_from_video(self,
                                video_path: str,
                                time_position: Union[str, float],
                                output_path: Optional[str] = None) -> str:
        """
        Extract a frame from a video for use as thumbnail background
        
        Args:
            video_path: Path to video file
            time_position: Position in seconds or as "HH:MM:SS.mmm"
            output_path: Path to save the extracted frame
            
        Returns:
            Path to the extracted frame
        """
        try:
            import ffmpeg
            
            if output_path is None:
                output_path = f"frame_{os.path.basename(video_path)}.jpg"
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build ffmpeg command
            stream = ffmpeg.input(video_path, ss=time_position)
            stream = ffmpeg.output(stream, str(output_path), vframes=1)
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
            
            logger.info(f"Extracted frame from video at position {time_position}: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error extracting frame from video: {str(e)}")
            raise
    
    def apply_template(self,
                      template_name: str,
                      main_text: str,
                      subtitle_text: Optional[str] = None,
                      output_path: str = "thumbnail.png") -> str:
        """
        Apply a predefined template to generate a thumbnail
        
        Args:
            template_name: Name of the template
            main_text: Main text to display
            subtitle_text: Optional subtitle text
            output_path: Path to save the output image
            
        Returns:
            Path to the generated thumbnail
        """
        templates = {
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
        
        if template_name not in templates:
            logger.warning(f"Template '{template_name}' not found, using default")
            template_name = "simple"
        
        # Save original config
        original_config = self.config.copy()
        
        # Apply template settings
        template = templates[template_name]
        if "thumbnail" not in self.config:
            self.config["thumbnail"] = {}
            
        for key, value in template.items():
            self.config["thumbnail"][key] = value
        
        # Generate thumbnail with template settings
        result_path = self.generate_thumbnail(
            main_text=main_text,
            subtitle_text=subtitle_text,
            output_path=output_path
        )
        
        # Restore original config
        self.config = original_config
        
        return result_path

def main():
    """Main function to run the thumbnail generator from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate thumbnails for shadowing videos')
    parser.add_argument('--text', '-t', type=str, required=True, 
                        help='Main text for the thumbnail')
    parser.add_argument('--subtitle', '-s', type=str,
                        help='Subtitle text (optional)')
    parser.add_argument('--output', '-o', type=str, default="thumbnail.png",
                        help='Output file path')
    parser.add_argument('--config', '-c', type=str,
                        help='Path to config.yaml file')
    parser.add_argument('--background', '-b', type=str,
                        help='Path to background image')
    parser.add_argument('--template', type=str, choices=['simple', 'professional', 'vibrant', 'minimalist', 'dark'],
                        help='Use a predefined template')
    parser.add_argument('--extract-from', type=str,
                        help='Extract background from video at specified position (e.g., 00:01:23)')
                        
    args = parser.parse_args()
    
    generator = ThumbnailGenerator(args.config)
    
    background_image = args.background
    
    # Extract background from video if requested
    if args.extract_from and not background_image:
        if ':' in args.extract_from:
            # Parse as time string
            time_position = args.extract_from
        else:
            # Parse as seconds
            time_position = float(args.extract_from)
        
        background_image = generator.extract_frame_from_video(
            video_path=args.extract_from.split(':')[0],
            time_position=time_position,
            output_path="temp_background.jpg"
        )
    
    # Generate using template if specified
    if args.template:
        thumbnail_path = generator.apply_template(
            template_name=args.template,
            main_text=args.text,
            subtitle_text=args.subtitle,
            output_path=args.output
        )
    else:
        # Generate with standard settings
        thumbnail_path = generator.generate_thumbnail(
            main_text=args.text,
            subtitle_text=args.subtitle,
            background_image=background_image,
            output_path=args.output
        )
    
    print(f"Generated thumbnail: {thumbnail_path}")

if __name__ == "__main__":
    main()
