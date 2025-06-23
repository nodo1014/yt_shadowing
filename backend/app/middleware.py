#!/usr/bin/env python3
"""
File: middleware.py
Description: FastAPI 애플리케이션의 미들웨어 설정
"""

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings

# 로거 설정
logger = logging.getLogger("middleware")

async def logging_middleware(request: Request, call_next):
    """요청/응답 로깅 미들웨어"""
    start_time = time.time()
    
    # 요청 로깅
    logger.info(f"요청: {request.method} {request.url.path}")
    
    # 요청 처리
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 응답 로깅
        logger.info(f"응답: {request.method} {request.url.path} - 상태 코드: {response.status_code}, 처리 시간: {process_time:.3f}초")
        
        # 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"오류 발생: {request.method} {request.url.path} - {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"message": "내부 서버 오류가 발생했습니다"}
        )

async def error_handler_middleware(request: Request, call_next):
    """전역 예외 처리 미들웨어"""
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception(f"처리되지 않은 예외: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"내부 서버 오류: {str(e)}"}
        )

def setup_middlewares(app: FastAPI):
    """미들웨어 설정"""
    
    # CORS 미들웨어
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 사용자 정의 미들웨어
    app.middleware("http")(logging_middleware)
    app.middleware("http")(error_handler_middleware) 