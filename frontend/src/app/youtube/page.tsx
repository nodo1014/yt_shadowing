"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'react-hot-toast';
import axios from 'axios';

export default function YouTubePage() {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloadStatus, setDownloadStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isUrlValid, setIsUrlValid] = useState(false);

  // 다운로드 상태 추적
  useEffect(() => {
    if (taskId && downloading) {
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      
      // 로그 메시지
      console.log(`다운로드 상태 확인 시작: task_id=${taskId}`);
      
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${BACKEND_URL}/api/youtube/download/status/${taskId}`);
          const data = response.data;
          
          console.log(`다운로드 상태 업데이트: progress=${data.progress}, status=${data.status}`);
          
          if (data.status === 'error') {
            clearInterval(interval);
            setError(`다운로드 오류: ${data.message}`);
            setDownloading(false);
            toast.error(`다운로드 오류: ${data.message}`);
            return;
          }
          
          setDownloadProgress(data.progress || 0);
          setDownloadStatus(data.message || '다운로드 중...');
          
          // 완료 또는 오류 상태 확인
          if (data.status === 'success') {
            clearInterval(interval);
            const message = '비디오가 성공적으로 다운로드되었습니다.';
            setSuccessMessage(message);
            setDownloading(false);
            toast.success(message);
            // 2초 후 클립 목록 페이지로 이동
            setTimeout(() => {
              router.push('/videos');
            }, 2000);
          } else if (data.status === 'failure') {
            clearInterval(interval);
            const errorMsg = `다운로드 오류: ${data.error || '알 수 없는 오류'}`;
            setError(errorMsg);
            setDownloading(false);
            toast.error(errorMsg);
          }
        } catch (err) {
          console.error('상태 확인 오류:', err);
          // 일시적인 네트워크 오류의 경우 계속 재시도
        }
      }, 1000);
      
      return () => {
        console.log(`다운로드 상태 확인 중지: task_id=${taskId}`);
        clearInterval(interval);
      };
    }
  }, [taskId, downloading, router]);

  // URL 유효성 검증
  useEffect(() => {
    const validateUrl = (url: string) => {
      // YouTube URL 패턴
      const patterns = [
        /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/,
        /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})($|&.+$)/
      ];
      
      setIsUrlValid(patterns.some(pattern => pattern.test(url.trim())));
    };
    
    if (url.trim()) {
      validateUrl(url);
    } else {
      setIsUrlValid(false);
    }
  }, [url]);

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setError('YouTube URL을 입력해주세요');
      toast.error('YouTube URL을 입력해주세요');
      return;
    }
    
    if (!isUrlValid) {
      setError('유효한 YouTube URL을 입력해주세요');
      toast.error('유효한 YouTube URL을 입력해주세요');
      return;
    }
    
    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    console.log(`다운로드 요청: URL=${url}`);
    
    setError(null);
    setSuccessMessage(null);
    setDownloading(true);
    setDownloadProgress(0);
    setDownloadStatus('다운로드 준비 중...');
    
    try {
      // 비디오 다운로드 요청
      const response = await axios.post(`${BACKEND_URL}/api/youtube/download`, { url });
      const data = response.data;
      
      console.log(`다운로드 요청 응답:`, data);
      
      if (data.status === 'accepted' && data.task_id) {
        setTaskId(data.task_id);
        toast.success('다운로드가 시작되었습니다');
        // 상태 추적은 useEffect에서 처리
      } else {
        const errorMsg = `다운로드 오류: ${data.message}`;
        setError(errorMsg);
        setDownloading(false);
        toast.error(errorMsg);
      }
    } catch (err) {
      console.error('비디오 다운로드 오류:', err);
      const errorMsg = '비디오 다운로드 중 오류가 발생했습니다.';
      setError(errorMsg);
      setDownloading(false);
      toast.error(errorMsg);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-md overflow-hidden">
        <div className="bg-blue-600 p-4">
          <h1 className="text-xl md:text-2xl font-bold text-white">YouTube 영상 다운로드</h1>
        </div>
        
        <div className="p-6">
          <form onSubmit={handleDownload} className="mb-6">
            <div className="mb-4">
              <label htmlFor="youtubeUrl" className="block text-sm font-medium text-gray-700 mb-1">
                YouTube URL
              </label>
              <input
                id="youtubeUrl"
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className={`w-full px-4 py-3 border rounded-md focus:outline-none focus:ring-2 ${
                  url && !isUrlValid ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                }`}
                disabled={downloading}
              />
              {url && !isUrlValid && (
                <p className="mt-1 text-sm text-red-600">유효한 YouTube URL을 입력해주세요.</p>
              )}
            </div>
            
            <button
              type="submit"
              disabled={downloading || (url.trim() !== '' && !isUrlValid)}
              className={`w-full py-3 px-4 rounded-md text-white font-medium transition-colors ${
                downloading || (url.trim() !== '' && !isUrlValid)
                  ? 'bg-blue-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {downloading ? '다운로드 중...' : '다운로드'}
            </button>
          </form>
          
          {downloading && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-1">다운로드 진행 상황</h3>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300" 
                  style={{ width: `${downloadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600 mt-2">
                {downloadStatus} ({Math.round(downloadProgress)}%)
              </p>
            </div>
          )}
          
          {error && (
            <div className="p-4 mb-6 bg-red-50 border-l-4 border-red-500">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}
          
          {successMessage && (
            <div className="p-4 mb-6 bg-green-50 border-l-4 border-green-500">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700">{successMessage}</p>
                  <p className="text-sm text-green-600 mt-1">클립 목록 페이지로 이동합니다...</p>
                </div>
              </div>
            </div>
          )}
          
          <div className="mt-6 bg-gray-50 p-4 rounded-md">
            <h3 className="text-sm font-medium text-gray-700 mb-2">도움말</h3>
            <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1">
              <li>YouTube 영상 URL을 입력하고 다운로드 버튼을 클릭하세요.</li>
              <li>다운로드한 영상은 자동으로 클립 목록에 추가됩니다.</li>
              <li>영상에 자막이 있는 경우 함께 다운로드됩니다.</li>
              <li>자막이 없는 경우 Whisper를 사용하여 자동으로 생성할 수 있습니다.</li>
            </ul>
          </div>
        </div>
        
        <div className="px-6 py-4 bg-gray-50 border-t flex justify-between">
          <button
            onClick={() => router.back()}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            뒤로 가기
          </button>
          
          <button
            onClick={() => router.push('/videos')}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700"
          >
            클립 목록으로
          </button>
        </div>
      </div>
    </div>
  );
} 