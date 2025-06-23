'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

// 영상 아이템 인터페이스
interface VideoItem {
  name: string;
  path: string;
  size: string;
  modified_str: string;
  has_subtitle: boolean;
  available_subtitles: string[];
}

// 자막 아이템 인터페이스
interface SubtitleItem {
  index: number;
  start_time: string;
  end_time: string;
  text: string;
  translation?: string;
}

// 생성 설정 인터페이스
interface GenerationConfig {
  repeat_count: number;
  subtitle_modes: string[];
  use_tts: boolean;
  tts_voice: string;
  highlight_phrases: boolean;
}

export default function Home() {
  // 현재 선택된 탭
  const [activeTab, setActiveTab] = useState<string>('youtube');
  
  // 영상 관련 상태
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [videoList, setVideoList] = useState<VideoItem[]>([]);
  const [loadingVideos, setLoadingVideos] = useState<boolean>(false);
  const [selectedVideo, setSelectedVideo] = useState<string>('');
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [downloadStatus, setDownloadStatus] = useState<string>('');
  const [downloadTaskId, setDownloadTaskId] = useState<string>('');
  // 자막 언어 선택 상태 추가
  const [subtitleLanguages, setSubtitleLanguages] = useState<string[]>(['en', 'en-US', 'en-GB', 'ko']);
  
  // 자막 관련 상태
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [loadingSubtitles, setLoadingSubtitles] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SubtitleItem[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [selectedSubtitles, setSelectedSubtitles] = useState<SubtitleItem[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en');
  
  // 생성 관련 상태
  const [generatingVideo, setGeneratingVideo] = useState<boolean>(false);
  const [generationProgress, setGenerationProgress] = useState<number>(0);
  const [generatedVideoPath, setGeneratedVideoPath] = useState<string>('');
  const [config, setConfig] = useState<GenerationConfig>({
    repeat_count: 3,
    subtitle_modes: ['no_subtitle', 'en_ko', 'en_ko'],
    use_tts: true,
    tts_voice: 'en-US-GuyNeural',
    highlight_phrases: true,
  });
  
  // 오류 상태
  const [error, setError] = useState<string>('');
  
  // 원스탑 모드 상태
  const [oneStopQuery, setOneStopQuery] = useState<string>('');
  const [oneStopProcessing, setOneStopProcessing] = useState<boolean>(false);
  const [oneStopProgress, setOneStopProgress] = useState<number>(0);
  const [oneStopStatus, setOneStopStatus] = useState<string>('');
  const [oneStopStage, setOneStopStage] = useState<string>('');
  const [oneStopEstimatedTime, setOneStopEstimatedTime] = useState<number>(0);
  const [oneStopResult, setOneStopResult] = useState<string>('');
  
  // 영상 목록 가져오기
  useEffect(() => {
    fetchVideos();
  }, []);
  
  // 선택된 영상이 변경되면 자막 가져오기
  useEffect(() => {
    if (selectedVideo) {
      fetchSubtitles();
    } else {
      setSubtitles([]);
      setSelectedSubtitles([]);
    }
  }, [selectedVideo]);
  
  // 다운로드 상태 추적
  useEffect(() => {
    let timerId: NodeJS.Timeout | null = null;
    
    if (downloadTaskId) {
      timerId = setInterval(() => {
        checkDownloadStatus(downloadTaskId);
      }, 1000);
    }
    
    return () => {
      if (timerId) clearInterval(timerId);
    };
  }, [downloadTaskId]);
  
  // 영상 목록 가져오기 함수
  const fetchVideos = async () => {
    try {
      setLoadingVideos(true);
      const response = await fetch('/api/youtube/clips');
      const data = await response.json();
      
      if (Array.isArray(data)) {
        setVideoList(data);
      } else {
        setError('영상 목록을 가져오는데 실패했습니다.');
      }
    } catch (err) {
      console.error('영상 목록 가져오기 오류:', err);
      setError('영상 목록을 가져오는 중 오류가 발생했습니다.');
    } finally {
      setLoadingVideos(false);
    }
  };
  
  // 자막 가져오기 함수
  const fetchSubtitles = async () => {
    if (!selectedVideo) {
      setError('비디오를 먼저 선택해주세요.');
      return;
    }
    
    try {
      setLoadingSubtitles(true);
      setError('');
      
      // 언어 파라미터를 추가하여 API 호출
      const response = await fetch(`/api/youtube/subtitle/get?video_path=${encodeURIComponent(selectedVideo)}&language=${selectedLanguage}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        if (data.subtitles && data.subtitles.length > 0) {
          setSubtitles(data.subtitles);
          setSelectedSubtitles([]);
        } else {
          setSubtitles([]);
          setSelectedSubtitles([]);
          setError('자막이 없습니다. 다른 언어를 선택하거나 Whisper로 자막을 생성하세요.');
        }
      } else {
        setError(`자막 가져오기 오류: ${data.message || '알 수 없는 오류'}`);
      }
    } catch (err) {
      console.error('자막 가져오기 오류:', err);
      setError('자막 가져오기 중 오류가 발생했습니다.');
    } finally {
      setLoadingSubtitles(false);
    }
  };
  
  // 다운로드 시작 함수
  const startDownload = async () => {
    if (!videoUrl.trim()) {
      setError('YouTube URL을 입력해주세요.');
      return;
    }
    
    try {
      setDownloadStatus('preparing');
      setDownloadProgress(0);
      setError('');
      
      const response = await fetch('/api/youtube/download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: videoUrl,
          options: {
            format: 'best',
            subtitles: true,
          },
          // 선택된 자막 언어 목록 추가
          subtitle_languages: subtitleLanguages,
        }),
      });
      
      const data = await response.json();
      
      if (data.status === 'pending' && data.task_id) {
        setDownloadTaskId(data.task_id);
        setDownloadStatus('downloading');
      } else {
        setError(`다운로드 시작 오류: ${data.message || '알 수 없는 오류'}`);
        setDownloadStatus('error');
      }
    } catch (err) {
      console.error('다운로드 시작 오류:', err);
      setError('다운로드 시작 중 오류가 발생했습니다.');
      setDownloadStatus('error');
    }
  };
  
  // 다운로드 상태 확인 함수
  const checkDownloadStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/youtube/download/status/${taskId}`);
      const data = await response.json();
      
      if (data.status === 'success' || data.status === 'completed') {
        setDownloadStatus('completed');
        setDownloadProgress(100);
        setDownloadTaskId('');
        // 새로운 영상 목록 갱신
        fetchVideos();
      } else if (data.status === 'error') {
        setError(`다운로드 오류: ${data.message || '알 수 없는 오류'}`);
        setDownloadStatus('error');
        setDownloadTaskId('');
      } else if (data.status === 'pending' || data.status === 'processing') {
        setDownloadProgress(data.progress || 0);
      }
    } catch (err) {
      console.error('다운로드 상태 확인 오류:', err);
    }
  };

  // 원스탑 프로세스 실행 함수
  const startOneStopProcess = async () => {
    if (!oneStopQuery.trim()) {
      setError('검색할 대사를 입력해주세요.');
      return;
    }
    
    try {
      setOneStopProcessing(true);
      setOneStopProgress(0);
      setOneStopStage('초기화');
      setOneStopStatus('자막 검색 준비 중...');
      setError('');
      setOneStopResult('');
      
      // 1단계: 모든 영상에서 자막 검색
      setOneStopStage('자막 검색');
      setOneStopStatus('대사와 일치하는 자막을 검색 중...');
      setOneStopProgress(5);
      
      // 여러 줄 처리를 위한 multiline 파라미터 추가
      const searchResponse = await fetch('/api/youtube/subtitle/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: oneStopQuery,
          multiline: oneStopQuery.includes('\n'), // 개행 문자가 있으면 멀티라인 모드 사용
        }),
      });
      
      const searchData = await searchResponse.json();
      
      if (searchData.status !== 'success' || !searchData.results || searchData.results.length === 0) {
        throw new Error(searchData.message || '일치하는 자막을 찾을 수 없습니다.');
      }
      
      setOneStopProgress(20);
      setOneStopStatus(`${searchData.results.length}개의 자막을 찾았습니다.`);
      
      // 가장 일치하는 자막 선택 (첫 번째 결과)
      const bestMatch = searchData.results[0];
      const videoPath = bestMatch.video_path;
      const subtitleSegment = {
        index: bestMatch.index,
        start_time: bestMatch.start_time,
        end_time: bestMatch.end_time,
        text: bestMatch.text,
      };
      
      // 선택된 영상 및 자막으로 작업 크기 추정
      setOneStopStage('작업 시간 추정');
      setOneStopStatus('클립 생성 작업 시간 추정 중...');
      setOneStopProgress(30);
      
      // 작업시간 추정은 건너뛰고 기본값 사용
      setOneStopEstimatedTime(30);
      setOneStopStatus(`예상 소요 시간: 30초`);
      setOneStopProgress(30);
      
      // 2단계: 반복 영상 생성 요청
      setOneStopStage('클립 생성');
      setOneStopStatus('선택된 자막으로 반복 영상 생성 중...');
      setOneStopProgress(40);
      
      const generationConfig = {
        repeat_count: 3,
        subtitle_modes: ['no_subtitle', 'en_ko', 'en_ko'],
        tts: {
          provider: 'edge-tts',
          voice: 'en-US-GuyNeural',
        },
        focus_phrases: {
          enabled: true,
        },
      };
      
      const generateResponse = await fetch('/api/youtube/generate-repeat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_path: videoPath,
          start_time: subtitleSegment.start_time,
          end_time: subtitleSegment.end_time,
          repeat_count: 3,
        }),
      });
      
      const generateData = await generateResponse.json();
      
      if (generateData.status !== 'success' && generateData.status !== 'pending' && generateData.status !== 'accepted') {
        throw new Error(generateData.message || '반복 영상 생성 중 오류가 발생했습니다.');
      }
      
      // 작업 ID가 있으면 진행 상태 추적
      if (generateData.task_id) {
        const taskId = generateData.task_id;
        
        // 진행 상태 확인 인터벌 설정
        let progress = 40;
        const statusInterval = setInterval(async () => {
          try {
            // 올바른 상태 확인 엔드포인트 사용
            const statusResponse = await fetch(`/api/youtube/repeat/status/${taskId}`);
            const statusData = await statusResponse.json();
            
            if (statusData.status === 'processing' || statusData.status === 'progress') {
              progress = Math.min(90, progress + 5);
              setOneStopProgress(progress);
              setOneStopStatus(statusData.message || '반복 영상 생성 중...');
            } else if (statusData.status === 'success' || statusData.status === 'completed') {
              clearInterval(statusInterval);
              setOneStopProgress(100);
              setOneStopStatus('반복 영상 생성 완료!');
              setOneStopStage('완료');
              
              // result 객체에서 output_path를 추출하거나 직접 output_path 사용
              const outputPath = statusData.result?.output_path || statusData.output_path || generateData.output_path;
              if (outputPath) {
                // 스트리밍 URL로 변환 (필요한 경우)
                const streamPath = outputPath.startsWith('/api/') ? outputPath : `/api/youtube/stream/${encodeURIComponent(outputPath)}`;
                setOneStopResult(streamPath);
                setGeneratedVideoPath(streamPath);
              }
            } else if (statusData.status === 'failure' || statusData.status === 'error') {
              clearInterval(statusInterval);
              throw new Error(statusData.error || statusData.message || '반복 영상 생성 중 오류가 발생했습니다.');
            }
          } catch (err) {
            console.error('상태 확인 오류:', err);
          }
        }, 2000);
        
        // accepted 상태에 대한 처리 추가
        if (generateData.status === 'accepted') {
          // 이미 task_id가 있는 경우이므로 진행 중 상태로 설정
          setOneStopStatus(`작업 ID ${taskId}로 영상 생성이 시작되었습니다.`);
          setOneStopProgress(45);
        }
        // 즉시 결과를 받은 경우 또는 상태 체크 없는 경우
        else if (generateData.status === 'success' && generateData.output_path) {
          clearInterval(statusInterval);
          setOneStopProgress(100);
          setOneStopStatus('반복 영상 생성 완료!');
          setOneStopStage('완료');
          setOneStopResult(generateData.output_path);
          setGeneratedVideoPath(generateData.output_path);
        }
      } else if (generateData.output_path) {
        // 작업 ID 없이 바로 결과가 나온 경우
        setOneStopProgress(100);
        setOneStopStatus('반복 영상 생성 완료!');
        setOneStopStage('완료');
        setOneStopResult(generateData.output_path);
        setGeneratedVideoPath(generateData.output_path);
      }
    } catch (err: any) {
      console.error('원스탑 프로세스 오류:', err);
      setError(`원스탑 프로세스 오류: ${err.message || '알 수 없는 오류'}`);
      setOneStopStatus('오류 발생');
    } finally {
      if (!oneStopResult) {
        setOneStopProcessing(false);
      }
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-gray-900 text-white shadow-md">
        <div className="container mx-auto py-6 px-4">
          <h1 className="text-4xl font-bold text-center">영어 쉐도잉 시스템</h1>
          <p className="text-center text-gray-300 mt-2">영상 자막을 활용한 언어 학습 쉐도잉(shadowing) 연습 도구</p>
        </div>
      </header>
      
      {/* 오류 메시지 */}
      {error && (
        <div className="container mx-auto px-4 mt-4">
          <div className="p-4 mb-4 bg-red-100 text-red-700 rounded-lg border border-red-300 flex items-center shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" width="20" height="20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}
      
      {/* 통합 인터페이스 */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 gap-6">
          {/* 새로운 섹션: 원스탑 모드 */}
          <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-blue-600">
            <h2 className="text-2xl font-bold mb-4 flex items-center">
              <span className="inline-flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full mr-3 text-sm">
                ★
              </span>
              원스탑 모드
            </h2>
            <p className="text-gray-700 mb-4">
              대사를 입력하면 자동으로 자막을 검색하고 반복 영상을 생성합니다. 모든 과정이 자동으로 처리됩니다.
            </p>
            
            <div className="space-y-4">
              <div>
                <label htmlFor="one-stop-query" className="block text-sm font-medium text-gray-700 mb-1">
                  찾을 대사
                </label>
                <div className="flex flex-col">
                  <textarea
                    id="one-stop-query"
                    value={oneStopQuery}
                    onChange={(e) => setOneStopQuery(e.target.value)}
                    placeholder="영상에서 찾을 대사를 입력하세요... (여러 줄 입력 가능, 각 줄은 개별 검색어로 처리됩니다)"
                    className="w-full px-4 py-2 border border-gray-300 rounded-t-md focus:ring-blue-500 focus:border-blue-500"
                    disabled={oneStopProcessing}
                    rows={10}
                    style={{ resize: 'vertical', overflowY: 'auto' }}
                  />
                  <button
                    onClick={startOneStopProcess}
                    disabled={oneStopProcessing || !oneStopQuery.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-b-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400"
                  >
                    {oneStopProcessing ? '처리 중...' : '실행'}
                  </button>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  여러 줄 입력 시 각 줄은 별도 검색어로 처리되며, 가장 좋은 매치를 사용합니다.
                </p>
              </div>
              
              {oneStopProcessing && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-medium text-blue-700">
                      {oneStopStage}: {oneStopStatus}
                    </div>
                    <div className="text-sm text-blue-600">
                      {oneStopEstimatedTime > 0 && oneStopProgress < 100 && (
                        <>예상 시간: 약 {Math.ceil(oneStopEstimatedTime * (1 - oneStopProgress/100))}초 남음</>
                      )}
                    </div>
                  </div>
                  
                  <div className="relative pt-1">
                    <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200">
                      <div 
                        style={{ width: `${oneStopProgress}%` }} 
                        className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500 transition-all duration-300"
                      />
                    </div>
                  </div>
                  
                  <div className="text-xs text-gray-600">
                    {oneStopProgress < 20 ? '자막 검색 중...' : 
                     oneStopProgress < 40 ? '작업 추정 중...' : 
                     oneStopProgress < 70 ? '영상 클립 생성 중...' : 
                     oneStopProgress < 90 ? '반복 영상 생성 중...' : 
                     '최종 처리 중...'}
                  </div>
                </div>
              )}
              
              {oneStopResult && (
                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                  <div className="flex items-center mb-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <div className="font-medium text-green-700">
                      영상 생성 완료!
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">
                    생성된 영상은 아래 반복 영상 생성 섹션에서 확인할 수 있습니다.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* 1. YouTube 다운로드 섹션 */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-4">1. YouTube 영상 다운로드</h2>
            <div className="space-y-4">
              <div>
                <label htmlFor="youtube-url" className="block text-sm font-medium text-gray-700 mb-1">
                  YouTube URL
                </label>
                <div className="flex">
                  <input
                    id="youtube-url"
                    type="text"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=..."
                    className="flex-grow px-4 py-2 border border-gray-300 rounded-l-md focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={startDownload}
                    disabled={downloadStatus === 'downloading' || downloadStatus === 'preparing'}
                    className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400"
                  >
                    {downloadStatus === 'downloading' || downloadStatus === 'preparing' ? '다운로드 중...' : '다운로드'}
                  </button>
                </div>
              </div>

              {/* 자막 언어 선택 드롭다운 추가 */}
              <div>
                <label htmlFor="subtitle-languages" className="block text-sm font-medium text-gray-700 mb-1">
                  자막 언어 선택
                </label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { code: 'en', name: '영어' },
                    { code: 'en-US', name: '영어(미국)' },
                    { code: 'en-GB', name: '영어(영국)' },
                    { code: 'ko', name: '한국어' },
                    { code: 'ja', name: '일본어' },
                    { code: 'zh-CN', name: '중국어(간체)' },
                    { code: 'zh-TW', name: '중국어(번체)' },
                    { code: 'fr', name: '프랑스어' },
                    { code: 'de', name: '독일어' },
                    { code: 'es', name: '스페인어' }
                  ].map(language => (
                    <div key={language.code} className="flex items-center">
                      <input
                        type="checkbox"
                        id={`lang-${language.code}`}
                        value={language.code}
                        checked={subtitleLanguages.includes(language.code)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSubtitleLanguages([...subtitleLanguages, language.code]);
                          } else {
                            setSubtitleLanguages(subtitleLanguages.filter(lang => lang !== language.code));
                          }
                        }}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mr-1"
                      />
                      <label htmlFor={`lang-${language.code}`} className="text-sm text-gray-700 mr-2">
                        {language.name}
                      </label>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  선택한 모든 언어로 자막을 검색합니다. 최소 하나 이상 선택해주세요.
                </p>
              </div>
              
              {(downloadStatus === 'downloading' || downloadStatus === 'preparing') && (
                <div className="mt-4">
                  <div className="relative pt-1">
                    <div className="text-xs text-gray-600 mb-1">
                      {downloadProgress}% 완료
                    </div>
                    <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-200">
                      <div 
                        style={{ width: `${downloadProgress}%` }} 
                        className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500"
                      />
                    </div>
                  </div>
                </div>
              )}
              
              {downloadStatus === 'completed' && (
                <div className="mt-4 p-3 bg-green-100 text-green-800 rounded-md">
                  다운로드가 완료되었습니다. 영상 선택 탭에서 확인하세요.
                </div>
              )}
            </div>
          </div>

          {/* 2. 영상 선택 섹션 */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">2. 영상 선택</h2>
              <button
                onClick={fetchVideos}
                className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                새로고침
              </button>
            </div>
            
            {loadingVideos ? (
              <div className="py-10 text-center">
                <svg className="animate-spin h-10 w-10 mx-auto text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" width="40" height="40">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
            ) : videoList.length === 0 ? (
              <div className="py-10 text-center text-gray-500">
                다운로드된 영상이 없습니다. YouTube 다운로드 탭에서 영상을 다운로드하세요.
              </div>
            ) : (
              <div className="overflow-auto max-h-72">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        영상 이름
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        크기
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        수정일
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        자막
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        선택
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {videoList.map((video, index) => (
                      <tr 
                        key={index}
                        className={selectedVideo === video.path ? 'bg-blue-50' : 'hover:bg-gray-50'}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{video.name}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{video.size}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{video.modified_str}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {video.has_subtitle ? (
                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                              자막 있음
                            </span>
                          ) : (
                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                              자막 없음
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button
                            onClick={() => {
                              setSelectedVideo(video.path);
                              // 자막 자동 로드
                              if (video.has_subtitle) {
                                fetchSubtitles();
                              }
                            }}
                            className={`px-3 py-1 rounded-md ${
                              selectedVideo === video.path
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                          >
                            {selectedVideo === video.path ? '선택됨' : '선택'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 3. 자막 관리 섹션 */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-4">3. 자막 검색 및 선택</h2>
            
            {!selectedVideo ? (
              <div className="py-10 text-center text-gray-500">
                먼저 위에서 영상을 선택하세요.
              </div>
            ) : (
              <>
                {/* 자막 언어 선택 드롭다운 추가 */}
                <div className="mb-4">
                  <label htmlFor="subtitle-language" className="block text-sm font-medium text-gray-700 mb-1">
                    자막 언어 선택
                  </label>
                  <div className="flex">
                    <select
                      id="subtitle-language"
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      className="mr-2 w-48 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="en">영어</option>
                      <option value="en-US">영어(미국)</option>
                      <option value="en-GB">영어(영국)</option>
                      <option value="ko">한국어</option>
                      <option value="ja">일본어</option>
                      <option value="zh-CN">중국어(간체)</option>
                      <option value="zh-TW">중국어(번체)</option>
                      <option value="fr">프랑스어</option>
                      <option value="de">독일어</option>
                      <option value="es">스페인어</option>
                    </select>
                    <button
                      onClick={fetchSubtitles}
                      disabled={loadingSubtitles}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400"
                    >
                      {loadingSubtitles ? '로딩 중...' : '자막 가져오기'}
                    </button>
                  </div>
                </div>
              
                {loadingSubtitles ? (
                  <div className="py-10 text-center">
                    <svg className="animate-spin h-10 w-10 mx-auto text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" width="40" height="40">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                ) : subtitles.length === 0 ? (
                  <div className="py-10 text-center text-gray-500">
                    선택한 영상에 {selectedLanguage} 자막이 없습니다.
                  </div>
                ) : (
                  <>
                    <div className="mb-4">
                      <label htmlFor="subtitle-search" className="block text-sm font-medium text-gray-700 mb-1">
                        자막 검색
                      </label>
                      <div className="flex">
                        <input
                          id="subtitle-search"
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="검색어 입력..."
                          className="flex-grow px-4 py-2 border border-gray-300 rounded-l-md focus:ring-blue-500 focus:border-blue-500"
                        />
                        <button
                          onClick={() => {
                            setIsSearching(true);
                            setSearchResults(
                              subtitles.filter(subtitle => 
                                subtitle.text.toLowerCase().includes(searchQuery.toLowerCase())
                              )
                            );
                          }}
                          className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          검색
                        </button>
                      </div>
                    </div>
                    
                    <div className="overflow-auto max-h-72 border border-gray-200 rounded-md">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              #
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              시작 시간
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              자막 텍스트
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                              선택
                            </th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {(isSearching ? searchResults : subtitles).map((subtitle) => (
                            <tr key={subtitle.index} className="hover:bg-gray-50">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {subtitle.index}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {subtitle.start_time}
                              </td>
                              <td className="px-6 py-4 text-sm text-gray-900">
                                {subtitle.text}
                                {subtitle.translation && (
                                  <div className="text-gray-500 text-xs mt-1">{subtitle.translation}</div>
                                )}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                <button
                                  onClick={() => {
                                    const isSelected = selectedSubtitles.some(s => s.index === subtitle.index);
                                    if (isSelected) {
                                      setSelectedSubtitles(selectedSubtitles.filter(s => s.index !== subtitle.index));
                                    } else {
                                      setSelectedSubtitles([...selectedSubtitles, subtitle]);
                                    }
                                  }}
                                  className={`px-3 py-1 rounded-md ${
                                    selectedSubtitles.some(s => s.index === subtitle.index)
                                      ? 'bg-blue-600 text-white'
                                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                  }`}
                                >
                                  {selectedSubtitles.some(s => s.index === subtitle.index) ? '선택됨' : '선택'}
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    
                    <div className="mt-4 text-sm text-gray-600">
                      {selectedSubtitles.length > 0 ? (
                        <div>
                          <div className="font-medium">선택된 자막 ({selectedSubtitles.length}개):</div>
                          <ul className="mt-2 pl-5 list-disc">
                            {selectedSubtitles.map(s => (
                              <li key={s.index} className="mb-1">{s.text}</li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        '학습하고 싶은 자막을 선택하세요.'
                      )}
                    </div>
                  </>
                )}
              </>
            )}
          </div>

          {/* 4. 영상 생성 섹션 */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-4">4. 반복 영상 생성</h2>
            
            {selectedSubtitles.length === 0 ? (
              <div className="py-10 text-center text-gray-500">
                먼저 위에서 자막을 선택하세요.
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <h3 className="text-lg font-semibold mb-3">선택된 자막</h3>
                    <div className="border border-gray-200 rounded-md p-4 h-48 overflow-auto">
                      <ul className="space-y-2">
                        {selectedSubtitles.map(s => (
                          <li key={s.index} className="text-sm">
                            <span className="text-gray-500 mr-2">{s.start_time}</span>
                            {s.text}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-lg font-semibold mb-3">생성 설정</h3>
                    <div className="space-y-4">
                      <div>
                        <label htmlFor="repeat-count" className="block text-sm font-medium text-gray-700 mb-1">
                          반복 횟수
                        </label>
                        <input
                          id="repeat-count"
                          type="number"
                          min="1"
                          max="10"
                          value={config.repeat_count}
                          onChange={(e) => setConfig({...config, repeat_count: parseInt(e.target.value)})}
                          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                        />
                      </div>
                      
                      <div className="flex items-center">
                        <input
                          id="use-tts"
                          type="checkbox"
                          checked={config.use_tts}
                          onChange={(e) => setConfig({...config, use_tts: e.target.checked})}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <label htmlFor="use-tts" className="ml-2 block text-sm text-gray-700">
                          TTS 사용
                        </label>
                      </div>
                      
                      <div className="flex items-center">
                        <input
                          id="highlight-phrases"
                          type="checkbox"
                          checked={config.highlight_phrases}
                          onChange={(e) => setConfig({...config, highlight_phrases: e.target.checked})}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <label htmlFor="highlight-phrases" className="ml-2 block text-sm text-gray-700">
                          문구 강조
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex justify-end">
                  <button
                    onClick={async () => {
                      if (selectedVideo && selectedSubtitles.length > 0) {
                        try {
                          setGeneratingVideo(true);
                          setGenerationProgress(0);
                          setError('');
                          
                          const firstSubtitle = selectedSubtitles[0];
                          
                          // 영상 생성 요청 보내기
                          const response = await fetch('/api/youtube/generate-repeat', {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                              video_path: selectedVideo,
                              start_time: firstSubtitle.start_time,
                              end_time: firstSubtitle.end_time,
                              repeat_count: config.repeat_count
                            }),
                          });
                          
                          const data = await response.json();
                          
                          if (data.status === 'accepted' || data.status === 'pending' || data.status === 'success') {
                            // 작업 상태 추적 
                            if (data.task_id) {
                              const taskId = data.task_id;
                              let intervalId = setInterval(async () => {
                                try {
                                  const statusResponse = await fetch(`/api/youtube/repeat/status/${taskId}`);
                                  const statusData = await statusResponse.json();
                                  
                                  if (statusData.status === 'success' || statusData.status === 'completed') {
                                    clearInterval(intervalId);
                                    setGeneratingVideo(false);
                                    setGenerationProgress(100);
                                    
                                    // 실제 생성된 영상 경로 설정
                                    // 주의: 백엔드가 반환하는 경로를 /api/youtube/stream/ 경로로 변환
                                    const videoPath = statusData.result?.output_path || statusData.output_path || data.output_path;
                                    if (videoPath) {
                                      const streamPath = videoPath.startsWith('/api/') ? videoPath : `/api/youtube/stream/${encodeURIComponent(videoPath)}`;
                                      setGeneratedVideoPath(streamPath);
                                    }
                                  } else if (statusData.status === 'failure' || statusData.status === 'error') {
                                    clearInterval(intervalId);
                                    setGeneratingVideo(false);
                                    setError(`영상 생성 실패: ${statusData.error || statusData.message || '알 수 없는 오류'}`);
                                  } else {
                                    // 진행 상황 업데이트
                                    const progress = statusData.progress || 0;
                                    setGenerationProgress(progress);
                                  }
                                } catch (error) {
                                  console.error('상태 확인 중 오류:', error);
                                }
                              }, 1000);
                            } else if (data.output_path) {
                              // 작업 ID 없이 바로 결과가 있는 경우
                              setGeneratingVideo(false);
                              setGenerationProgress(100);
                              const videoPath = data.output_path;
                              const streamPath = videoPath.startsWith('/api/') ? videoPath : `/api/youtube/stream/${encodeURIComponent(videoPath)}`;
                              setGeneratedVideoPath(streamPath);
                            }
                          } else if (data.status === 'error') {
                            setGeneratingVideo(false);
                            setError(`영상 생성 시작 오류: ${data.message || '알 수 없는 오류'}`);
                          }
                        } catch (error) {
                          console.error('영상 생성 오류:', error);
                          setGeneratingVideo(false);
                          setError('영상 생성 중 오류가 발생했습니다.');
                        }
                      } else {
                        setError('영상과 자막을 먼저 선택해주세요.');
                      }
                    }}
                    disabled={generatingVideo || selectedSubtitles.length === 0}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-400"
                  >
                    {generatingVideo ? '생성 중...' : '영상 생성'}
                  </button>
                </div>
                
                {generatingVideo && (
                  <div className="mt-6">
                    <div className="relative pt-1">
                      <div className="flex justify-between mb-1">
                        <div className="text-sm font-medium text-blue-700">
                          영상 생성 중...
                        </div>
                        <div className="text-sm font-medium text-blue-700">
                          {generationProgress}%
                        </div>
                      </div>
                      <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-gray-200">
                        <div 
                          style={{ width: `${generationProgress}%` }} 
                          className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500 transition-all duration-300"
                        />
                      </div>
                      <div className="text-xs text-gray-600">
                        {generationProgress < 20 ? '시작 준비 중...' : 
                         generationProgress < 40 ? '영상 구간 추출 중...' : 
                         generationProgress < 60 ? '반복 영상 구성 중...' : 
                         generationProgress < 80 ? '영상 인코딩 중...' : 
                         '최종 처리 중...'}
                      </div>
                    </div>
                  </div>
                )}
                
                {generatedVideoPath && (
                  <div className="mt-6">
                    <h3 className="text-lg font-semibold mb-3">생성된 영상</h3>
                    <div className="aspect-w-16 aspect-h-9 border border-gray-200 rounded-md overflow-hidden">
                      <video controls className="w-full h-full">
                        <source src={generatedVideoPath} type="video/mp4" />
                        브라우저가 비디오 태그를 지원하지 않습니다.
                      </video>
                    </div>
                    <div className="mt-2 text-sm text-gray-600">
                      <p>다운로드: <a href={generatedVideoPath} className="text-blue-600 hover:underline" download>영상 다운로드</a></p>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
      
      {/* 푸터 */}
      <footer className="bg-gray-900 text-gray-300 py-6">
        <div className="container mx-auto px-4 text-center">
          <p>영어 쉐도잉 자동화 시스템 v0.3.0</p>
          <p className="text-sm mt-2">© 2024 YouTube 쉐도잉 시스템</p>
        </div>
      </footer>
    </main>
  );
}
