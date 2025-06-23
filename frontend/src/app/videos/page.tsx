'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import Link from 'next/link';

// 비디오 클립 인터페이스 정의
interface VideoClip {
  name: string;
  path: string;
  full_path?: string;
  size: string;
  modified: number;
  modified_str: string;
  has_subtitle: boolean;
  available_subtitles: string[];
}

export default function VideosPage() {
  const router = useRouter();
  const [videoList, setVideoList] = useState<VideoClip[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // 비디오 목록 가져오기
  useEffect(() => {
    const fetchVideoList = async () => {
      try {
        setLoading(true);
        setError(null);
        
        console.log('비디오 목록 가져오기 시작...');
        const response = await axios.get(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/youtube/clips`);
        
        console.log('비디오 목록 응답:', response.data);
        
        if (Array.isArray(response.data)) {
          setVideoList(response.data);
        } else {
          console.error('비디오 목록 응답이 배열이 아님:', response.data);
          setError('서버 응답이 올바른 형식이 아닙니다.');
          setVideoList([]);
        }
      } catch (err) {
        console.error('비디오 목록 가져오기 오류:', err);
        setError('비디오 목록을 가져오는 중 오류가 발생했습니다.');
        setVideoList([]);
      } finally {
        setLoading(false);
      }
    };

    fetchVideoList();
  }, [refreshTrigger]);

  // 비디오 선택 시 편집 페이지로 이동
  const handleVideoSelect = (video: VideoClip) => {
    const path = encodeURIComponent(video.path);
    router.push(`/subtitles?video=${path}`);
  };

  // 목록 새로고침
  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">비디오 클립 목록</h1>
        <div className="flex space-x-2">
          <button
            onClick={handleRefresh}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
            disabled={loading}
          >
            {loading ? '로딩 중...' : '새로고침'}
          </button>
          <button
            onClick={() => router.push('/youtube')}
            className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded"
          >
            새 비디오 다운로드
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <p>{error}</p>
          <p className="text-sm mt-2">
            오류가 계속되면 서버 상태를 확인하거나 관리자에게 문의하세요.
          </p>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <div>
          {videoList.length === 0 ? (
            <div className="bg-gray-100 rounded-lg p-8 text-center">
              <p className="text-lg text-gray-700 mb-4">비디오 클립이 없습니다.</p>
              <p className="text-gray-500 mb-6">
                YouTube 영상을 다운로드하여 새로운 클립을 만들어보세요.
              </p>
              <button
                onClick={() => router.push('/youtube')}
                className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg"
              >
                YouTube 영상 다운로드
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {videoList.map((video, index) => (
                <div
                  key={`${video.path}-${index}`}
                  className="border rounded-lg overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-300"
                >
                  <div className="p-4 bg-white">
                    <h3 className="font-semibold text-lg mb-2 truncate" title={video.name}>
                      {video.name}
                    </h3>
                    <div className="text-sm text-gray-500 mb-3">
                      <p>크기: {video.size}</p>
                      <p>수정일: {video.modified_str}</p>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {video.has_subtitle ? (
                        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded">
                          자막 있음
                        </span>
                      ) : (
                        <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">
                          자막 없음
                        </span>
                      )}
                      {video.available_subtitles.map((sub) => (
                        <span
                          key={sub}
                          className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                        >
                          {sub}
                        </span>
                      ))}
                    </div>
                    <button
                      onClick={() => handleVideoSelect(video)}
                      className="w-full bg-blue-500 hover:bg-blue-600 text-white py-2 rounded"
                    >
                      편집하기
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 개발 정보 표시 (개발 모드에서만) */}
      {process.env.NODE_ENV === 'development' && videoList.length > 0 && (
        <div className="mt-8 p-4 bg-gray-100 rounded">
          <details>
            <summary className="font-semibold cursor-pointer">디버그 정보</summary>
            <div className="mt-2 overflow-x-auto">
              <pre className="text-xs bg-gray-800 text-white p-4 rounded">
                {JSON.stringify(videoList, null, 2)}
              </pre>
            </div>
          </details>
        </div>
      )}
    </div>
  );
} 