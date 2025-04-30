# 영어 쉐도잉 자동화 시스템 가이드

**최종 업데이트: 2025년 5월 1일**

## 개요

영어 쉐도잉 자동화 시스템은 YouTube 영상을 활용하여 효과적인 영어 학습 자료를 만드는 도구입니다. 원하는 영상의 일부를 추출하고, 학습에 최적화된 반복 영상을 생성하여 영어 발음과 표현 습득을 도와줍니다.

## 주요 기능

1. **영상 추출**: YouTube 영상에서 원하는 부분만 추출
2. **반복 영상 생성**: 쉐도잉 학습에 최적화된 반복 영상 생성
3. **자막 처리**: 영어 자막 추출 및 한국어 번역 자동 생성
4. **맞춤형 썸네일**: 학습 내용 기반 썸네일 자동 생성
5. **최종 영상 편집**: 인트로/아웃트로가 포함된 완성도 높은 영상 제작
6. **다양한 파일 형식 지원**: MP4, MKV, AVI, MOV, WEBM 등 다양한 비디오 파일 형식 지원

## 시작하기

### 필요 요구 사항

- Python 3.9 이상
- FFmpeg
- Internet 연결

### 설치 방법

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필요 패키지 설치
pip install -r requirements.txt
```

## 기본 사용법

### 1. 영상 추출하기

```bash
python modules/extract_video_clip.py --url "https://www.youtube.com/watch?v=EXAMPLE" --start "00:01:30" --end "00:02:45" --output "clips/example.mp4"
```

또는 로컬 비디오 파일에서 추출:

```bash
python modules/extract_video_clip.py --input "videos/my_video.mkv" --start "00:01:30" --end "00:02:45" --output "clips/example.mp4"
```

### 2. 자막 추출 및 번역

```bash
# 자막 추출
python modules/extract_video_clip.py --url "https://www.youtube.com/watch?v=EXAMPLE" --subtitle_only

# 한국어 번역 생성
python modules/subtitle_matcher.py --subtitle "subtitles/example.srt" --output "translations/example.json"
```

### 3. 반복 영상 생성

```bash
python modules/generate_repeat_video.py --video "clips/example.mp4" --subtitle "subtitles/example.srt" --output "output/example_shadowing.mp4" --config "config.yaml" --translation "translations/example.json"
```

### 4. 썸네일 생성

```bash
python modules/generate_thumbnail.py --text "핵심 표현" --subtitle "영어 쉐도잉" --output "thumbnails/example.jpg" --template "professional"
```

### 5. 최종 영상 병합

```bash
python modules/merge_final_video.py --segments "output/example_shadowing.mp4" --output "final/example_final.mp4" --title "영어 쉐도잉 #1" --watermark "@영어쉐도잉"
```

## 고급 기능 가이드

### 난이도별 학습 모드

이제 학습자의 수준에 맞게 난이도를 선택할 수 있습니다:

```bash
# 학습 난이도 설정 후 영상 생성
python main.py --video "clips/example.mp4" --level "beginner"  # 'beginner', 'intermediate', 'advanced' 중 선택
```

초보자 모드는 더 느린 속도와 긴 휴식 시간, 더 많은 반복 횟수를 제공하여 학습 효과를 높입니다. 고급자 모드는 빠른 진행과 적은 반복으로 도전적인 연습이 가능합니다.

### 핵심 구문 하이라이트

중요한 표현이나 학습이 필요한 구문을 강조할 수 있습니다:

```bash
# 핵심 구문 파일 생성
echo '{"key_phrases": ["특별한 표현", "중요한 구문"]}' > key_phrases.json

# 핵심 구문 하이라이트가 적용된 영상 생성
python modules/generate_repeat_video.py --video "clips/example.mp4" --subtitle "subtitles/example.srt" --output "output/example_highlighted.mp4" --key_phrases "key_phrases.json"
```

### 발음 연습 특화 기능

한국인이 어려워하는 특정 발음을 집중 연습할 수 있습니다:

```bash
# 발음 연습 모드로 영상 생성
python main.py --video "clips/example.mp4" --pronunciation_focus "r,l,th" --ipa_display
```

해당 설정은 r, l, th 발음이 포함된 단어를 하이라이트하고 국제 음성 기호(IPA)를 표시하여 정확한 발음 학습을 돕습니다.

### 다양한 내보내기 옵션

학습 환경에 맞는 형식과 품질로 내보낼 수 있습니다:

```bash
# 오디오만 추출 (이동 중 학습용)
python modules/merge_final_video.py --segments "output/example_shadowing.mp4" --output "final/example_audio.mp3" --format "audio_only"

# 저용량 모바일 버전 생성
python modules/merge_final_video.py --segments "output/example_shadowing.mp4" --output "final/example_mobile.mp4" --quality "low"

# MKV 형식으로 출력 생성
python modules/merge_final_video.py --segments "output/example_shadowing.mp4" --output "final/example_final.mkv" --title "영어 쉐도잉 #1"
```

### 지원되는 비디오 형식

이 시스템은 다양한 비디오 포맷을 지원합니다:

- MP4 (가장 일반적)
- MKV (고품질 비디오에 적합)
- AVI
- MOV
- WEBM

MKV 파일은 고품질 비디오와 다중 오디오 트랙을 지원하는 컨테이너 형식으로, 고품질 영상 작업에 적합합니다.

## 설정 커스터마이징

`config.yaml` 파일을 수정하여 다양한 설정을 변경할 수 있습니다:

```yaml
# 예시 설정
repeat_count: 3 # 반복 횟수
subtitle_mode: [no_subtitle, en_ko, en_ko] # 각 반복별 자막 모드
```

자세한 설정 옵션은 `config.yaml` 파일의 주석을 참고하세요.

## 자주 묻는 질문 (FAQ)

**Q: API 키는 어디서 설정하나요?**  
A: 환경 변수 또는 `user-configs/api_keys.yaml` 파일에 설정할 수 있습니다.

**Q: 자막 번역이 정확하지 않을 때는 어떻게 하나요?**  
A: `translations` 폴더의 JSON 파일을 직접 수정하여 번역을 개선할 수 있습니다.

**Q: 저작권 문제는 없나요?**  
A: 본 도구는 개인 학습 목적으로만 사용하시고, 생성된 영상을 공유하거나 상업적으로 활용할 경우 저작권 문제가 발생할 수 있습니다.

## 문제해결

문제가 발생하면 다음 조치를 취해보세요:

1. 로그 파일 확인: `*.log` 파일들이 오류 메시지를 포함하고 있을 수 있습니다.
2. 최신 버전 확인: `git pull` 명령으로 최신 버전을 유지하세요.
3. 의존성 패키지 업데이트: `pip install -r requirements.txt --upgrade`

## 향후 개발 계획

- 학습 진도 추적 및 분석 기능
- 모바일 앱 연동
- 커뮤니티 기반 학습 자료 공유 시스템
