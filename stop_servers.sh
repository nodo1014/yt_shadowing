#!/bin/bash

# 색상 설정
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# quiet 모드 확인
QUIET=0
if [[ "$1" == "quiet" ]]; then
    QUIET=1
fi

# 메시지 출력 함수
print_msg() {
    if [[ $QUIET -eq 0 ]]; then
        echo -e "$1"
    fi
}

# 스크립트 실행 시작 메시지
print_msg "${GREEN}========================================${NC}"
print_msg "${GREEN}영어 쉐도잉 시스템 서버 중지${NC}"
print_msg "${GREEN}========================================${NC}"

# 프로젝트 루트 디렉토리 설정 (스크립트 위치 기준)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# PID 파일에서 프로세스 ID 읽기
BACKEND_PID=""
FRONTEND_PID=""

if [ -f "$PROJECT_ROOT/.backend_pid" ]; then
    BACKEND_PID=$(cat "$PROJECT_ROOT/.backend_pid")
fi

if [ -f "$PROJECT_ROOT/.frontend_pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/.frontend_pid")
fi

# 백엔드 서버 중지
print_msg "${YELLOW}백엔드 서버 중지 중...${NC}"
BACKEND_STOPPED=0

# PID 파일로 프로세스 확인 및 종료 시도
if [[ -n "$BACKEND_PID" ]]; then
    if ps -p $BACKEND_PID > /dev/null; then
        kill $BACKEND_PID
        sleep 2
        if ps -p $BACKEND_PID > /dev/null; then
            print_msg "${YELLOW}정상 종료 실패, 강제 종료 시도...${NC}"
            kill -9 $BACKEND_PID 2>/dev/null
        fi
        BACKEND_STOPPED=1
    fi
fi

# 프로세스 이름으로 추가 확인
if pkill -f "uvicorn app.main:app" > /dev/null 2>&1; then
    BACKEND_STOPPED=1
fi

# 프론트엔드 서버 중지
print_msg "${YELLOW}프론트엔드 서버 중지 중...${NC}"
FRONTEND_STOPPED=0

# PID 파일로 프로세스 확인 및 종료 시도
if [[ -n "$FRONTEND_PID" ]]; then
    if ps -p $FRONTEND_PID > /dev/null; then
        kill $FRONTEND_PID
        sleep 2
        if ps -p $FRONTEND_PID > /dev/null; then
            print_msg "${YELLOW}정상 종료 실패, 강제 종료 시도...${NC}"
            kill -9 $FRONTEND_PID 2>/dev/null
        fi
        FRONTEND_STOPPED=1
    fi
fi

# 프로세스 이름으로 추가 확인
if pkill -f "next dev" > /dev/null 2>&1; then
    FRONTEND_STOPPED=1
fi

# PID 파일 정리
rm -f "$PROJECT_ROOT/.backend_pid" "$PROJECT_ROOT/.frontend_pid"

# 결과 확인
if [ $BACKEND_STOPPED -eq 1 ]; then
    print_msg "${GREEN}백엔드 서버가 성공적으로 중지되었습니다.${NC}"
else
    print_msg "${YELLOW}백엔드 서버가 실행 중이지 않습니다.${NC}"
fi

if [ $FRONTEND_STOPPED -eq 1 ]; then
    print_msg "${GREEN}프론트엔드 서버가 성공적으로 중지되었습니다.${NC}"
else
    print_msg "${YELLOW}프론트엔드 서버가 실행 중이지 않습니다.${NC}"
fi

print_msg "${GREEN}========================================${NC}"
print_msg "${GREEN}모든 서버가 중지되었습니다.${NC}"
print_msg "${GREEN}========================================${NC}"
