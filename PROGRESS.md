# YouTube 쉐도잉 애플리케이션 개발 진행 상황

## 프로젝트 개요
이 프로젝트는 YouTube 영상을 활용하여 언어 학습을 위한 쉐도잉 연습을 지원하는 애플리케이션을 개발하는 것을 목표로 합니다. 사용자는 YouTube 영상을 선택하고, 자막을 추출하며, 선택한 문장을 반복적으로 연습할 수 있는 맞춤형 영상을 생성할 수 있습니다.

## 기술 스택
- **프론트엔드**: Next.js, TypeScript, Tailwind CSS
- **백엔드**: FastAPI, Python
- **데이터 처리**: MoviePy, yt-dlp, YouTube Transcript API, FFmpeg
- **저장소**: 파일 시스템 기반 (SQLite 데이터베이스 계획 중)

## 개발 진행 상황

### 2023-11-30: 기본 인프라 구축 및 초기 UI 개발
- 프로젝트 구조 설정 및 환경 구성 완료 (backend/, frontend/)
- FastAPI 및 Next.js 기본 설정 완료
- 기본 라우팅 및 API 엔드포인트 구현
- YouTube 영상 다운로드 기능 구현 (backend/core/extractor.py)
- 자막 추출 및 인덱싱 기능 개발 (backend/core/subtitle.py)
- 프론트엔드 UI 컴포넌트 개발:
  - 홈 페이지 (frontend/src/app/page.tsx)
  - 비디오 관리 페이지 (frontend/src/app/videos/page.tsx)
  - 자막 관리 페이지 (frontend/src/app/subtitles/page.tsx)
  - 반복 영상 생성 페이지 (frontend/src/app/repeat/page.tsx)

### 2023-12-10: 핵심 기능 구현 및 확장
- YouTube API 연동 기능 확장
- 자막 검색 및 필터링 기능 추가
- 반복 영상 생성 알고리즘 개선
- 유저 인터페이스 업데이트 및 사용성 개선
- Docker 환경 구성 및 Docker Compose 파일 생성 (docker-compose.yml)
- 프론트엔드 컴포넌트 세분화 및 재사용성 향상

### 2023-12-30: 기능 안정화 및 사용성 개선
- 프론트엔드 반응형 디자인 구현 완료
- 자막 인덱싱 성능 최적화
- 발음 평가 기능 프로토타입 개발 (backend/core/pronunciation.py)
- 사용자 피드백 UI 개선
- 오류 처리 및 로깅 시스템 보강
- 프로젝트 문서화 확장 (README.md, CONVENTIONS.md)

### 2024-02-20: 다국어 지원 및 확장 기능
- 다국어 자막 추출 및 번역 기능 추가
- TTS(Text-to-Speech) 기능 통합 (backend/core/tts.py)
- 쉐도잉 진행 상황 추적 기능 구현
- 학습 데이터 시각화 컴포넌트 추가
- 로컬 저장 및 동기화 기능 개선
- 프론트엔드 성능 최적화

### 2024-04-10: Beta 버전 완성
- 프론트엔드/백엔드 전체 기능 통합 테스트
- 영상 플레이어 기능 확장 및 사용성 개선
- 썸네일 자동 생성 기능 구현 (backend/core/generator.py)
- 사용자 계정 및 설정 기능 추가
- 성능 최적화 및 캐싱 시스템 개선
- 로컬/클라우드 저장소 옵션 확장

### 2024-05-15: 백엔드 아키텍처 개선 및 표준화
- FastAPI 백엔드 구조를 표준 아키텍처로 재구성 (backend/app)
- 모델-라우터-서비스 레이어 분리 구현
- 의존성 주입 패턴 적용
- 에러 핸들링 미들웨어 구현 (backend/app/middleware.py)
- API 응답 형식 표준화
- Pydantic v2 모델 업데이트 및 설정 관리 개선 (backend/app/config.py)
- YouTube API 엔드포인트 구현 (backend/app/routers/youtube.py)
- SQLite 데이터베이스 연동 준비 (backend/app/db.py)
- 가상환경 자동 설정 스크립트 구현 (backend/run.sh)

### 2024-06-01: 백엔드 디렉토리 구조 개선 및 코드 리팩토링
- 기존 core 디렉토리 내 파일들을 services 디렉토리로 이동 및 구조화 (backend/app/services/)
- 핵심 비즈니스 로직을 서비스 레이어로 분리:
  - 비디오 추출 서비스 (backend/app/services/extractor.py)
  - 자막 처리 서비스 (backend/app/services/subtitle.py)
  - 클립 생성 서비스 (backend/app/services/generator.py)
  - 발음 분석 서비스 (backend/app/services/pronunciation.py)
