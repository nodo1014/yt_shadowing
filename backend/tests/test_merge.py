#!/usr/bin/env python3

from modules.merge_final_video import VideoMerger

def main():
    # VideoMerger 클래스 인스턴스 생성
    merger = VideoMerger("config.yaml")
    
    # 비디오 세그먼트 병합
    success = merger.merge_segments(
        segments=["output/xmen_repeat.mp4"],
        output_path="final/xmen_final.mp4",
        title="영어 쉐도잉 X-Men",
        watermark="@영어쉐도잉",
        quality="high"
    )
    
    if success:
        print("비디오 병합 성공!")
    else:
        print("비디오 병합 실패!")

if __name__ == "__main__":
    main()
