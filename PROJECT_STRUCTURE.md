# YouTube 쉐도잉 애플리케이션 프로젝트 구조

이 문서는 YouTube 쉐도잉 애플리케이션의 전체 프로젝트 구조와 각 디렉토리 및 주요 파일의 역할을 설명합니다.

## 전체 구조

```
.
├── backend/                # 백엔드 코드
│   ├── app/                # FastAPI 앱 및 API 라우트
│   │   ├── main.py         # FastAPI 엔트리 포인트
│   │   ├── models/         # DB 모델
│   │   ├── routers/        # API 엔드포인트
│   │   ├── services/       # 핵심 비즈니스 로직 서비스
│   │   │   ├── extractor.py # 비디오 추출 서비스
│   │   │   ├── subtitle.py # 자막 처리 서비스
│   │   │   ├── generator.py # 클립 생성 서비스
│   │   │   ├── pronunciation.py # 발음 분석 서비스
│   │   │   ├── whisper_generator.py # Whisper 자막 생성 서비스
│   │   ├── common/         # 공통 유틸리티 및 헬퍼 함수
│   │   ├── static/         # 정적 파일
│   │   ├── templates/      # 템플릿 파일
│   │   ├── config.py       # 환경 변수 설정
│   │   ├── middleware.py   # 미들웨어
│   │   ├── db.py           # 데이터베이스 설정
│   ├── data/               # 저장된 파일
│   │   ├── clips/          # 다운로드된 영상 파일
│   │   ├── subtitles/      # 자막 파일
│   │   ├── temp/           # 임시 파일
│   │   ├── logs/           # 로그 파일
│   ├── tests/              # 테스트 코드
│   ├── requirements.txt    # Python 패키지 목록
│   ├── run.sh              # 실행 스크립트
│   ├── .env                # 환경 변수 파일
├── frontend/               # Next.js 프론트엔드
│   ├── public/             # 정적 파일
│   ├── src/                # 소스 코드
│   │   ├── app/            # Next.js 앱 라우트
│   │   │   ├── api/        # 클라이언트 API 라우트
│   │   │   │   ├── mcp-youtube-transcript/ # Claude 3.7용 MCP 플러그인
│   │   │   ├── youtube/    # YouTube 페이지
│   │   │   ├── videos/     # 비디오 관리 페이지
│   │   │   ├── subtitles/  # 자막 관리 페이지
│   │   │   ├── generator/  # 반복 영상 생성 페이지
│   │   │   ├── thumbnails/ # 썸네일 생성 페이지
│   │   │   ├── dashboard/  # 대시보드 페이지
│   ├── .env.local          # 환경 변수 파일
│   ├── tailwind.config.js  # Tailwind CSS 설정
│   ├── next.config.js      # Next.js 설정
│   ├── package.json        # npm 패키지 목록
├── docs/                   # 프로젝트 문서
│   ├── claude_youtube_integration.md # Claude 3.7 통합 가이드
├── start_servers.sh        # 서버 시작 스크립트
├── stop_servers.sh         # 서버 중지 스크립트
├── README.md               # 프로젝트 설명서
├── PROGRESS.md             # 개발 진행 상황
├── CONVENTIONS.md          # 개발 표준 및 컨벤션
├── PROJECT_STRUCTURE.md    # 프로젝트 구조 설명 (이 파일)
├── docker-compose.yml      # Docker 구성 파일
```

## 주요 구성 요소 설명

### 백엔드 (backend/)

백엔드는 FastAPI 기반의 RESTful API 서버로, 다음과 같은 핵심 기능을 제공합니다:

1. **`app/main.py`**: FastAPI 앱 인스턴스 생성 및 초기화
2. **`app/routers/`**: API 엔드포인트 정의
   - `youtube.py`: YouTube 영상 다운로드 및 처리 관련 API
   - `subtitle.py`: 자막 관리 관련 API
3. **`app/services/`**: 비즈니스 로직 구현
   - `extractor.py`: YouTube 영상 다운로드 및 정보 추출
   - `subtitle.py`: 자막 처리 및 관리
   - `generator.py`: 반복 영상 및 썸네일 생성
   - `pronunciation.py`: 발음 분석
   - `whisper_generator.py`: OpenAI Whisper 기반 자동 자막 생성
4. **`app/config.py`**: 앱 설정 및 환경 변수 관리
5. **`app/middleware.py`**: CORS 및 예외 처리 미들웨어
6. **`data/`**: 저장된 파일 관리

### 프론트엔드 (frontend/)

프론트엔드는 Next.js와 TypeScript 기반의 웹 애플리케이션으로, 다음과 같은 핵심 페이지를 제공합니다:

1. **`src/app/page.tsx`**: 홈페이지
2. **`src/app/youtube/`**: YouTube 영상 다운로드 페이지
3. **`src/app/videos/`**: 다운로드된 영상 관리 페이지
4. **`src/app/subtitles/`**: 자막 관리 페이지
5. **`src/app/generator/`**: 반복 영상 생성 페이지
6. **`src/app/thumbnails/`**: 썸네일 생성 페이지
7. **`src/app/api/mcp-youtube-transcript/`**: Claude 3.7용 YouTube 트랜스크립트 MCP 플러그인

### 유틸리티 스크립트

1. **`start_servers.sh`**: 백엔드와 프론트엔드 서버를 모두 시작하는 통합 스크립트
2. **`stop_servers.sh`**: 실행 중인 서버를 중지하는 스크립트
3. **`backend/run.sh`**: 백엔드 서버만 단독으로 실행하는 스크립트

### 문서

1. **`README.md`**: 프로젝트 개요 및 설치/실행 방법
2. **`PROGRESS.md`**: 개발 진행 상황 및 업데이트 내역
3. **`CONVENTIONS.md`**: 개발 표준 및 컨벤션
4. **`docs/claude_youtube_integration.md`**: Claude 3.7과 YouTube 트랜스크립트 통합 가이드

## 주요 데이터 흐름

1. 사용자가 YouTube URL을 입력
2. 백엔드에서 `extractor.py`를 통해 영상 다운로드
3. `subtitle.py`를 통해 자막 추출 및 처리
4. 필요시 `whisper_generator.py`로 자동 자막 생성
5. 사용자가 특정 자막 구간 선택
6. `generator.py`를 통해 반복 영상 생성
7. 생성된 영상 및 자막을 `data/` 디렉토리에 저장

## 개발 환경 설정

1. **백엔드**: Python 3.9+ 및 FastAPI
2. **프론트엔드**: Node.js 18+ 및 Next.js
3. **필수 도구**: FFmpeg (영상 처리용)

## 설계 원칙

1. **모듈화**: 기능별로 독립된 모듈로 분리
2. **계층화**: 라우터-서비스-모델 패턴 준수
3. **재사용성**: 공통 기능은 유틸리티로 분리
4. **확장성**: 새로운 기능 추가가 용이한 구조
5. **타입 안전성**: TypeScript와 Python 타입 힌팅 활용