- 라우터 파일명 통일 및 API 엔드포인트 재구성 (youtube_routes.py → youtube.py)
- FastAPI 종속성 주입 시스템 개선
- 공통 유틸리티 기능 분리 및 모듈화 (backend/app/common/)
- 정적 파일 및 템플릿 디렉토리 구조화 (backend/app/static/, backend/app/templates/)
- 타입 힌팅 및 문서화 강화

### 2024-06-15: API 경로 및 포트 설정 수정
- Next.js 프록시 설정 수정 (frontend/next.config.js)
  - 백엔드 서버 포트를 8001에서 8000으로 수정
  - `/api/video/*` 요청을 `/api/youtube/*`로 리다이렉트하는 규칙 추가
  - `/api/subtitle/*` 요청을 `/api/subtitle/*`로 직접 연결하도록 수정
- 백엔드 서버 포트 일관성 유지 (backend/run.sh)
  - 실행 스크립트의 포트를 config.py 설정과 일치하도록 8000으로 수정
- 프론트엔드 코드의 API 경로 직접 수정
  - 비디오 페이지 API 경로 수정 (frontend/src/app/videos/page.tsx)
  - 썸네일 페이지 API 경로 수정 (frontend/src/app/thumbnails/page.tsx)
  - 영상 생성기 페이지 API 경로 수정 (frontend/src/app/generator/page.tsx)
    - `/api/video/generate-repeat`를 `/api/youtube/generate-repeat`로 변경
    - `/api/video/stream/`를 `/api/youtube/stream/`로 변경
    - `/api/subtitle/get`을 `/api/youtube/subtitle/get`으로 변경
- 백엔드 자막 처리 기능 수정 (backend/app/services/subtitle.py)
  - SubtitleProcessor 클래스에 get_subtitles 메서드 추가
  - VideoExtractor 모듈 import 추가

### 2024-06-20: 파일 경로 처리 개선
- 자막 로딩 시 상대 경로 처리 로직 추가 (backend/app/routers/youtube.py)
  - 프론트엔드에서 넘어오는 다양한 형태의 경로 패턴 지원
  - `clips/파일명`, `data/clips/파일명` 등 여러 경로 형식 처리
  - 상대 경로를 backend 기준 절대 경로로 자동 변환하는 로직 구현
- 자막 관리 페이지 오류 메시지 개선
  - 비디오 파일을 찾을 수 없는 경우의 사용자 경험 향상

### 2024-06-25: 영어 자막 추출 기능 향상 및 Whisper 자동 자막 생성 구현
- 영어 자막 추출 기능 개선 (backend/app/services/subtitle.py)
  - 자동 변환 자막, 영국 영어, 미국 영어 등 다양한 자막 형식 검색 지원
  - 파일 확장자 우선순위 기반 로드 시스템 도입 (.en.srt, .en.vtt, .srt, .vtt)
  - VTT 파일을 SRT로 자동 변환하는 기능 추가
- Whisper 자막 생성 기능 구현 (backend/app/services/whisper_generator.py)
  - OpenAI Whisper 모델 기반 자동 자막 생성 서비스 구현
  - 5가지 모델 크기 지원 (tiny, base, small, medium, large)
  - 비디오 길이 기반 처리 시간 예측 로직 구현
  - 백그라운드 처리 및 진행률 표시 기능
- 자막 관리 API 엔드포인트 추가 (backend/app/routers/youtube.py)
  - 자막이 없을 경우 Whisper 생성 옵션 제공
  - 자막 생성 시간 예측 API 추가 (/api/youtube/whisper/estimate)
  - 자막 생성 요청 API 추가 (/api/youtube/whisper/generate)
  - 자막 생성 상태 확인 API 추가 (/api/youtube/whisper/status/{task_id})

### 2024-06-26: 다운로드 진행 상태 표시 및 클립 목록 개선
- 다운로드 진행 상태 표시 기능 추가 (backend/app/routers/youtube.py)
  - 비동기 백그라운드 작업으로 다운로드 처리
  - 비디오 다운로드 진행률 실시간 표시
  - 다운로드 완료 후 자막 존재 여부 자동 확인
  - 작업 상태 추적 시스템 구현
- 다운로드 상태 확인 API 추가 (/api/youtube/download/status/{task_id})
- VideoExtractor 클래스 개선 (backend/app/services/extractor.py)
  - 다운로드 진행률 콜백 함수 지원
  - 자막 언어 옵션 확장 (en, en-US, en-GB, ko)
  - 다운로드 프로세스 실시간 모니터링 개선
- 클립 목록 API 개선 (backend/app/routers/youtube.py)
  - 자막 존재 여부 표시 기능 추가
  - 가용한 자막 목록 정보 제공
  - 파일 크기 및 수정 날짜 정보 추가

