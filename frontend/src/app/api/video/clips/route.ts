import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    console.log('[API] GET /api/video/clips - 요청 시작');
    
    // 백엔드 API로 요청 전달
    const apiUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8001/api'}/youtube/clips`;
    console.log(`[API] 백엔드 요청: ${apiUrl}`);
    
    // 가상 데이터로 응답 (실제 백엔드 구현 전까지)
    // 실제로는 백엔드 API 호출 결과를 반환해야 함
    return NextResponse.json({
      status: 'success',
      clips: [
        {
          id: '1',
          name: '샘플 영상 1.mp4',
          path: '/data/clips/sample1.mp4',
          size: 15728640, // 15MB
          modified: Date.now() / 1000 - 86400 // 하루 전
        },
        {
          id: '2',
          name: '샘플 영상 2.mp4',
          path: '/data/clips/sample2.mp4',
          size: 52428800, // 50MB
          modified: Date.now() / 1000 - 3600 // 1시간 전
        }
      ]
    });
    
  } catch (error) {
    console.error('[API] 오류 발생:', error);
    return NextResponse.json(
      { status: 'error', message: '서버 내부 오류가 발생했습니다.' },
      { status: 500 }
    );
  }
} 