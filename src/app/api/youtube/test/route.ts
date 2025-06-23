import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    console.log('[API] GET /api/youtube/test - 요청 시작');
    
    // 백엔드 API로 요청 전달
    const apiUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8001/api'}/youtube/test`;
    console.log(`[API] 백엔드 요청: ${apiUrl}`);
    
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 0 } // 캐시 비활성화
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