### 2024-07-05: Claude 3.7 통합 및 MCP(Multi-Call Protocol) 연동 
- Claude 3.7과 YouTube 트랜스크립트 API 통합 (frontend/src/app/api/mcp-youtube-transcript/)
  - MCP 플러그인 구현으로 AI가 YouTube 자막을 직접 분석할 수 있는 기능 추가
  - 언어 코드별 자막 추출 지원 (영어, 한국어 등 다국어 지원)
  - 단락 자동 구성 옵션을 통한 가독성 높은 자막 텍스트 생성
  - 기존 백엔드 YouTube 트랜스크립트 API 활용하여 중복 개발 방지
- MCP 도구 인터페이스 표준화 및 문서화
  - TypeScript 인터페이스 정의로 타입 안정성 확보
  - 자막 텍스트, 시작 시간, 지속 시간 등 구조화된 데이터 제공
  - 다양한 형식으로 자막 데이터 반환 (텍스트, 구조화된 객체 등)

### 2024-07-10: 서버 관리 스크립트 개선 및 사용자 문서 작성
- 서버 관리 스크립트 개발 (start_servers.sh, stop_servers.sh)
  - 백엔드와 프론트엔드 서버를 동시에 시작/중지할 수 있는 스크립트 추가
  - 서버 로그를 파일로 저장하여 디버깅 용이성 향상
  - 실행 중인 서버 프로세스 정리 기능 추가
- 사용자 문서 작성 (docs/claude_youtube_integration.md)
  - Claude 3.7과 YouTube 트랜스크립트 API 통합 사용 가이드 작성
  - 통합 기능의 주요 특징 및 사용 방법 설명
  - 다양한 사용 시나리오 및 문제 해결 방법 제공
  - 언어 옵션 및 단락 구성 기능 사용 예시 추가

### 2024-07-11: 코드 리팩토링 및 UI/UX 개선
- 백엔드 리팩토링 (backend/app/routers/youtube.py, backend/app/common/utils.py)
  - 로깅 시스템 개선으로 상세한 디버깅 정보 제공
  - 경로 처리 표준화를 통한 일관된 파일 경로 관리
  - 에러 처리 개선 및 상세한 오류 정보 제공
  - 중복 코드 제거 및 재사용 가능한 유틸리티 함수 개발
- 프론트엔드 개선 (frontend/src/app/videos/page.tsx, frontend/src/app/youtube/page.tsx)
  - 비디오 클립 목록 UI 개선으로 사용성 향상
  - YouTube 다운로드 페이지 UI 현대화 및 반응형 디자인 적용
  - 실시간 다운로드 진행 상태 표시 기능 개선
  - 오류 메시지 및 성공 메시지 개선으로 사용자 피드백 강화
  - 환경 변수 활용한 백엔드 URL 설정으로 다양한 환경 지원
- 전체 시스템 안정성 개선
  - 다운로드 완료 후 자동 페이지 전환 구현
  - 유효성 검사 강화로 잘못된 입력 방지
  - 디버그 모드에서 개발자 정보 표시 기능 추가

### 2024-07-15: 환경 변수 설정 및 로그 시스템 안정화
- 환경 변수 파일 구현으로 설정 관리 개선
  - 프론트엔드 환경 변수 파일 추가 (frontend/.env.local)
  - 백엔드 환경 변수 파일 추가 (backend/.env)
  - NEXT_PUBLIC_BACKEND_URL 변수를 통한 API 서버 연결 설정
- 로깅 시스템 안정성 개선 (backend/app/common/utils.py)
  - 로그 디렉토리 경로 처리 오류 수정
  - getattr 함수를 활용한 안전한 설정 접근 구현
  - 예외 처리 강화로 로깅 실패 시에도 앱 실행 보장
  - 프로젝트 루트 기준 절대 경로 사용으로 경로 일관성 확보
- 프론트엔드-백엔드 통신 안정성 강화
  - API 요청시 환경 변수 기반 URL 사용으로 유연성 확보
  - 백엔드 서버 포트 설정 일관성 유지 (8000)
  - next.config.js의 rewrites 설정과 백엔드 API 엔드포인트 일치

### 2024-07-20: 설정 관리 및 실행 스크립트 개선
- 백엔드 설정 파일 오류 수정 (backend/app/config.py)
  - CORS_ORIGINS 설정을 Settings 클래스 내부로 이동하여 타입 오류 해결
  - 환경 변수 로딩 중 JSON 파싱 오류 수정
- 패키지 의존성 관리 개선
  - concurrently 패키지 추가로 프론트엔드/백엔드 동시 실행 지원
  - npm 스크립트 수정 및 안정화

