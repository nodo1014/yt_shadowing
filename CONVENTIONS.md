# YouTube 쉐도잉 애플리케이션 개발 컨벤션 및 표준

## 프로젝트 구조 표준

```
프로젝트_루트/
├── frontend/                      # Next.js + Tailwind 프론트엔드
│   ├── src/                      # 소스 코드
│   │   ├── app/                 # Next.js 앱 라우트
│   │   ├── components/          # 재사용 컴포넌트
│   │   └── lib/                 # 유틸리티 및 API 클라이언트
│   ├── public/                   # 정적 자산
│   ├── package.json              # 의존성 및 스크립트
│   ├── next.config.ts            # Next.js 설정
│   └── Dockerfile                # 프론트엔드 컨테이너 설정
│
├── backend/                       # FastAPI 백엔드
│   ├── app/                      # 애플리케이션 코드
│   │   ├── __init__.py          # 패키지 초기화
│   │   ├── main.py              # FastAPI 진입점
│   │   ├── config.py            # 설정 및 환경 변수
│   │   ├── db.py                # 데이터베이스 설정
│   │   ├── middleware.py        # 미들웨어 설정
│   │   ├── models/              # Pydantic 모델 및 SQLAlchemy ORM
│   │   ├── routers/             # API 라우터
│   │   ├── services/            # 비즈니스 로직
│   │   ├── core/                # 코어 기능 및 유틸리티
│   │   ├── static/              # 정적 파일
│   │   └── templates/           # 템플릿 파일
│   ├── data/                     # 데이터 저장소
│   │   ├── clips/               # 비디오 클립
│   │   ├── subtitles/           # 자막 파일
│   │   └── temp/                # 임시 파일
│   ├── tests/                    # 테스트 코드
│   ├── venv/                     # Python 가상환경
│   ├── requirements.txt          # Python 의존성
│   ├── Dockerfile                # 백엔드 컨테이너 설정
│   ├── .env                      # 환경 변수 파일
│   └── run.sh                    # 실행 스크립트
│
├── docker-compose.yml             # 전체 프로젝트 컨테이너 구성
├── .gitignore                     # Git 제외 파일
├── README.md                      # 프로젝트 설명서
├── PROGRESS.md                    # 개발 진행 상황
└── CONVENTIONS.md                 # 개발 표준 문서
```

## 코딩 표준

### 파이썬 (백엔드)

1. **임포트 방식**
   - 모든 임포트는 **절대 경로**를 사용
   - 상대 경로 (`..`, `.`) 사용 금지
   - 예시: `from app.core.utils import setup_logger`

2. **모듈 구조**
   - 각 모듈은 명확한 목적을 가져야 함
   - 모든 파일 상단에 docstring 주석 추가
   - 관련 기능은 동일한 모듈에 그룹화

3. **네이밍 컨벤션**
   - 변수/함수: `snake_case`
   - 클래스: `PascalCase`
   - 상수: `UPPER_CASE`
   - 임시 변수는 의미있는 이름 사용 (`i`, `j` 같은 변수명 최소화)

4. **타입 힌트**
   - 모든 함수에 타입 힌트 사용
   - Pydantic 모델 사용 시 타입 명시
   - Optional, Union 등 복합 타입 적절히 사용

5. **모델 정의**
   - 모든 API 요청/응답 모델은 `app/models/` 디렉토리에 정의
   - Pydantic 모델 사용 시 `Field` 데코레이터로 설명 추가
   - 관련 모델은 동일한 파일에 그룹화

6. **에러 처리**
   - 적절한 예외처리 사용
   - 로깅을 통한 에러 추적
   - 사용자에게 명확한 에러 메시지 제공

7. **비동기 패턴**
   - FastAPI 라우트 함수는 `async def` 사용
   - I/O 작업은 비동기 함수 사용
   - 백그라운드 작업은 FastAPI의 `BackgroundTasks` 사용

8. **환경 변수**
   - 설정은 `config.py`에서 중앙 관리
   - `.env` 파일 사용하여 환경 변수 관리
   - 민감한 정보는 환경 변수로 저장하고 소스 코드에 포함하지 않음

### TypeScript (프론트엔드)

1. **컴포넌트 구조**
   - 재사용 가능한 컴포넌트는 `components/` 디렉토리에 정의
   - 컴포넌트 이름은 `PascalCase` 사용
   - 페이지 별 컴포넌트는 해당 페이지 폴더 내 정의

2. **타입 정의**
   - 인터페이스와 타입 명시적 정의
   - Props에 타입 정의 필수
   - `any` 타입 사용 최소화

3. **API 통신**
   - API 엔드포인트는 `/api/` 접두사 사용
   - 응답 타입 명시적 정의
   - API 클라이언트는 `lib/api.ts`에 중앙화하여 관리

4. **스타일링**
   - Tailwind CSS 유틸리티 클래스 우선 사용
   - 일관된 디자인 시스템 적용
   - 컴포넌트 별 스타일 적용 시 모듈 CSS 사용

5. **상태 관리**
   - React Hooks 패턴 사용 (`useState`, `useEffect` 등)
   - 필요한 경우에만 외부 상태 관리 라이브러리 적용
   - 전역 상태와 로컬 상태 구분하여 사용

## 파일명 표준화

- 클립 파일: `{project_name}_clip_{number}.mp4`
- 자막 파일: `{project_name}_subtitle_{number}.srt`
- 번역 파일: `{project_name}_translation_{number}.json`
- 반복 영상: `{project_name}_repeat_{number}.mp4`
- 썸네일: `{project_name}_thumbnail_{number}.jpg`
- 최종 영상: `{project_name}_final_{number}.mp4`

## 로깅 표준

1. **백엔드 로깅**
   - 모든 모듈은 자체 로거 사용
   - 로그 수준 적절히 사용 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - 로그 파일은 모듈명과 일치하게 명명

2. **프론트엔드 로깅**
   - 개발 환경에서 console.log 사용 가능
   - 프로덕션 환경에서는 필요한 경우만 선택적으로 로깅
   - 에러 추적 시스템 연동 (향후 구현)

## 실행 표준

### 백엔드
1. 반드시 가상환경 활성화 후 실행:
   ```bash
   cd backend
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ./run.sh
   ```

### 프론트엔드
1. 의존성 설치 후 개발 서버 실행:
   ```bash
   cd frontend
   npm install  # 최초 1회 또는 의존성 변경 시
   npm run dev
   ```

### Docker 실행 (옵션)
1. 전체 시스템 실행:
   ```bash
   docker-compose up -d
   ```

## 코드 리뷰 및 PR 표준

1. 코드 변경은 Pull Request를 통해 진행
2. 코드 리뷰는 최소 1명 이상의 승인 필요
3. 테스트 코드 작성 권장
4. 커밋 메시지는 명확하고 간결하게 작성 