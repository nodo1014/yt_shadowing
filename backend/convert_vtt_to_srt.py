#!/usr/bin/env python3
import sys
import os
from webvtt import WebVTT

def convert_vtt_to_srt(vtt_file):
    """VTT 파일을 SRT 형식으로 변환합니다."""
    if not os.path.exists(vtt_file):
        print(f"파일을 찾을 수 없습니다: {vtt_file}")
        return False
    
    srt_file = vtt_file.replace('.vtt', '.srt')
    
    try:
        # WebVTT 파일 읽기
        vtt = WebVTT().read(vtt_file)
        
        # SRT 파일 작성
        with open(srt_file, 'w', encoding='utf-8') as srt:
            for i, caption in enumerate(vtt, 1):
                # 순번
                srt.write(f"{i}\n")
                
                # 시간 형식 변환 (HH:MM:SS.mmm --> HH:MM:SS,mmm)
                start = caption.start.replace('.', ',')
                end = caption.end.replace('.', ',')
                srt.write(f"{start} --> {end}\n")
                
                # 자막 텍스트
                srt.write(f"{caption.text}\n\n")
        
        print(f"변환 완료: {vtt_file} -> {srt_file}")
        return True
    except Exception as e:
        print(f"변환 실패: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python convert_vtt_to_srt.py <vtt_file1> <vtt_file2> ...")
        sys.exit(1)
    
    success = True
    for vtt_file in sys.argv[1:]:
        if not convert_vtt_to_srt(vtt_file):
            success = False
    
    sys.exit(0 if success else 1) 