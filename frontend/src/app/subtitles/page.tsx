'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

interface SubtitleItem {
  index: number;
  start_time: string;
  end_time: string;
  text: string;
  translation?: string;
}

export default function SubtitlesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const videoPath = searchParams.get('video') || '';
  
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SubtitleItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedSubtitle, setSelectedSubtitle] = useState<SubtitleItem | null>(null);
  const [translation, setTranslation] = useState('');
  
  // Whisper 자막 생성 관련 상태
  const [showWhisperModal, setShowWhisperModal] = useState(false);
  const [whisperModel, setWhisperModel] = useState('tiny');
  const [whisperEstimate, setWhisperEstimate] = useState<any>(null);
  const [whisperLoading, setWhisperLoading] = useState(false);
  const [whisperProgress, setWhisperProgress] = useState(0);
  const [whisperTaskId, setWhisperTaskId] = useState<string | null>(null);
  const [whisperStatus, setWhisperStatus] = useState('');
  
  useEffect(() => {
    if (videoPath) {
      fetchSubtitles();
    } else {
      setError('영상을 선택해주세요.');
      setLoading(false);
    }
  }, [videoPath]);
  
  // Whisper 생성 상태 추적
  useEffect(() => {
    if (whisperTaskId && whisperLoading) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(`/api/youtube/whisper/status/${whisperTaskId}`);
          const data = await response.json();
          
          if (data.status === 'error') {
            clearInterval(interval);
            setError(`자막 생성 오류: ${data.message}`);
            setWhisperLoading(false);
            return;
          }
          
          setWhisperProgress(data.progress || 0);
          setWhisperStatus(data.message || '자막 생성 중...');
          
          // 완료 또는 오류 상태 확인
          if (data.status === 'success') {
            clearInterval(interval);
            setWhisperLoading(false);
            setShowWhisperModal(false);
            // 자막 다시 로드
            await fetchSubtitles();
          } else if (data.status === 'failure') {
            clearInterval(interval);
            setError(`자막 생성 오류: ${data.error || '알 수 없는 오류'}`);
            setWhisperLoading(false);
          }
        } catch (err) {
          console.error('상태 확인 오류:', err);
        }
      }, 1000);
      
      return () => clearInterval(interval);
    }
  }, [whisperTaskId, whisperLoading, videoPath]);
  
  const fetchSubtitles = async () => {
    try {
      setLoading(true);
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/youtube/subtitle/get?video_path=${encodeURIComponent(videoPath)}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setSubtitles(data.subtitles || []);
      } else {
        setError(`자막 로드 오류: ${data.message}`);
        
        // 자막이 없는 경우 Whisper 모달 표시 제안
        if (data.message.includes('자막을 찾을 수 없습니다')) {
          const shouldUseWhisper = window.confirm('자막이 없습니다. Whisper로 자막을 생성하시겠습니까?');
          if (shouldUseWhisper) {
            setShowWhisperModal(true);
            await estimateWhisperTime();
          }
        }
      }
    } catch (err) {
      console.error('자막 가져오기 오류:', err);
      setError('자막을 가져오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };
  
  const estimateWhisperTime = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/youtube/whisper/estimate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_path: videoPath,
          model: whisperModel
        }),
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        setWhisperEstimate(data.estimate);
      } else {
        console.error('처리 시간 예상 오류:', data.message);
      }
    } catch (err) {
      console.error('처리 시간 예상 요청 오류:', err);
    }
  };
  
  const generateWhisperSubtitle = async () => {
    try {
      setWhisperLoading(true);
      setWhisperProgress(0);
      setWhisperStatus('자막 생성 준비 중...');
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/youtube/whisper/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_path: videoPath,
          model: whisperModel,
          language: 'en'
        }),
      });
      
      const data = await response.json();
      
      if (data.status === 'accepted' && data.task_id) {
        setWhisperTaskId(data.task_id);
        // 상태 추적은 useEffect에서 처리
      } else {
        setError(`자막 생성 오류: ${data.message}`);
        setWhisperLoading(false);
      }
    } catch (err) {
      console.error('자막 생성 오류:', err);
      setError('자막 생성 중 오류가 발생했습니다.');
      setWhisperLoading(false);
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
  
  const handleSubtitleClick = (subtitle: SubtitleItem) => {
    setSelectedSubtitle(subtitle);
    setTranslation(subtitle.translation || '');
  };
  
  const saveTranslation = async () => {
    if (!selectedSubtitle) return;
    
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const apiUrl = `${backendUrl}/api/subtitle/translate`;
      
      console.log('API 요청 URL:', apiUrl);
      
      const requestBody = {
        video_path: videoPath,
        subtitle_index: selectedSubtitle.index,
        text: selectedSubtitle.text,
        translation: translation,
      };
      
      console.log('요청 본문:', JSON.stringify(requestBody));
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      console.log('응답 상태:', response.status);
      
      const data = await response.json();
      console.log('응답 데이터:', data);
      
      if (data.status === 'success') {
        // 번역이 성공적으로 저장됨
        const updatedSubtitles = [...subtitles];
        const index = updatedSubtitles.findIndex(s => s.index === selectedSubtitle.index);
        
        if (index !== -1) {
          updatedSubtitles[index] = {
            ...updatedSubtitles[index],
            translation,
          };
          
          setSubtitles(updatedSubtitles);
          
          // 검색 결과도 업데이트
          if (isSearching) {
            const updatedResults = [...searchResults];
            const resultIndex = updatedResults.findIndex(s => s.index === selectedSubtitle.index);
            
            if (resultIndex !== -1) {
              updatedResults[resultIndex] = {
                ...updatedResults[resultIndex],
                translation,
              };
              
              setSearchResults(updatedResults);
            }
          }
        }
      } else {
        console.error('번역 저장 오류:', data.message);
      }
    } catch (err) {
      console.error('번역 저장 중 오류 발생:', err);
    }
  };
  
  const formatTimestamp = (timestamp: string) => {
    return timestamp.replace(',', '.');
  };
  
  const displaySubtitles = isSearching ? searchResults : subtitles;
  
  if (loading) {
    return (
      <div className="container mx-auto p-4 text-center">
        <p>자막을 불러오는 중...</p>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">자막 관리</h1>
      
      {error ? (
        <div className="p-4 bg-red-100 text-red-700 rounded mb-6">
          {error}
          {error.includes('자막을 찾을 수 없습니다') && (
            <div className="mt-2">
              <button
                onClick={() => {
                  setShowWhisperModal(true);
                  estimateWhisperTime();
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Whisper로 자막 생성하기
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="mb-6 bg-white p-4 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-2">영상 정보</h2>
            <p className="mb-2">경로: {videoPath}</p>
            <p>자막 수: {subtitles.length}개</p>
          </div>
          
          <div className="mb-6 bg-white p-4 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">자막 검색</h2>
            <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="검색어 입력"
                className="flex-1 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
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
                  className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  모두 보기
                </button>
              )}
            </form>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-4 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold mb-4">
                {isSearching 
                  ? `검색 결과 (${searchResults.length}개)` 
                  : `자막 목록 (${subtitles.length}개)`}
              </h2>
              
              <div className="max-h-[50vh] overflow-y-auto">
                {displaySubtitles.length === 0 ? (
                  <p className="text-gray-500">
                    {isSearching ? '검색 결과가 없습니다.' : '자막이 없습니다.'}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {displaySubtitles.map((sub) => (
                      <div
                        key={sub.index}
                        onClick={() => handleSubtitleClick(sub)}
                        className={`p-3 border rounded cursor-pointer hover:bg-gray-50 ${
                          selectedSubtitle?.index === sub.index ? 'border-blue-500 bg-blue-50' : ''
                        }`}
                      >
                        <div className="text-sm text-gray-500 mb-1">
                          {formatTimestamp(sub.start_time)} - {formatTimestamp(sub.end_time)}
                        </div>
                        <div className="font-medium">{sub.text}</div>
                        {sub.translation && (
                          <div className="mt-1 italic text-gray-600">{sub.translation}</div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow-md">
              <h2 className="text-xl font-semibold mb-4">번역 관리</h2>
              
              {selectedSubtitle ? (
                <div>
                  <div className="mb-4">
                    <h3 className="font-medium mb-1">원문:</h3>
                    <div className="p-3 border rounded bg-gray-50">
                      {selectedSubtitle.text}
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <h3 className="font-medium mb-1">번역:</h3>
                    <textarea
                      value={translation}
                      onChange={(e) => setTranslation(e.target.value)}
                      className="w-full p-3 border rounded min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="번역문을 입력하세요"
                    ></textarea>
                  </div>
                  
                  <div className="flex gap-2">
                    <button
                      onClick={saveTranslation}
                      className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                    >
                      저장
                    </button>
                    
                    <button
                      onClick={() => {
                        setSelectedSubtitle(null);
                        setTranslation('');
                      }}
                      className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                    >
                      취소
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">
                  왼쪽에서 자막을 선택하면 번역을 관리할 수 있습니다.
                </p>
              )}
            </div>
          </div>
        </>
      )}
      
      <div className="mt-6 text-center">
        <Link href="/videos" className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
          영상 목록으로
        </Link>
        <Link href="/" className="ml-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
          홈으로
        </Link>
      </div>
      
      {/* Whisper 자막 생성 모달 */}
      {showWhisperModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-xl font-semibold mb-4">Whisper로 자막 생성</h2>
            
            <div className="mb-4">
              <label className="block mb-2 font-medium">모델 선택:</label>
              <select
                value={whisperModel}
                onChange={(e) => {
                  setWhisperModel(e.target.value);
                  // 모델 변경 시 예상 시간 다시 계산
                  estimateWhisperTime();
                }}
                className="w-full px-3 py-2 border rounded"
                disabled={whisperLoading}
              >
                <option value="tiny">Tiny (가장 빠름, 39M)</option>
                <option value="base">Base (빠름, 74M)</option>
                <option value="small">Small (보통, 244M)</option>
                <option value="medium">Medium (느림, 769M)</option>
                <option value="large">Large (가장 느림, 1.5GB)</option>
              </select>
            </div>
            
            {whisperEstimate && (
              <div className="mb-4 p-3 bg-blue-50 text-blue-700 rounded">
                <p>예상 처리 시간: {whisperEstimate.human_estimate}</p>
                <p>모델 크기: {whisperEstimate.model_size}</p>
                <p>처리 속도: {whisperEstimate.processing_speed}</p>
              </div>
            )}
            
            {whisperLoading && (
              <div className="mb-4">
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                    style={{ width: `${whisperProgress}%` }}
                  ></div>
                </div>
                <p className="text-sm text-center mt-1">{whisperStatus} ({Math.round(whisperProgress)}%)</p>
              </div>
            )}
            
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowWhisperModal(false)}
                className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                disabled={whisperLoading}
              >
                취소
              </button>
              <button
                onClick={generateWhisperSubtitle}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-300"
                disabled={whisperLoading || !whisperEstimate}
              >
                {whisperLoading ? '생성 중...' : '자막 생성'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}