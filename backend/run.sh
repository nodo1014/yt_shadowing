#!/bin/bash

# 가상환경 활성화
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "가상환경이 활성화되었습니다."
else
    echo "가상환경이 존재하지 않습니다. 생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo "가상환경이 생성되고 의존성이 설치되었습니다."
fi

# 환경 변수 설정
export PYTHONPATH=.

# FastAPI 서버 실행
echo "FastAPI 서버를 시작합니다..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 종료 시 가상환경 비활성화
deactivate 
