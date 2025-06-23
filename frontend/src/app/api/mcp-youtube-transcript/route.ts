import { NextRequest, NextResponse } from 'next/server';
import { TranscriptItem, GetTranscriptsResponse } from './interface';

/**
 * API 라우트 핸들러: YouTube 트랜스크립트 추출
 * 
 * @param req - Next.js API 요청 객체
 * @returns NextResponse 객체
 */
export async function POST(req: NextRequest) {
  try {
    // 요청 본문에서 URL 및 언어 코드 추출
    const { url, lang, enableParagraphs } = await req.json();
    
    if (!url) {
      console.error('YouTube 트랜스크립트 요청 오류: URL이 제공되지 않음');
      return NextResponse.json(
        { status: 'error', message: 'YouTube URL을 제공해야 합니다.' },
        { status: 400 }
      );
    }

    // 백엔드 API 엔드포인트로 요청 전달
    const backendUrl = `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/youtube/transcript`;
    
    console.log(`YouTube 트랜스크립트 요청: URL=${url}, 언어=${lang || 'en'}, 단락=${enableParagraphs ? '활성화' : '비활성화'}`);
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        url, 
        language: lang || 'en' 
      }),
    });

    const data = await response.json();

    // 백엔드 응답이 성공인 경우
    if (data.status === 'success' && data.transcripts) {
      // 단락으로 구성할지 여부에 따라 처리
      let content: string = '';
      
      if (enableParagraphs) {
        // 문장 끝 기호(.!?)로 문장을 구분하고 단락으로 그룹화
        let currentParagraph: string = '';
        for (const item of data.transcripts) {
          const text = item.text.trim();
          currentParagraph += ' ' + text;
          
          // 문장 끝 기호 확인
          if (text.match(/[.!?]$/)) {
            content += currentParagraph.trim() + '\n\n';
            currentParagraph = '';
          }
        }
        
        // 남은 단락 추가
        if (currentParagraph.trim().length > 0) {
          content += currentParagraph.trim();
        }
      } else {
        // 기본 형식: 모든 자막을 줄바꿈으로 연결
        content = data.transcripts.map((item: TranscriptItem) => item.text).join('\n');
      }

      console.log(`YouTube 트랜스크립트 추출 성공: ${data.transcripts.length}개 항목`);
      
      const responseData: GetTranscriptsResponse = {
        status: 'success',
        content,
        data: {
          url,
          transcripts: data.transcripts,
          enableParagraphs: Boolean(enableParagraphs)
        }
      };

      return NextResponse.json(responseData);
    }

    // 백엔드 응답이 오류인 경우
    console.error(`YouTube 트랜스크립트 요청 실패: ${data.message || '알 수 없는 오류'}`);
    
    return NextResponse.json(
      { 
        status: 'error', 
        message: data.message || '트랜스크립트를 가져오는 중 오류가 발생했습니다.' 
      },
      { status: data.status === 'error' ? 404 : 500 }
    );
  } catch (error) {
    console.error('YouTube 트랜스크립트 처리 오류:', error);
    return NextResponse.json(
      { status: 'error', message: '트랜스크립트 처리 중 서버 오류가 발생했습니다.' },
      { status: 500 }
    );
  }
}

export const GET = POST; // GET 요청도 동일한 핸들러로 처리 