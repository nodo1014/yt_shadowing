# YouTube 쉐도잉 애플리케이션

영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구입니다. YouTube 영상을 다운로드하고, 자막을 추출하여, 선택한 문장을 반복적으로 연습할 수 있는 맞춤형 영상을 생성합니다.

## 진행 상황

- 최신 진행상황 및 작업 내역은 [PROGRESS.md](PROGRESS.md) 파일을 참고하세요.
- 개발 표준 및 컨벤션은 [CONVENTIONS.md](CONVENTIONS.md) 파일을 참고하세요.

## 주요 기능

- **영상 관리**: YouTube 영상 다운로드 및 관리
- **자막 관리**: 자막 추출, 검색, 번역 관리
- **YouTube 트랜스크립트**: YouTube 영상의 자막을 가져와 텍스트로 추출
- **반복 영상 생성**: 선택한 자막 구간을 반복하는 학습용 영상 생성
- **썸네일 생성**: 학습 영상을 위한 맞춤형 썸네일 생성
- **AI 통합**: Claude 3.7과 연동을 통한 자막 분석 및 처리 자동화
- **인용문 검색 개선**: 문장 앞뒤 따옴표, 구두점 등 자동 제거 후 검색 진행
- **순차적 영상 생성**: 여러 문장 선택 후 각각 개별 반복 영상 생성 및 하나로 병합

## 새로운 기능

### Claude 3.7 통합

이제 YouTube 쉐도잉 애플리케이션은 Claude 3.7과 통합되어 다음과 같은 향상된 기능을 제공합니다:

- **자동 자막 분석**: AI 어시스턴트가 YouTube 자막을 직접 분석하여 중요 정보 추출
- **맞춤형 학습 자료 생성**: 사용자 질문에 기반한 맞춤형 학습 내용 제공
- **다국어 자막 지원**: 영어, 한국어 등 다양한 언어 자막의 실시간 처리
- **단락 구성 최적화**: 자연스러운 문단 구성으로 가독성 향상

