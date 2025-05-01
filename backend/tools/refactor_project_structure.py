#!/usr/bin/env python3
"""
프로젝트 구조 리팩토링 스크립트
프론트엔드와 백엔드 구조를 명확히 분리하고 코드를 재배치합니다.
"""

import os
import shutil
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("refactor")

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))

# 새 디렉토리 구조
NEW_DIRS = [
    # 백엔드 디렉토리
    "backend",
    "backend/api",
    "backend/api/routes",
    "backend/core",
    "backend/data",
    "backend/data/clips",
    "backend/data/output",
    "backend/data/subtitles",
    "backend/data/translations",
    "backend/data/thumbnails",
    "backend/data/final",
    "backend/tests",
    
    # 프론트엔드 디렉토리
    "frontend",
    "frontend/public",
    "frontend/public/assets",
    "frontend/public/assets/images",
    "frontend/public/assets/icons",
    "frontend/src",
    "frontend/src/components",
    "frontend/src/scripts",
    "frontend/src/styles",
    
    # 공통 디렉토리
    "config",
    "docs",
    "scripts"
]

# 코드 이동 맵핑 (소스 경로 -> 대상 경로)
FILE_MOVES = {
    # 코어 모듈 이동
    "yt_shadowing/core/utils.py": "backend/core/utils.py",
    "yt_shadowing/core/subtitle.py": "backend/core/subtitle.py",
    "yt_shadowing/core/extractor.py": "backend/core/extractor.py",
    "yt_shadowing/core/generator.py": "backend/core/generator.py",
    
    # API 라우트 이동
    "yt_shadowing/web/routes/subtitle_routes.py": "backend/api/routes/subtitle_routes.py",
    "yt_shadowing/web/routes/video_routes.py": "backend/api/routes/video_routes.py",
    "yt_shadowing/web/routes/thumbnail_routes.py": "backend/api/routes/thumbnail_routes.py",
    
    # 메인 앱 이동
    "yt_shadowing/web/app.py": "backend/api/app.py",

    # 프론트엔드 이동
    "yt_shadowing/frontend/src/index.html": "frontend/src/index.html",
    "yt_shadowing/frontend/src/scripts/app.js": "frontend/src/scripts/app.js",
    "yt_shadowing/frontend/src/styles/style.css": "frontend/src/styles/style.css",
    
    # 구성 파일 이동
    "config.yaml": "config/config.yaml",
    "requirements.txt": "requirements.txt",
    "PROGRESS.md": "docs/PROGRESS.md",
    "README.md": "README.md"
}

def create_directory_structure():
    """새로운 디렉토리 구조 생성"""
    logger.info("새 디렉토리 구조 생성 중...")
    
    for dir_path in NEW_DIRS:
        full_path = PROJECT_ROOT / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True)
            logger.info(f"디렉토리 생성됨: {dir_path}")
        else:
            logger.info(f"디렉토리 이미 존재함: {dir_path}")
    
    logger.info("디렉토리 구조 생성 완료")

def move_files():
    """파일 이동"""
    logger.info("파일 이동 중...")
    
    for src_path, dst_path in FILE_MOVES.items():
        src_full = PROJECT_ROOT / src_path
        dst_full = PROJECT_ROOT / dst_path
        
        # 소스 파일이 존재하는지 확인
        if src_full.exists():
            # 대상 디렉토리가 존재하는지 확인
            dst_dir = dst_full.parent
            if not dst_dir.exists():
                dst_dir.mkdir(parents=True)
            
            # 파일 복사
            try:
                shutil.copy2(src_full, dst_full)
                logger.info(f"파일 복사됨: {src_path} -> {dst_path}")
            except Exception as e:
                logger.error(f"파일 복사 오류 ({src_path} -> {dst_path}): {str(e)}")
        else:
            logger.warning(f"소스 파일이 존재하지 않음: {src_path}")
    
    logger.info("파일 이동 완료")

def create_init_files():
    """필요한 __init__.py 파일 생성"""
    logger.info("__init__.py 파일 생성 중...")
    
    init_dirs = [
        "backend",
        "backend/api",
        "backend/api/routes",
        "backend/core",
        "backend/tests"
    ]
    
    for dir_path in init_dirs:
        init_file = PROJECT_ROOT / dir_path / "__init__.py"
        if not init_file.exists():
            with open(init_file, "w") as f:
                pass
            logger.info(f"__init__.py 파일 생성됨: {dir_path}/__init__.py")
    
    logger.info("__init__.py 파일 생성 완료")

def create_basic_readme():
    """기본 README.md 파일 생성"""
    readme_path = PROJECT_ROOT / "README.md"
    
    if not readme_path.exists():
        logger.info("기본 README.md 파일 생성 중...")
        
        readme_content = """# 영어 쉐도잉 자동화 시스템

영어 쉐도잉 자동화 시스템은 YouTube 영상을 활용하여 효과적인 영어 학습 자료를 만드는 도구입니다.

## 주요 기능

- YouTube 영상에서 원하는 구간 추출
- 반복 학습을 위한 영상 생성
- 자막 추출 및 번역
- 썸네일 자동 생성
- 최종 영상 병합 및 편집

## 시작하기

### 백엔드

```bash
cd backend
pip install -r requirements.txt
python api/app.py
```

### 프론트엔드

```bash
cd frontend
# 웹 서버로 제공하거나 직접 index.html 실행
```

## 프로젝트 구조

- `backend/`: 백엔드 API 및 코어 로직
- `frontend/`: 사용자 인터페이스
- `config/`: 구성 파일
- `docs/`: 문서

## 라이센스

개인 학습 목적으로만 사용하세요.
"""
        
        with open(readme_path, "w") as f:
            f.write(readme_content)
        
        logger.info("기본 README.md 파일 생성 완료")

def create_updated_requirements():
    """업데이트된 requirements.txt 생성"""
    req_path = PROJECT_ROOT / "requirements.txt"
    
    if req_path.exists():
        with open(req_path, "r") as f:
            current_requirements = f.read()
    else:
        current_requirements = ""
    
    # 필요한 패키지 목록
    required_packages = [
        "fastapi>=0.75.0",
        "uvicorn>=0.17.6",
        "python-multipart>=0.0.5",
        "aiofiles>=0.8.0",
        "pysrt>=1.1.2",
        "pyyaml>=6.0",
        "pillow>=9.1.0",
        "edge-tts>=6.0.0",
        "jinja2>=3.1.1",
    ]
    
    # 기존 패키지 목록에 없는 패키지 추가
    for package in required_packages:
        package_name = package.split(">=")[0]
        if package_name not in current_requirements:
            current_requirements += f"\n{package}"
    
    with open(req_path, "w") as f:
        f.write(current_requirements)
    
    logger.info("requirements.txt 업데이트 완료")

def main():
    """리팩토링 스크립트 메인 함수"""
    logger.info("프로젝트 구조 리팩토링 시작")
    
    create_directory_structure()
    move_files()
    create_init_files()
    create_basic_readme()
    create_updated_requirements()
    
    logger.info("리팩토링 완료!")
    logger.info("다음 단계: 임포트 경로 및 코드 충돌 수정이 필요합니다.")

if __name__ == "__main__":
    main()