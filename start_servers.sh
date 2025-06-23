#!/bin/bash

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 스크립트 실행 시작 메시지
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}영어 쉐도잉 시스템 서버 시작${NC}"
echo -e "${GREEN}========================================${NC}"

# 프로젝트 루트 디렉토리 설정 (스크립트 위치 기준)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"
echo -e "${YELLOW}프로젝트 루트 디렉토리: $PROJECT_ROOT${NC}"

# 로그 디렉토리 확인 및 생성
LOG_DIR="$PROJECT_ROOT/logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo -e "${YELLOW}로그 디렉토리를 생성했습니다: $LOG_DIR${NC}"
fi

# 로그 파일 경로 설정
BACKEND_LOG="$LOG_DIR/backend_server.log"
FRONTEND_LOG="$LOG_DIR/frontend_server.log"

# 로그 파일 초기화
> "$BACKEND_LOG"
> "$FRONTEND_LOG"
echo -e "${YELLOW}로그 파일을 초기화했습니다.${NC}"

# 실행 중인 서버 중지
echo -e "${YELLOW}기존 서버 프로세스 정리 중...${NC}"
bash "$PROJECT_ROOT/stop_servers.sh" quiet
echo -e "${YELLOW}기존 서버 프로세스 정리 완료${NC}"

# 백엔드 환경 확인 및 서버 시작
echo -e "${YELLOW}백엔드 서버 시작 준비 중...${NC}"
cd "$PROJECT_ROOT/backend"

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo -e "${RED}가상환경이 존재하지 않습니다. 설치를 시작합니다...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}가상환경 설정에 실패했습니다.${NC}"
        exit 1
    fi
    echo -e "${GREEN}가상환경 설치 및 패키지 설치 완료${NC}"
fi

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}백엔드 .env 파일이 없습니다. 기본 설정으로 생성합니다.${NC}"
    cat > ".env" << EOF
MEDIA_PATH=data/clips
SUBTITLE_PATH=data/subtitles
TEMP_PATH=data/temp
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
EOF
    echo -e "${GREEN}.env 파일 생성 완료${NC}"
fi

# 필요한 디렉토리 확인 및 생성
DIRS=("data" "data/clips" "data/clips/thumbnails" "data/subtitles" "data/temp")
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "${YELLOW}디렉토리 생성: $dir${NC}"
    fi
done

# 백엔드 서버 시작
echo -e "${YELLOW}백엔드 서버 시작 중...${NC}"
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# 백엔드 서버 시작 확인
sleep 3
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}백엔드 서버가 성공적으로 시작되었습니다. (PID: $BACKEND_PID)${NC}"
    echo -e "${YELLOW}백엔드 로그: $BACKEND_LOG${NC}"
else
    echo -e "${RED}백엔드 서버 시작 실패. 로그를 확인하세요: $BACKEND_LOG${NC}"
    exit 1
fi

# 프론트엔드 환경 확인 및 서버 시작
echo -e "${YELLOW}프론트엔드 서버 시작 준비 중...${NC}"
cd "$PROJECT_ROOT/frontend"

# Node 모듈 확인
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Node 모듈이 설치되어 있지 않습니다. npm install을 실행합니다...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}Node 모듈 설치에 실패했습니다.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Node 모듈 설치 완료${NC}"
fi

# .env.local 파일 확인
if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}프론트엔드 .env.local 파일이 없습니다. 기본 설정으로 생성합니다.${NC}"
    cat > ".env.local" << EOF
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
EOF
    echo -e "${GREEN}.env.local 파일 생성 완료${NC}"
fi

# 프론트엔드 서버 시작
echo -e "${YELLOW}프론트엔드 서버 시작 중...${NC}"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# 프론트엔드 서버 시작 확인
sleep 3
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}프론트엔드 서버가 성공적으로 시작되었습니다. (PID: $FRONTEND_PID)${NC}"
    echo -e "${YELLOW}프론트엔드 로그: $FRONTEND_LOG${NC}"
else
    echo -e "${RED}프론트엔드 서버 시작 실패. 로그를 확인하세요: $FRONTEND_LOG${NC}"
    echo -e "${YELLOW}백엔드 서버도 종료합니다...${NC}"
    kill $BACKEND_PID
    exit 1
fi

# PID 파일 저장
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend_pid"
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend_pid"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}모든 서버가 성공적으로 시작되었습니다.${NC}"
echo -e "${GREEN}백엔드 API: http://localhost:8000/api/docs${NC}"
echo -e "${GREEN}프론트엔드: http://localhost:3000${NC}"
echo -e "${GREEN}서버를 중지하려면 './stop_servers.sh'를 실행하세요.${NC}"
echo -e "${GREEN}========================================${NC}"
