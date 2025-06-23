import { NextRequest, NextResponse } from 'next/server';
import { GetTranscriptsParams, GetTranscriptsResponse } from './interface';

/**
 * YouTube 트랜스크립트 MCP 도구 핸들러
 * 
 * @param req Next.js API 요청 객체
 * @param params 요청 매개변수
 * @returns 응답 객체
 */
export async function get_transcripts(
  req: NextRequest,
  params: GetTranscriptsParams
): Promise<GetTranscriptsResponse> {
  try {
    // 필수 매개변수 검증
    if (!params.url) {
      return {
        status: 'error',
        message: 'YouTube URL이 필요합니다.'
      };
    }

    // API 라우트로 요청 전달
    const response = await fetch(`${req.nextUrl.origin}/api/mcp-youtube-transcript`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: params.url,
        lang: params.lang,
        enableParagraphs: params.enableParagraphs || false
      }),
    });

    // 응답 처리
    const data = await response.json();
    return data as GetTranscriptsResponse;
  } catch (error) {
    console.error('YouTube 트랜스크립트 처리 오류:', error);
    return {
      status: 'error',
      message: '트랜스크립트 처리 중 오류가 발생했습니다.'
    };
  }
} 