### 특수문자 제거 검색
입력창에 복사/붙여넣기 또는 직접 작성한 문장에서 따옴표(", '), 쉼표, 느낌표 등 구두점을 자동으로 제거하여 검색합니다. 이를 통해 원문 그대로 복사한 인용문도 정확히 검색할 수 있습니다.

### 순차적 영상 생성
검색 결과에서 여러 문장을 선택한 후 "순차적 개별 영상 생성 모드"를 활성화하면 각 문장마다 개별 반복 영상을 생성한 후 이를 순차적으로 병합하여 하나의 최종 영상으로 만들 수 있습니다. 이 기능을 통해 자연스러운 순서로 여러 문장을 연습할 수 있는 학습 영상을 쉽게 생성할 수 있습니다.

Claude 3.7 통합을 사용하려면 프론트엔드와 백엔드가 모두 실행되어야 합니다. 간편하게 서버를 시작하려면 다음 명령을 사용하세요:

```bash
# 서버 시작
./start_servers.sh

# 서버 중지
./stop_servers.sh
```

자세한 사용 방법은 [Claude YouTube 통합 가이드](docs/claude_youtube_integration.md)를 참고하세요.

## 기술 스택

- **프론트엔드**: Next.js, TypeScript, Tailwind CSS
- **백엔드**: FastAPI, Python
- **데이터 처리**: MoviePy, yt-dlp, YouTube Transcript API

## 설치 및 실행 방법

## AI 패턴 실수 방지: 실시간 점검용 체크리스트
	•	임포트하려는 클래스/함수가 실제 정의되어 있는지 파일 내에서 확인했는가?
	•	상대경로 임포트 시, PYTHONPATH 설정을 고려한 app. 기준 경로로 작성했는가?
	•	새로 정의된 클래스나 함수가 있다면, 해당 모듈의 __init__.py 또는 main에서 import 되어 있는가?
	•	파일 이름만 존재하고 클래스/함수가 없는 상태에서 import 시도한 건 아닌가?
	•	모듈 경로 수정/이동 후, AI가 참조하는 경로를 정확히 반영했는가?

이 체크리스트는 FastAPI, Next.js 백엔드 연동 프로젝트에서 자주 반복되는 실수를 줄이기 위해 도입되었음.

### 사전 요구사항

- Python 3.9+ 
- Node.js 18+
- FFmpeg

### 백엔드 설정

1. 백엔드 디렉토리로 이동:
   ```bash
   cd backend
   ```

2. 실행 스크립트를 통해 자동 가상환경 설정 및 서버 실행:
   ```bash
   ./run.sh
   ```
   
   또는 수동으로 가상 환경 생성 및 활성화:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. FastAPI 서버가 http://localhost:8000에서 실행됩니다. 
   API 문서는 http://localhost:8000/api/docs 에서 확인할 수 있습니다.

### 프론트엔드 설정

1. 의존성 설치:
   ```bash
   cd frontend
   npm install
   ```

2. 개발 서버 실행:
   ```bash
   npm run dev
   ```

3. 프론트엔드 서버가 http://localhost:3000에서 실행됩니다.

## 사용 방법

1. 브라우저에서 `http://localhost:3000`로 접속하여 애플리케이션 홈페이지를 엽니다.
2. **영상 관리** 페이지에서 YouTube URL을 입력하여 영상을 다운로드합니다.
3. **자막 관리** 페이지에서 다운로드한 영상의 자막을 확인하고 번역을 추가할 수 있습니다.
4. **반복 영상 생성** 페이지에서 원하는 자막 구간을 선택하고 반복 영상을 생성합니다.
5. **YouTube 트랜스크립트** 페이지에서 YouTube URL을 입력하여 빠르게 영상의 자막을 추출할 수 있습니다.
6. **썸네일 생성** 페이지에서 생성된 학습 영상을 위한 맞춤형 썸네일을 생성합니다.

## 프로젝트 구조

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
│   │   ├── common/         # 공통 유틸리티 및 헬퍼 함수
│   │   ├── static/         # 정적 파일
│   │   ├── templates/      # 템플릿 파일
│   │   ├── config.py       # 환경 변수 설정
│   │   ├── middleware.py   # 미들웨어
│   │   ├── db.py           # 데이터베이스 설정
│   ├── data/               # 저장된 파일
│   ├── tests/              # 테스트 코드
│   ├── requirements.txt    # Python 패키지 목록
│   ├── run.sh              # 실행 스크립트
├── frontend/               # Next.js 프론트엔드
│   ├── public/             # 정적 파일
│   └── src/                # 소스 코드
│       └── app/            # Next.js 앱 라우트
└── docs/                   # 프로젝트 문서
```

## 기여 방법

1. 이 저장소를 포크합니다.
2. 새 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 변경 사항을 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다.

## 라이선스

MIT 라이선스에 따라 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

# 🧠 AI 개발 지시서: Next.js + FastAPI 프로젝트

이 프로젝트는 프론트엔드(Next.js)와 백엔드(FastAPI)를 분리된 디렉토리 구조로 구성한 전형적인 풀스택 웹 애플리케이션입니다.

---

## 📁 프로젝트 구조 (반드시 다음과 같은 표준 구조를 준수한다.)

```
nextjs-fastapi-project/
│── backend/                # FastAPI 백엔드
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI 엔트리 포인트
│   │   ├── models/         # DB 모델
│   │   ├── routers/        # API 엔드포인트
│   │   ├── services/       # 비즈니스 로직
│   │   ├── config.py       # 환경 변수 설정
│   │   ├── db.py           # 데이터베이스 설정
│   │   ├── middleware.py   # 미들웨어
│   ├── tests/              # FastAPI 테스트 코드
│   ├── requirements.txt    # Python 패키지 목록
│   ├── Dockerfile          # 백엔드 컨테이너 설정
│   ├── .env                # 환경 변수 설정 파일
│── frontend/               # Next.js 프론트엔드
│   ├── public/             # 정적 파일 (이미지, 폰트 등)
│   ├── src/                # Next.js 소스코드
│   │   ├── components/     # UI 컴포넌트
│   │   ├── pages/          # Next.js 페이지
│   │   ├── styles/         # TailwindCSS 및 글로벌 스타일링
│   │   ├── utils/          # 유틸리티 함수
│   │   ├── services/       # API 요청 관리
│   ├── tailwind.config.js  # TailwindCSS 설정
│   ├── postcss.config.js   # PostCSS 설정
│   ├── package.json        # npm 패키지 목록
│   ├── next.config.js      # Next.js 설정
│   ├── tsconfig.json       # TypeScript 설정 (선택 사항)
│── docker-compose.yml      # 전체 프로젝트 컨테이너 구성
│── README.md               # 프로젝트 설명서

```

---

## 🔧 개발 환경 기본 규칙

### ✅ Python

* 반드시 **Python 3.10** 가상환경에서 실행할 것
* `backend/venv` 또는 `.venv` 등 명시된 경로에 가상환경 생성

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

* 사용 모듈은 FastAPI, uvicorn, pydantic, aiofiles 등 포함되어야 하며, 실제 사용 모듈은 다음 명령으로 확인:

```bash
pip list
```

---

## 🔗 프론트-백 연결 방식

* 모든 프론트 요청은 `/api/*` 형식으로 이루어지며,
* Next.js에서 이를 FastAPI로 프록시 처리합니다.

```js
// frontend/next.config.js
rewrites: async () => [
  {
    source: '/api/:path*',
    destination: 'http://localhost:8000/api/:path*',
  },
]
```

---

## 🧩 AI 개발 시 지켜야 할 규칙

### ✅ 공통

* 모든 import 경로는 **절대경로 기준**으로 작성합니다.
* 상대경로 (`..`, `.` 등)는 사용하지 않습니다.

### ✅ 프론트엔드 (Next.js + Tailwind CSS)

* `pages/` 디렉토리 기준으로 페이지를 작성합니다.
* fetch 요청은 항상 `/api/xxx` 경로로 작성합니다.
* CSS는 Tailwind 유틸리티 클래스를 기본으로 사용하며, 커스텀 스타일은 최소화합니다.
* 상태 관리는 React useState / useEffect 조합으로 처리하고, 필수일 경우에만 외부 라이브러리 사용
* JavaScript 사용 시 ES6+ 문법 사용 권장하며, 가급적 TypeScript로 작성

```ts
// 예시
fetch('/api/videos', {
  method: 'POST',
  body: ...
})
```

### ✅ 백엔드 (FastAPI)

* FastAPI의 `app` 객체는 `backend/app/main.py`에 있습니다.
* Uvicorn 실행은 다음과 같이 설정합니다:

```bash
cd backend
PYTHONPATH=app uvicorn main:app --reload --port 8000
```

* API 라우터는 `api/` 폴더에 작성하고, `main.py`에서 `include_router()`로 등록합니다.
* import 는 모두 `backend/app` 경로 기준으로 작성

```python
from api.videos import router  # ✅ 권장
```

---

## ✅ 이 지시서를 기반으로만 개발을 진행하세요.

AI 모델은 위 디렉토리와 경로 기준을 정확히 따라야 하며,
프론트/백 구분 없이 모든 모듈은 **일관된 경로 체계와 스타일 가이드**를 사용해야 합니다.

## 파일명 규칙

표준화된 파일명 규칙을 사용하여 프로젝트의 일관성을 유지합니다:

- 클립 파일: `{project_name}_clip_{number}.mp4`
- 자막 파일: `{project_name}_subtitle_{number}.srt`
- 번역 파일: `{project_name}_translation_{number}.json`
- 반복 영상: `{project_name}_repeat_{number}.mp4`
- 썸네일: `{project_name}_thumbnail_{number}.jpg`
- 최종 영상: `{project_name}_final_{number}.mp4`

예시: `avengers_clip_1.mp4`, `avengers_subtitle_1.srt`, `avengers_repeat_1.mp4`

## 변경 사유

기존 프로젝트 구조에서 다음과 같은 문제가 있어 Next.js + FastAPI 구조로 변경했습니다:

1. **모듈 임포트 문제**: Python 모듈 경로 참조 이슈로 인한 백엔드 실행 오류
2. **비표준적 구조**: 표준적이지 않은 디렉토리 구조로 인한 혼란
3. **개발 효율성**: 프론트엔드 개발을 위한 현대적인 도구 부재
4. **확장성**: 기능 확장 및 유지보수의 어려움

Next.js + FastAPI 구조는 다음과 같은 이점을 제공합니다:
- 명확한 프론트엔드/백엔드 분리
- 표준화된 디렉토리 구조
- 현대적인 개발 경험 (핫 리로딩, 타입 체크 등)
- 더 나은 확장성과 유지보수성
