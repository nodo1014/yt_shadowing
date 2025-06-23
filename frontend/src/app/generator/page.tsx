'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

interface VideoItem {
  path: string;
  name: string;
  subtitles_available: boolean;
  last_modified: string;
}

interface SubtitleItem {
  index: number;
  start_time: string;
  end_time: string;
  text: string;
  translation?: string;
}

interface GenerationConfig {
  repeat_count: number;
  subtitle_modes: string[];
  use_tts: boolean;
  tts_voice: string;
  highlight_phrases: boolean;
}

// 실제 페이지 컨텐츠를 렌더링하는 컴포넌트
function GeneratorContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const videoPathFromUrl = searchParams.get('video') || '';
  
  // 영상 관련 상태
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  const [videoPath, setVideoPath] = useState(videoPathFromUrl);
  
  // 자막 관련 상태
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SubtitleItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  
  const [selectedSubtitles, setSelectedSubtitles] = useState<SubtitleItem[]>([]);
  const [generatingVideo, setGeneratingVideo] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generatedVideoPath, setGeneratedVideoPath] = useState('');
  
  // 순차적 모드 관련 새로운 상태
  const [sequentialMode, setSequentialMode] = useState(false);
  const [generatedClips, setGeneratedClips] = useState<string[]>([]);
  const [mergingClips, setMergingClips] = useState(false);
  const [mergeProgress, setMergeProgress] = useState(0);
  const [finalVideoPath, setFinalVideoPath] = useState('');
  
  // 생성된 영상 목록 관리 (최근에 생성된 영상들을 저장)
  const [processedVideos, setProcessedVideos] = useState<{path: string, timestamp: number}[]>([]);
  
  const [config, setConfig] = useState<GenerationConfig>({
    repeat_count: 3,
    subtitle_modes: ['no_subtitle', 'en_ko', 'en_ko'],
    use_tts: true,
    tts_voice: 'en-US-GuyNeural',
    highlight_phrases: true,
  });
  
  // 영상 목록 가져오기
  useEffect(() => {
    fetchVideos();
  }, []);
  
  // 선택된 영상의 자막 가져오기
  useEffect(() => {
    if (videoPath) {
      fetchSubtitles();
      
      // URL 파라미터로 전달된 경로가 아니라면, URL 갱신
      if (videoPath !== videoPathFromUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set('video', videoPath);
        window.history.pushState({}, '', url.toString());
      }
    } else {
      setSubtitles([]);
      setSelectedSubtitles([]);
      setError('');
    }
  }, [videoPath, videoPathFromUrl]);
  
  const fetchVideos = async () => {
    try {
      setLoadingVideos(true);
      const response = await fetch('/api/youtube/list-videos');
      const data = await response.json();
      
      if (data.status === 'success') {
        setVideos(data.videos || []);
      }
    } catch (err) {
      console.error('영상 목록 가져오기 오류:', err);
    } finally {
      setLoadingVideos(false);
    }
  };
  
  const fetchSubtitles = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await fetch(`/api/youtube/subtitle/get?video_path=${encodeURIComponent(videoPath)}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setSubtitles(data.subtitles || []);
      } else {
        setError(`자막 로드 오류: ${data.message}`);
      }
    } catch (err) {
      console.error('자막 가져오기 오류:', err);
      setError('자막을 가져오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    
    try {
      setIsSearching(true);
      
      // 검색어에서 특수 문자 제거
      const cleanedQuery = searchQuery.replace(/['",.!?:;()\[\]{}]/g, '').trim();
      
      // 내부적으로 자막 검색 - 정제된 검색어 사용
      const filteredResults = subtitles.filter(
        sub => {
          // 자막 텍스트에서도 특수 문자 제거 후 검색
          const cleanedText = sub.text.replace(/['",.!?:;()\[\]{}]/g, '').trim();
          return cleanedText.toLowerCase().includes(cleanedQuery.toLowerCase());
        }
      );
      
      setSearchResults(filteredResults);
    } catch (err) {
      console.error('자막 검색 오류:', err);
    }
  };
  
  const toggleSubtitleSelection = (subtitle: SubtitleItem) => {
    const index = selectedSubtitles.findIndex(sub => sub.index === subtitle.index);
    
    if (index === -1) {
      // 추가
      setSelectedSubtitles([...selectedSubtitles, subtitle]);
    } else {
      // 제거
      setSelectedSubtitles(selectedSubtitles.filter(sub => sub.index !== subtitle.index));
    }
  };
  
  const generateVideo = async () => {
    if (selectedSubtitles.length === 0) {
      setError('선택된 자막이 없습니다.');
      return;
    }
    
    try {
      setGeneratingVideo(true);
      setGenerationProgress(0);
      setGeneratedVideoPath('');
      setGeneratedClips([]);
      setFinalVideoPath('');
      setError('');
      
      // 진행 상태 표시를 위한 타이머 설정
      const progressInterval = setInterval(() => {
        setGenerationProgress(prev => {
          const newProgress = prev + Math.random() * 10;
          return newProgress >= 100 ? 99 : newProgress; // 100%는 완료 후에 설정
        });
      }, 1000);
      
      // 선택된 자막의 인덱스 및 시간 정보로 요청 구성
      const subtitleSegments = selectedSubtitles.map(sub => ({
        index: sub.index,
        start_time: sub.start_time,
        end_time: sub.end_time,
        text: sub.text,
      }));
      
      if (sequentialMode && selectedSubtitles.length > 1) {
        // 순차적 모드: 각 자막별로 개별 영상 생성 후 병합
        const clipPaths = [];
        
        for (let i = 0; i < selectedSubtitles.length; i++) {
          const subtitle = selectedSubtitles[i];
          const segment = {
            index: subtitle.index,
            start_time: subtitle.start_time,
            end_time: subtitle.end_time,
            text: subtitle.text,
          };
          
          // 개별 클립 생성 요청
          const response = await fetch('/api/youtube/generate-repeat', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              video_path: videoPath,
              subtitle_segments: [segment], // 단일 세그먼트로 전송
              config: {
                repeat_count: config.repeat_count,
                subtitle_modes: config.subtitle_modes,
                tts: {
                  provider: config.use_tts ? 'edge-tts' : null,
                  voice: config.tts_voice,
                },
                focus_phrases: {
                  enabled: config.highlight_phrases,
                },
              },
            }),
          });
          
          const data = await response.json();
          
          if (data.status === 'success' || data.status === 'pending') {
            clipPaths.push(data.output_path);
            
            // 생성된 클립 목록 업데이트
            setGeneratedClips(prev => [...prev, data.output_path]);
            
            // 진행률 업데이트
            setGenerationProgress((i + 1) / selectedSubtitles.length * 100);
            
            // 생성된 영상 목록 추가
            if (data.output_path) {
              setProcessedVideos(prev => [{
                path: data.output_path,
                timestamp: Date.now()
              }, ...prev].slice(0, 10)); // 최근 10개까지만 유지
            }
          } else {
            setError(`클립 생성 오류: ${data.message}`);
            break;
          }
        }
        
        // 모든 클립이 생성되면 병합 요청
        if (clipPaths.length === selectedSubtitles.length) {
          clearInterval(progressInterval);
          setGenerationProgress(100);
          
          // 클립 병합 시작
          setMergingClips(true);
          setMergeProgress(0);
          
          const mergeInterval = setInterval(() => {
            setMergeProgress(prev => {
              const newProgress = prev + Math.random() * 10;
              return newProgress >= 100 ? 99 : newProgress;
            });
          }, 1000);
          
          const mergeResponse = await fetch('/api/youtube/merge-clips', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              clip_paths: clipPaths,
              output_filename: `merged_${Date.now()}.mp4`
            }),
          });
          
          clearInterval(mergeInterval);
          
          const mergeData = await mergeResponse.json();
          
          if (mergeData.status === 'success') {
            setMergeProgress(100);
            setFinalVideoPath(mergeData.output_path);
            
            // 생성된 영상 목록 추가
            setProcessedVideos(prev => [{
              path: mergeData.output_path,
              timestamp: Date.now()
            }, ...prev].slice(0, 10)); // 최근 10개까지만 유지
            
            // 병합 완료 메시지 (추가)
            setError('');
            setMergingClips(false); // 명시적으로 병합 중 상태 해제
            setGeneratingVideo(false); // 생성 중 상태도 함께 해제
          } else {
            setError(`영상 병합 오류: ${mergeData.message}`);
          }
        }
      } else {
        // 기존 단일 영상 생성 방식
        const response = await fetch('/api/youtube/generate-repeat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            video_path: videoPath,
            subtitle_segments: subtitleSegments,
            config: {
              repeat_count: config.repeat_count,
              subtitle_modes: config.subtitle_modes,
              tts: {
                provider: config.use_tts ? 'edge-tts' : null,
                voice: config.tts_voice,
              },
              focus_phrases: {
                enabled: config.highlight_phrases,
              },
            },
          }),
        });
        
        clearInterval(progressInterval);
        
        const data = await response.json();
        
        if (data.status === 'success' || data.status === 'pending') {
          setGenerationProgress(100);
          setGeneratedVideoPath(data.output_path || '');
          
          // 생성된 영상 목록 추가
          if (data.output_path) {
            setProcessedVideos(prev => [{
              path: data.output_path,
              timestamp: Date.now()
            }, ...prev].slice(0, 10)); // 최근 10개까지만 유지
          }
          
          // 생성 완료 메시지 (추가)
          setError('');
          setGeneratingVideo(false); // 명시적으로 생성 중 상태 해제
        } else {
          setError(`반복 영상 생성 오류: ${data.message}`);
        }
      }
    } catch (err) {
      console.error('반복 영상 생성 오류:', err);
      setError('반복 영상 생성 중 오류가 발생했습니다.');
    } finally {
      // 명시적으로 진행 중 상태 해제 
      if (!finalVideoPath && !generatedVideoPath) {
        setGeneratingVideo(false);
        setMergingClips(false);
      }
    }
  };
  
  const formatTimestamp = (timestamp: string) => {
    return timestamp.replace(',', '.');
  };
  
  const displaySubtitles = isSearching ? searchResults : subtitles;
  
  if (loadingVideos) {
    return (
      <div className="container mx-auto p-4 flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-lg">영상 목록을 불러오는 중...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-4 pb-20">
      <h1 className="text-3xl font-bold mb-6">쉐도잉 영상 생성 도구</h1>
      
      {error && (
        <div className="p-4 mb-6 bg-red-100 text-red-700 rounded-lg border border-red-300 flex items-center shadow-sm">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
        </div>
      )}
      
      {/* 영상 선택 섹션 */}
      <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm7 2h1a1 1 0 011 1v3a1 1 0 01-1 1h-1V5zm-2 0H8a1 1 0 00-1 1v3a1 1 0 001 1h1V5zm8 6v3a1 1 0 01-1 1h-1v-4h1a1 1 0 011 1zm-5 3v-4H8v4h4zm-6 0v-4H5v3a1 1 0 001 1h1z" clipRule="evenodd" />
          </svg>
          영상 선택
        </h2>
        
        {videos.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">사용 가능한 영상이 없습니다.</p>
            <Link href="/videos" className="mt-4 inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
              영상 관리 페이지로 이동
            </Link>
          </div>
        ) : (
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <select
                value={videoPath}
                onChange={(e) => {
                  setVideoPath(e.target.value);
                  setSelectedSubtitles([]);
                  setGeneratedVideoPath('');
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">영상을 선택하세요</option>
                {videos.map((video) => (
                  <option key={video.path} value={video.path}>
                    {video.name} {video.subtitles_available ? '(자막있음)' : '(자막없음)'}
                  </option>
                ))}
              </select>
              
              <Link 
                href="/videos" 
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
              >
                영상 관리
              </Link>
            </div>
            
            {videoPath && (
              <div className="flex items-center bg-gray-50 p-3 rounded-lg border border-gray-100">
                <span className="font-medium mr-2">선택된 영상:</span>
                <span className="text-sm text-gray-600">{videoPath.split('/').pop()}</span>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* 자막 관련 섹션 */}
      {videoPath && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
              <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 2h6v4H7V5zm8 8v2h1v-2h-1zm-2-8h1V5h-1v2zm0 8h1v-2h-1v2zM9 13h2v-2H9v2zm0-8h2V5H9v2z" clipRule="evenodd" />
                </svg>
                영상 정보
              </h2>
              <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-100">
                <p className="mb-2 flex items-center">
                  <span className="font-medium mr-2">경로:</span>
                  <span className="text-sm text-gray-600 overflow-hidden overflow-ellipsis">{videoPath}</span>
                </p>
                <p className="flex items-center">
                  <span className="font-medium mr-2">자막 수:</span>
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-medium">{subtitles.length}개</span>
                </p>
              </div>
              {selectedSubtitles.length > 0 && (
                <div className="flex items-center justify-between text-sm bg-green-50 p-3 rounded-lg border border-green-100">
                  <span>선택된 자막: <strong>{selectedSubtitles.length}개</strong></span>
                  <button 
                    onClick={() => setSelectedSubtitles([])}
                    className="text-red-500 hover:text-red-700 font-medium"
                  >
                    선택 초기화
                  </button>
                </div>
              )}
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
              <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
                자막 검색
              </h2>
              
              {loading ? (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mb-4"></div>
                  <p>자막을 불러오는 중...</p>
                </div>
              ) : (
                <>
                  <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-2 mb-4">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="검색어 입력"
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <button
                      type="submit"
                      className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                    >
                      검색
                    </button>
                    {isSearching && (
                      <button
                        type="button"
                        onClick={() => {
                          setSearchQuery('');
                          setSearchResults([]);
                          setIsSearching(false);
                        }}
                        className="px-6 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50"
                      >
                        모두 보기
                      </button>
                    )}
                  </form>
                  
                  <div className="max-h-[50vh] overflow-y-auto rounded-lg border border-gray-200">
                    <div className="sticky top-0 bg-gray-50 p-3 border-b border-gray-200 flex items-center justify-between">
                      <h3 className="font-medium text-gray-700">
                        {isSearching 
                          ? `검색 결과 (${searchResults.length}개)` 
                          : `자막 목록 (선택: ${selectedSubtitles.length}개)`}
                      </h3>
                      {isSearching && searchResults.length > 0 && (
                        <button 
                          onClick={() => {
                            // 검색 결과의 모든 항목 선택
                            const newSelections = [...selectedSubtitles];
                            searchResults.forEach(result => {
                              if (!newSelections.some(s => s.index === result.index)) {
                                newSelections.push(result);
                              }
                            });
                            setSelectedSubtitles(newSelections);
                          }}
                          className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded hover:bg-blue-200 transition-colors"
                        >
                          검색 결과 모두 선택
                        </button>
                      )}
                    </div>
                    
                    {displaySubtitles.length === 0 ? (
                      <div className="p-8 text-center text-gray-500">
                        {isSearching ? (
                          <>
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p>검색 결과가 없습니다.</p>
                            <p className="text-sm mt-1">다른 검색어로 시도해보세요.</p>
                          </>
                        ) : (
                          <>
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            <p>자막이 없습니다.</p>
                            <p className="text-sm mt-1">자막이 있는 영상을 선택하세요.</p>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {displaySubtitles.map((sub) => {
                          const isSelected = selectedSubtitles.some(s => s.index === sub.index);
                          
                          return (
                            <div
                              key={sub.index}
                              onClick={() => toggleSubtitleSelection(sub)}
                              className={`p-3 border rounded cursor-pointer transition-all duration-200 ${
                                isSelected 
                                  ? 'border-green-500 bg-green-50 hover:bg-green-100' 
                                  : 'border-gray-200 hover:bg-gray-50'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <div className="text-sm font-medium text-gray-500 flex items-center">
                                  <span className="bg-gray-200 text-gray-700 px-2 py-0.5 rounded-md text-xs">
                                    {formatTimestamp(sub.start_time)} - {formatTimestamp(sub.end_time)}
                                  </span>
                                  <span className="ml-2 text-xs text-gray-500">#{sub.index}</span>
                                </div>
                                <div>
                                  <input 
                                    type="checkbox" 
                                    checked={isSelected} 
                                    onChange={() => {}} 
                                    className="h-5 w-5 text-blue-600 focus:ring-blue-500 rounded"
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                </div>
                              </div>
                              <div className="font-medium">{sub.text}</div>
                              {sub.translation && (
                                <div className="mt-1 text-gray-600 border-t border-gray-100 pt-1">{sub.translation}</div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
          
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
              <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                </svg>
                간편 설정 및 생성
              </h2>
              
              <div className="space-y-4 mb-4">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">반복 횟수:</span>
                    <div className="flex border border-gray-300 rounded-md overflow-hidden">
                      <button 
                        onClick={() => setConfig({...config, repeat_count: Math.max(1, config.repeat_count - 1)})}
                        className="px-3 py-1 bg-gray-200 text-gray-700 hover:bg-gray-300"
                        disabled={config.repeat_count <= 1}
                      >
                        -
                      </button>
                      <input
                        type="number"
                        min="1"
                        max="10"
                        value={config.repeat_count}
                        onChange={(e) => setConfig({...config, repeat_count: parseInt(e.target.value) || 3})}
                        className="w-12 text-center border-x border-gray-300"
                      />
                      <button 
                        onClick={() => setConfig({...config, repeat_count: Math.min(10, config.repeat_count + 1)})}
                        className="px-3 py-1 bg-gray-200 text-gray-700 hover:bg-gray-300"
                        disabled={config.repeat_count >= 10}
                      >
                        +
                      </button>
                    </div>
                  </div>
                
                  <div className="flex items-center gap-2">
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={config.use_tts}
                        onChange={(e) => setConfig({...config, use_tts: e.target.checked})}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 rounded"
                      />
                      <span className="ml-1 text-sm">TTS 사용</span>
                    </label>
                    
                    <label className="inline-flex items-center">
                      <input
                        type="checkbox"
                        checked={config.highlight_phrases}
                        onChange={(e) => setConfig({...config, highlight_phrases: e.target.checked})}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 rounded"
                      />
                      <span className="ml-1 text-sm">하이라이트</span>
                    </label>
                  </div>
                </div>
                
                {config.use_tts && (
                  <div className="pl-2 border-l-2 border-blue-100">
                    <label className="block text-sm font-medium text-gray-700 mb-1">음성 선택:</label>
                    <select
                      value={config.tts_voice}
                      onChange={(e) => setConfig({...config, tts_voice: e.target.value})}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="en-US-GuyNeural">영어(남성)</option>
                      <option value="en-US-JennyNeural">영어(여성)</option>
                      <option value="en-GB-RyanNeural">영국식 영어(남성)</option>
                      <option value="en-GB-SoniaNeural">영국식 영어(여성)</option>
                    </select>
                  </div>
                )}
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">순차적 개별 영상 생성 모드</label>
                <div className="flex items-center">
                  <input 
                    type="checkbox" 
                    id="sequentialMode" 
                    className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                    checked={sequentialMode}
                    onChange={(e) => setSequentialMode(e.target.checked)}
                  />
                  <label htmlFor="sequentialMode" className="ml-2 block text-sm text-gray-700">
                    선택한 자막별로 개별 영상 생성 후 하나로 병합
                  </label>
                </div>
                {sequentialMode && (
                  <p className="mt-1 text-sm text-gray-500">
                    각 자막마다 개별 영상을 생성한 후 순차적으로 결합합니다. 검색 결과에서 여러 문장을 선택하세요.
                  </p>
                )}
              </div>
              
              <div className="flex flex-col">
                <div className="flex items-center justify-between mb-3">
                  <p className="flex items-center">
                    <span className="font-medium mr-2">선택된 자막:</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      selectedSubtitles.length > 0 ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {selectedSubtitles.length}개
                    </span>
                  </p>
                  
                  {selectedSubtitles.length > 0 && (
                    <span className="text-xs text-gray-500">
                      총 {(selectedSubtitles.reduce((acc, sub) => {
                        // 시간 문자열을 초로 변환하는 함수
                        const timeToSeconds = (timeStr: string): number => {
                          const parts = timeStr.replace(',', '.').split(':');
                          let seconds = 0;
                          for (let i = 0; i < parts.length; i++) {
                            seconds = seconds * 60 + parseFloat(parts[i]);
                          }
                          return seconds;
                        };
                        
                        const start = timeToSeconds(sub.start_time);
                        const end = timeToSeconds(sub.end_time);
                        return acc + (end - start);
                      }, 0) * config.repeat_count).toFixed(1)}초 분량
                    </span>
                  )}
                </div>
                
                <button
                  onClick={generateVideo}
                  disabled={selectedSubtitles.length === 0 || generatingVideo}
                  className={`w-full flex items-center justify-center px-6 py-3 rounded-md text-white font-medium transition-all duration-200 ${
                    selectedSubtitles.length === 0 || generatingVideo
                      ? 'bg-gray-300 cursor-not-allowed'
                      : 'bg-green-600 hover:bg-green-700 shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50'
                  }`}
                >
                  {generatingVideo ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      영상 생성 중...
                    </>
                  ) : (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" clipRule="evenodd" />
                      </svg>
                      반복 영상 생성하기
                    </>
                  )}
                </button>
              </div>
            </div>
            
            {/* 생성 진행 중 UI에 순차 모드 클립 진행상황 표시 추가 */}
            {generatingVideo && !finalVideoPath && (
              <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <h3 className="font-medium mb-3 text-gray-700">생성 진행 중...</h3>
                <div className="mb-2 flex justify-between text-sm font-medium text-gray-500">
                  <span>완료율</span>
                  <span>{Math.round(generationProgress)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                    style={{ width: `${generationProgress}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-xs text-center text-gray-500">
                  {generationProgress < 25 ? '영상 정보 분석 중...' : 
                   generationProgress < 50 ? '자막 구간 추출 중...' :
                   generationProgress < 75 ? '반복 영상 생성 중...' : 
                   '최종 처리 중...'}
                </p>
                
                {/* 순차 모드에서 클립 목록 표시 */}
                {sequentialMode && generatedClips.length > 0 && (
                  <div className="mt-4 border-t pt-3">
                    <h4 className="text-sm font-medium mb-2">생성된 클립: {generatedClips.length}/{selectedSubtitles.length}</h4>
                    <ul className="text-xs text-gray-600 space-y-1 max-h-40 overflow-y-auto">
                      {generatedClips.map((path, idx) => (
                        <li key={idx} className="truncate">
                          - 클립 {idx+1}: {path.split('/').pop()}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            
            {/* 클립 병합 진행 상태 - 병합 중이고 finalVideoPath가 없을 때만 표시 */}
            {mergingClips && !finalVideoPath && (
              <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 mt-4">
                <h3 className="font-medium mb-3 text-gray-700">클립 병합 중...</h3>
                <div className="mb-2 flex justify-between text-sm font-medium text-gray-500">
                  <span>완료율</span>
                  <span>{Math.round(mergeProgress)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                  <div 
                    className="bg-green-600 h-2.5 rounded-full transition-all duration-300" 
                    style={{ width: `${mergeProgress}%` }}
                  ></div>
                </div>
              </div>
            )}
            
            {/* 생성 완료 성공 메시지 표시 */}
            {(finalVideoPath || generatedVideoPath) && !mergingClips && !generatingVideo && (
              <div className="bg-white p-6 rounded-lg shadow-md border border-green-200 mt-4 mb-4">
                <div className="flex items-center text-green-600">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <h3 className="font-medium">영상 생성 완료!</h3>
                </div>
                <p className="text-sm text-gray-600 mt-1 ml-7">
                  선택하신 {selectedSubtitles.length}개의 자막으로 {config.repeat_count}회 반복 영상이 생성되었습니다.
                </p>
              </div>
            )}
            
            {/* 영상 목록 및 재생 영역 - 전체 창으로 표시되도록 수정 */}
            {(finalVideoPath || generatedVideoPath || processedVideos.length > 0) && (
              <div className="mt-4 bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <h2 className="text-xl font-semibold mb-4 text-gray-800 flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 mr-2 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  생성된 영상
                </h2>
                
                <div className="grid grid-cols-1 gap-6">
                  {/* 현재 선택된 영상 플레이어 - 항상 우선적으로 finalVideoPath, 없으면 generatedVideoPath, 없으면 첫번째 processedVideo 표시 */}
                  <div>
                    <div className="aspect-video bg-black mb-4 rounded-md overflow-hidden shadow-lg w-full">
                      {(finalVideoPath || generatedVideoPath || (processedVideos.length > 0)) ? (
                        <video 
                          controls 
                          autoPlay
                          className="w-full h-full" 
                          src={`/api/youtube/stream?path=${encodeURIComponent(finalVideoPath || generatedVideoPath || (processedVideos.length > 0 ? processedVideos[0].path : ''))}`}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full bg-gray-900 text-white">
                          <p>영상을 선택하세요</p>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap justify-between items-center mb-4">
                      <div>
                        <h3 className="text-lg font-medium">영상 정보</h3>
                        <p className="text-sm text-gray-600 mt-1">
                          <span className="font-medium">파일명:</span> {(finalVideoPath || generatedVideoPath || (processedVideos.length > 0 ? processedVideos[0].path : '')).split('/').pop()}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          <span className="font-medium">생성일시:</span> {new Date().toLocaleString()}
                        </p>
                      </div>
                      
                      <div className="flex gap-2 mt-2 sm:mt-0">
                        <a 
                          href={`/api/youtube/stream?path=${encodeURIComponent(finalVideoPath || generatedVideoPath || (processedVideos.length > 0 ? processedVideos[0].path : ''))}&download=true`}
                          download
                          target="_blank"
                          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          다운로드
                        </a>
                        <button
                          onClick={() => {
                            setSelectedSubtitles([]);
                            setFinalVideoPath('');
                            setGeneratedVideoPath('');
                          }}
                          className="inline-flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                          새로 만들기
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  {/* 생성된 영상 목록 - 스크롤 가능한 가로 목록으로 표시 */}
                  {processedVideos.length > 0 && (
                    <div>
                      <h3 className="text-md font-medium mb-3 flex items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M5 3a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 2h10v7h-2l-1 2H8l-1-2H5V5z" clipRule="evenodd" />
                        </svg>
                        최근 생성된 영상 목록
                      </h3>
                      <div className="flex overflow-x-auto space-x-4 pb-4">
                        {processedVideos.map((video, index) => (
                          <div key={index} className="flex-shrink-0 w-72">
                            <div 
                              className={`cursor-pointer rounded-lg overflow-hidden shadow-md border-2 ${
                                (video.path === finalVideoPath || video.path === generatedVideoPath || 
                                 (index === 0 && !finalVideoPath && !generatedVideoPath)) 
                                ? 'border-blue-500' : 'border-gray-100'
                              }`}
                              onClick={() => {
                                if (video.path === finalVideoPath) return;
                                setFinalVideoPath(video.path);
                                setGeneratedVideoPath('');
                              }}
                            >
                              <div className="aspect-video bg-gray-900 relative">
                                <video 
                                  className="w-full h-full object-cover"
                                  src={`/api/youtube/stream?path=${encodeURIComponent(video.path)}`}
                                  onMouseOver={(e) => e.currentTarget.play()} 
                                  onMouseOut={(e) => {e.currentTarget.pause(); e.currentTarget.currentTime = 0;}}
                                />
                                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20 opacity-0 hover:opacity-100 transition-opacity">
                                  <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                </div>
                              </div>
                              <div className="p-2">
                                <p className="truncate text-sm">{video.path.split('/').pop()}</p>
                                <p className="text-xs text-gray-500 mt-1">{new Date(video.timestamp).toLocaleString()}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    생성된 영상은 서버의 <code className="bg-gray-100 px-1 py-0.5 rounded">data/clips_output</code> 폴더에 저장됩니다.
                    다운로드 버튼을 클릭하여 컴퓨터에 저장할 수도 있습니다.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="mt-8 text-center">
        <Link href="/" className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7m-7-7v14" />
          </svg>
          홈으로
        </Link>
      </div>
    </div>
  );
}

// 메인 페이지 컴포넌트
export default function GeneratorPage() {
  return (
    <Suspense fallback={<div className="p-6 text-center">자막 생성기 로딩 중...</div>}>
      <GeneratorContent />
    </Suspense>
  );
} 