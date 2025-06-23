#!/usr/bin/env python3
"""
File: main.py
Description: FastAPI 애플리케이션 진입점
"""

import os
import sys
import traceback

# 디버깅용 코드
try:
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    
    from app.config import settings
    from app.middleware import setup_middlewares
    print("기본 모듈 가져오기 성공")
    
    # 라우터 가져오기 시도
    try:
        from app.routers import youtube, subtitle
        print("라우터 모듈 가져오기 성공")
    except Exception as e:
        print(f"라우터 가져오기 실패: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
except Exception as e:
    print(f"모듈 가져오기 실패: {str(e)}")
    print(traceback.format_exc())
    sys.exit(1)

# 앱 설정
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 정적 파일 마운트 (절대 경로 사용)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 미들웨어 설정
setup_middlewares(app)

# 라우터 등록
app.include_router(youtube.router, prefix="/api/youtube", tags=["youtube"])
app.include_router(subtitle.router, tags=["subtitle"])

# 메인 라우트
@app.get("/api")
async def root():
    """메인 API 경로"""
    return {
        "message": "YouTube 쉐도잉 애플리케이션 API",
        "version": settings.APP_VERSION
    }

# 오류 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리기"""
    error_trace = traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={
            "message": f"내부 서버 오류: {str(exc)}",
            "trace": error_trace if settings.DEBUG else "디버그 모드에서만 표시됩니다."
        }
    )

# 앱 시작 시 실행
@app.on_event("startup")
async def startup():
    """앱 시작 시 실행되는 함수"""
    print(f"=== {settings.APP_NAME} v{settings.APP_VERSION} 시작 ===")
    print(f"API 문서: http://{settings.API_HOST}:{settings.API_PORT}/api/docs")

    # 필요한 디렉토리 생성
    from app.config import ensure_directories
    ensure_directories()

# 앱 종료 시 실행
@app.on_event("shutdown")
async def shutdown():
    """앱 종료 시 실행되는 함수"""
    print(f"=== {settings.APP_NAME} 종료 ===")

# 직접 실행 시
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    ) 