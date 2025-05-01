# YouTube Shadowing

영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구입니다.

## 진행 상황

- 최신 진행상황 및 작업 내역은 [PROGRESS.md](PROGRESS.md) 파일을 참고하세요.

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

```
youtube-shadowing/
├── api/                    # API 관련 파일
├── clips/                  # 추출된 비디오 클립 (extracted_clips → clips로 이름 변경 필요)
├── config.yaml             # 전역 설정 파일
├── final/                  # 최종 병합된 영상
├── modules/                # 핵심 기능 모듈
├── output/                 # 중간 처리된 반복 영상
├── projects/               # 프로젝트 파일
├── requirements.txt        # 필요 패키지 목록
├── subtitles/              # 추출된 자막 파일 (새로 생성 필요)
├── thumbnails/             # 생성된 썸네일 이미지
├── translations/           # 번역 파일 (새로 생성 필요)
└── user-configs/           # 사용자 설정 파일
```

## 파일명 규칙

표준화된 파일명 규칙을 사용하여 프로젝트의 일관성을 유지합니다:

- 클립 파일: `{project_name}_clip_{number}.mp4`
- 자막 파일: `{project_name}_subtitle_{number}.srt`
- 번역 파일: `{project_name}_translation_{number}.json`
- 반복 영상: `{project_name}_repeat_{number}.mp4`
- 썸네일: `{project_name}_thumbnail_{number}.jpg`
- 최종 영상: `{project_name}_final_{number}.mp4`

예시: `avengers_clip_1.mp4`, `avengers_subtitle_1.srt`, `avengers_repeat_1.mp4`

## 개발자 안내

프로젝트 구조 개선을 위해 다음 작업이 필요합니다:

1. `extracted_clips/` 폴더를 `clips/`로 이름 변경
2. `subtitles/` 및 `translations/` 폴더 생성
3. 기존 파일 이름을 표준화된 규칙에 맞게 변경
4. 지시서.md 파일의 경로 참조를 실제 프로젝트 구조와 일치하도록 수정

자세한 내용은 [지시서.md](지시서.md)를 참고하세요.
