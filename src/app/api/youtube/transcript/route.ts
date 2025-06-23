import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    console.log('[API] POST /api/youtube/transcript - 요청 시작');
    
    // 요청 본문 파싱
    const body = await request.json();
    console.log('[API] 요청 본문:', body);
    
    // 필수 파라미터 확인
    if (!body.url) {
      console.error('[API] 오류: URL 파라미터 누락');
      return NextResponse.json(
        { status: 'error', message: 'URL이 필요합니다' },
        { status: 400 }
      );
    }
    
    // 백엔드 API로 요청 전달
    const apiUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8001/api'}/youtube/transcript`;
    console.log(`[API] 백엔드 요청: ${apiUrl}`);
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    // 응답 처리
    const data = await response.json();
    console.log('[API] 백엔드 응답 상태:', response.status);
    
    if (!response.ok) {
      console.error(`[API] 백엔드 오류: ${response.status} - ${response.statusText}`);
      console.error('[API] 오류 응답:', data);
      return NextResponse.json(data, { status: response.status });
    }
    
    console.log('[API] 요청 성공 처리 완료');
    return NextResponse.json(data);
  } catch (error) {
    console.error('[API] 오류 발생:', error);
    return NextResponse.json(
      { status: 'error', message: '서버 내부 오류가 발생했습니다.' },
      { status: 500 }
    );
  }
} 