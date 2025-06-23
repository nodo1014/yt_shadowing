'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface VideoClip {
  id: string;
  name: string;
  path: string;
  size: number;
  modified: number;
}

interface ThumbnailTemplate {
  id: string;
  name: string;
  description: string;
}

export default function ThumbnailsPage() {
  const [clips, setClips] = useState<VideoClip[]>([]);
  const [selectedClip, setSelectedClip] = useState<VideoClip | null>(null);
  const [mainText, setMainText] = useState('');
  const [subtitleText, setSubtitleText] = useState('');
  const [template, setTemplate] = useState('simple');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [thumbnailUrl, setThumbnailUrl] = useState('');
  
  const templates: ThumbnailTemplate[] = [
    { 
      id: 'simple', 
      name: '심플', 
      description: '깔끔한 흰색 배경에 텍스트 중심 디자인' 
    },
    { 
      id: 'professional', 
      name: '프로페셔널', 
      description: '세련된 어두운 배경에 강조된 텍스트' 
    },
    { 
      id: 'vibrant', 
      name: '비비드', 
      description: '밝고 화려한 색상의 활발한 디자인' 
    },
    { 
      id: 'minimalist', 
      name: '미니멀', 
      description: '단순하고 미니멀한 디자인 스타일' 
    },
    { 
      id: 'dark', 
      name: '다크', 
      description: '어두운 배경에 선명한 텍스트' 
    }
  ];
  
  useEffect(() => {
    fetchClips();
  }, []);
  
  const fetchClips = async () => {
    try {
      const response = await fetch('/api/youtube/clips');
      const data = await response.json();
      
      if (data.status === 'success') {
        setClips(data.clips || []);
      } else {
        console.error('클립 로드 오류:', data.message);
      }
    } catch (err) {
      console.error('클립 목록 가져오기 오류:', err);
    }
  };
  
  const handleClipSelect = (clip: VideoClip) => {
    setSelectedClip(clip);
    setMainText(clip.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
  };
  
  const handleGenerateThumbnail = async () => {
    if (!selectedClip) {
      setError('클립을 선택해주세요.');
      return;
    }
    
    if (!mainText.trim()) {
      setError('메인 텍스트를 입력해주세요.');
      return;
    }
    
    try {
      setLoading(true);
      setError('');
      
      const response = await fetch('/api/thumbnail/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          main_text: mainText,
          subtitle_text: subtitleText || undefined,
          template: template,
          video_path: selectedClip.path,
        }),
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        setThumbnailUrl(data.thumbnail_url);
      } else {
        setError(`썸네일 생성 오류: ${data.message}`);
      }
    } catch (err) {
      console.error('썸네일 생성 오류:', err);
      setError('썸네일 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };
  
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">썸네일 생성</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white p-4 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">클립 선택</h2>
            
            {clips.length === 0 ? (
              <p className="text-gray-500">저장된 클립이 없습니다.</p>
            ) : (
              <div className="max-h-[30vh] overflow-y-auto">
                <div className="space-y-2">
                  {clips.map((clip) => (
                    <div
                      key={clip.id}
                      onClick={() => handleClipSelect(clip)}
                      className={`p-3 border rounded cursor-pointer hover:bg-gray-50 ${
                        selectedClip?.id === clip.id ? 'border-blue-500 bg-blue-50' : ''
                      }`}
                    >
                      <div className="font-medium">{clip.name}</div>
                      <div className="text-sm text-gray-500">
                        크기: {formatFileSize(clip.size)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          <div className="bg-white p-4 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">썸네일 설정</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block mb-1 font-medium">메인 텍스트</label>
                <input
                  type="text"
                  value={mainText}
                  onChange={(e) => setMainText(e.target.value)}
                  placeholder="메인 텍스트 입력"
                  className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block mb-1 font-medium">서브 텍스트 (선택사항)</label>
                <input
                  type="text"
                  value={subtitleText}
                  onChange={(e) => setSubtitleText(e.target.value)}
                  placeholder="서브 텍스트 입력"
                  className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block mb-1 font-medium">템플릿</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2 gap-2">
                  {templates.map((tmpl) => (
                    <div
                      key={tmpl.id}
                      onClick={() => setTemplate(tmpl.id)}
                      className={`p-3 border rounded cursor-pointer hover:bg-gray-50 ${
                        template === tmpl.id ? 'border-blue-500 bg-blue-50' : ''
                      }`}
                    >
                      <div className="font-medium">{tmpl.name}</div>
                      <div className="text-sm text-gray-500">{tmpl.description}</div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <button
                  onClick={handleGenerateThumbnail}
                  disabled={!selectedClip || loading}
                  className="w-full px-6 py-3 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  {loading ? '생성 중...' : '썸네일 생성'}
                </button>
              </div>
              
              {error && (
                <div className="p-3 bg-red-100 text-red-700 rounded">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4">썸네일 미리보기</h2>
          
          {thumbnailUrl ? (
            <div className="space-y-4">
              <div className="aspect-video bg-gray-100 flex items-center justify-center overflow-hidden rounded">
                <img 
                  src={thumbnailUrl} 
                  alt="생성된 썸네일" 
                  className="w-full h-auto"
                />
              </div>
              
              <div className="flex justify-between">
                <a
                  href={thumbnailUrl}
                  download="thumbnail.jpg"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  다운로드
                </a>
                <button
                  onClick={() => setThumbnailUrl('')}
                  className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  새로 만들기
                </button>
              </div>
            </div>
          ) : (
            <div className="aspect-video bg-gray-100 flex items-center justify-center rounded">
              <p className="text-gray-500">
                {loading ? '썸네일 생성 중...' : '썸네일을 생성하면 여기에 표시됩니다.'}
              </p>
            </div>
          )}
        </div>
      </div>
      
      <div className="mt-6 text-center">
        <Link href="/videos" className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 mr-2">
          영상 목록으로
        </Link>
        <Link href="/" className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
          홈으로
        </Link>
      </div>
    </div>
  );
} 