/**
 * YouTube 트랜스크립트 아이템 인터페이스
 */
export interface TranscriptItem {
  text: string;     // 자막 텍스트
  start: number;    // 시작 시간(초)
  duration: number; // 지속 시간(초)
}

/**
 * YouTube 트랜스크립트 요청 매개변수 인터페이스
 */
export interface GetTranscriptsParams {
  url: string;             // YouTube URL 또는 ID
  lang?: string;           // 자막 언어 코드 (선택 사항, 기본값: 'en')
  enableParagraphs?: boolean; // 단락 나누기 활성화 (선택 사항, 기본값: false)
}

/**
 * YouTube 트랜스크립트 응답 인터페이스
 */
export interface GetTranscriptsResponse {
  status: 'success' | 'error';     // 응답 상태
  content?: string;                // 추출된 트랜스크립트 내용
  message?: string;                // 오류 메시지 (오류 발생 시)
  data?: {
    url: string;                   // 원본 YouTube URL 또는 ID
    transcripts: TranscriptItem[]; // 트랜스크립트 항목 목록
    enableParagraphs: boolean;     // 단락 나누기 활성화 여부
  };
}

/**
 * YouTube 트랜스크립트 기능 인터페이스
 */
export interface YouTubeTranscriptInterface {
  get_transcripts: (params: GetTranscriptsParams) => Promise<GetTranscriptsResponse>;
} 