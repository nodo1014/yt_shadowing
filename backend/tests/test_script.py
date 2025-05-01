#!/usr/bin/env python3
from modules.extract_video_clip import VideoClipper
import os

clipper = VideoClipper()
print("지원되는 비디오 포맷:", clipper.supported_video_formats)
print("지원되는 오디오 포맷:", clipper.supported_audio_formats)

# 존재하는 파일로 테스트
input_file = "extracted_clips/xmen_clip.mp4"
if os.path.exists(input_file):
    print(f"{input_file} 파일 존재 확인")
    # 영어 오디오 검색 기능 테스트
    english_stream = clipper.get_english_audio_stream(input_file)
    print(f"영어 오디오 스트림 인덱스: {english_stream}")
    
    # 클립 추출 테스트
    result = clipper.extract_clip(
        input_file,
        "00:00:00",
        "00:00:05",
        "extracted_clips/test_output.mp4",
        english_audio_only=True
    )
    print(f"클립 추출 결과: {'성공' if result else '실패'}")
else:
    print(f"{input_file} 파일이 존재하지 않습니다.")
