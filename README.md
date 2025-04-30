# YouTube Shadowing

영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구입니다.

## 주요 기능

- 자막 인덱싱 및 검색
- 비디오 클립 추출
- 반복 영상 생성
- 썸네일 생성
- 최종 영상 병합

## 설치 방법

```bash
pip install -r requirements.txt
```

## 사용 방법

1. `config.yaml` 파일을 수정하여 설정
2. 자막 인덱싱: `python -m modules.index_subtitles`
3. 비디오 클립 추출: `python -m modules.extract_video_clip`
4. 반복 영상 생성: `python -m modules.generate_repeat_video`

## 프로젝트 구조

- `api/`: API 관련 파일
- `extracted_clips/`: 추출된 비디오 클립
- `modules/`: 핵심 기능 모듈
- `projects/`: 프로젝트 파일
- `user-configs/`: 사용자 설정 파일