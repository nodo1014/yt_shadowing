import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    console.log('[API] POST /api/video/download - 요청 시작');
    
    // 요청 본문 파싱
    const body = await request.json();
    console.log('[API] 요청 본문:', body);
    
    // 백엔드 API로 요청 전달 (youtube/download 엔드포인트로 전달)
    const apiUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8001/api'}/youtube/download`;
    console.log(`[API] 백엔드 요청: ${apiUrl}`, '(video/download → youtube/download로 전달)');
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    // 응답 처리
    const data = await response.json();
    console.log('[API] 백엔드 응답:', data);
    
    if (!response.ok) {
      console.error(`[API] 백엔드 오류: ${response.status} - ${response.statusText}`);
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