### 2024-07-25: 자막 검색 및 영상 생성 기능 향상
- 자막 검색 기능 개선 (frontend/src/app/subtitles/page.tsx, frontend/src/app/generator/page.tsx)
  - 입력창에서 문장 복사/붙여넣기 시 따옴표(", '), 쉼표, 구두점 등 자동 제거 기능 추가
  - 자막 텍스트에서도 특수 문자를 제거한 후 검색하여 정확도 향상
  - 정규식을 활용한 텍스트 정제 기능 구현
- 순차적 영상 생성 및 병합 기능 추가
  - 다중 자막 선택 시 개별 영상 클립 생성 후 하나로 병합하는 기능 구현
  - 클립 병합 API 엔드포인트 추가 (backend/app/routers/youtube.py)
  - FFmpeg concat demuxer 방식을 활용한 효율적인 영상 병합 구현
  - 순차 모드 UI 및 진행 상태 표시 개선
  - 병합된 최종 영상 미리보기 및 다운로드 기능 추가
- 사용자 경험 개선
  - 영상 생성 진행 상황 실시간 표시 기능 강화
  - 다중 클립 생성 및 병합 시 진행률 개별 표시
  - 결과 영상 재생 UI 개선 및 메타데이터 표시 강화

## 다음 할 일
*마지막 업데이트: 2024-05-06*

### 우선 순위 작업
1. 자막 언어 선택 기능 개선
   - 백엔드 API 언어 선택 옵션 확장 (backend/app/routers/youtube.py)
   - 프론트엔드 UI에 언어 선택 컴포넌트 추가 (frontend/src/app/page.tsx)
   - 지원 가능한 모든 언어 코드 목록 추가 (en, ko, ja, zh-CN, fr, de 등)

2. 반복 영상 생성 성능 최적화
   - FFmpeg 명령 최적화 및 처리 성능 개선 (backend/app/services/generator.py)
   - 진행 상태 표시 기능 강화 (frontend/src/app/page.tsx)
   - 백그라운드 작업 시스템 안정성 개선

3. 사용자 인터페이스 개선
   - 다크 모드 지원 추가
   - 모바일 레이아웃 최적화
   - 로딩 상태 표시 개선
   - 자막 검색 및 선택 UI 개선

4. 프론트엔드-백엔드 연동 테스트 및 디버깅
   - API 요청/응답 타입 일관성 보장
   - 에러 처리 및 사용자 피드백 강화
   - 네트워크 지연 및 오류 상황 테스트

5. AI 통합 기능 개선
   - Claude 3.7과 YouTube 통합 UX 개선
   - 자동 번역 및 분석 기능 확장
   - 학습 추천 기능 구현

### 장기 과제
- 데이터베이스 마이그레이션 및 모델 정의
- 컨테이너화 및 배포 환경 구성
- 멀티 환경(Windows/macOS/Linux) 지원 강화
- 사용자 계정 및 학습 진행 추적 기능

## 해결해야 할 이슈
- [ ] 긴 영상에서 자막 추출 시 성능 이슈
- [ ] 특정 YouTube 채널에서 자막 추출 제한 문제
- [ ] 영상 처리 중 메모리 사용량 최적화
- [ ] 프론트엔드-백엔드 API 연동 시 CORS 설정
- [ ] 멀티 환경(Windows/macOS/Linux) 지원 이슈
- [ ] 절대 경로/상대 경로 처리 방식 일관성 확보

## 표준화된 실행 방법

### 서버 실행/종료 (개선된 스크립트 사용)
1. 서버 시작: 프로젝트 루트 디렉토리에서 `./start_servers.sh` 실행
   - 백엔드와 프론트엔드 서버가 동시에 시작됨
   - 필요한 디렉토리, 환경 파일이 자동으로 생성됨
   - 가상환경 및 Node 모듈 자동 확인 및 설치
2. 서버 종료: 프로젝트 루트 디렉토리에서 `./stop_servers.sh` 실행
   - 모든 서버가 안전하게 종료됨
   - quiet 모드 지원: `./stop_servers.sh quiet`

### 백엔드 개별 실행 (기존 방식)
1. 백엔드 디렉토리로 이동: `cd backend`
2. 가상환경 활성화: `source venv/bin/activate` (Windows: `venv\Scripts\activate`)
3. 실행 스크립트 사용: `./run.sh`

### 프론트엔드 개별 실행 (기존 방식)
1. 프론트엔드 디렉토리로 이동: `cd frontend`
2. 의존성 설치 (최초 1회): `npm install`
3. 개발 서버 실행: `npm run dev`

### Docker 실행 (옵션)
전체 애플리케이션 실행: `docker-compose up -d`

### 필수 환경 변수 설정
`.env` 파일은 이제 `start_servers.sh`에 의해 자동으로 생성됩니다. 기본 설정:

```
# 백엔드 설정 (.env)
MEDIA_PATH=data/clips
SUBTITLE_PATH=data/subtitles
TEMP_PATH=data/temp
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000

# 프론트엔드 설정 (.env.local)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```
