#!/usr/bin/env python3
"""
File: db.py
Description: 데이터베이스 설정 및 모델 정의
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

from app.config import get_project_root

# 데이터베이스 경로 설정
DB_PATH = get_project_root() / "backend" / "data" / "shadowing.db"
DB_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 기본 클래스
Base = declarative_base()

# 데이터베이스 세션 의존성
def get_db():
    """DB 세션 제공"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 테이블 생성
def create_tables():
    """DB 테이블 생성"""
    # 데이터베이스 파일이 위치할 디렉토리 생성
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    print(f"데이터베이스 테이블이 생성되었습니다: {DB_PATH}")

# 앱 시작 시 테이블 확인
if __name__ == "__main__":
    create_tables() 