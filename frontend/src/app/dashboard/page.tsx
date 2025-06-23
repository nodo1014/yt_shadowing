'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Stats {
  clips_count: number;
  subtitles_count: number;
  repeat_videos_count: number;
  thumbnails_count: number;
  total_duration: number;
}

interface RecentActivity {
  id: string;
  action: string;
  item: string;
  timestamp: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({
    clips_count: 0,
    subtitles_count: 0,
    repeat_videos_count: 0,
    thumbnails_count: 0,
    total_duration: 0,
  });
  
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchDashboardData();
  }, []);
  
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // 실제 API가 구현되어 있지 않으므로 더미 데이터를 사용
      setTimeout(() => {
        setStats({
          clips_count: 8,
          subtitles_count: 12,
          repeat_videos_count: 5,
          thumbnails_count: 4,
          total_duration: 3600, // 1시간
        });
        
        setRecentActivities([
          {
            id: '1',
            action: '영상 다운로드',
            item: 'english_conversation_01.mp4',
            timestamp: Date.now() - 1000 * 60 * 5, // 5분 전
          },
          {
            id: '2',
            action: '자막 처리',
            item: 'business_meeting_subtitles.srt',
            timestamp: Date.now() - 1000 * 60 * 30, // 30분 전
          },
          {
            id: '3',
            action: '반복 영상 생성',
            item: 'daily_expressions_repeat.mp4',
            timestamp: Date.now() - 1000 * 60 * 60, // 1시간 전
          },
          {
            id: '4',
            action: '썸네일 생성',
            item: 'interview_questions_thumbnail.jpg',
            timestamp: Date.now() - 1000 * 60 * 60 * 2, // 2시간 전
          },
          {
            id: '5',
            action: '영상 다운로드',
            item: 'travel_phrases.mp4',
            timestamp: Date.now() - 1000 * 60 * 60 * 5, // 5시간 전
          },
        ]);
        
        setLoading(false);
      }, 1000);
      
      // 실제 구현 시에는 아래와 같이 API 호출
      // const response = await fetch('/api/dashboard/stats');
      // const data = await response.json();
      // if (data.status === 'success') {
      //   setStats(data.stats);
      //   setRecentActivities(data.recent_activities);
      // }
    } catch (err) {
      console.error('대시보드 데이터 가져오기 오류:', err);
    }
  };
  
  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    return `${hours}시간 ${minutes}분`;
  };
  
  const formatTimestamp = (timestamp: number): string => {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.round(diffMs / 1000);
    const diffMin = Math.round(diffSec / 60);
    const diffHour = Math.round(diffMin / 60);
    const diffDay = Math.round(diffHour / 24);
    
    if (diffSec < 60) return `${diffSec}초 전`;
    if (diffMin < 60) return `${diffMin}분 전`;
    if (diffHour < 24) return `${diffHour}시간 전`;
    return `${diffDay}일 전`;
  };
  
  if (loading) {
    return (
      <div className="container mx-auto p-4 text-center">
        <p>대시보드 로딩 중...</p>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">대시보드</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-lg shadow-md">
          <div className="text-lg font-medium text-gray-500">영상 클립</div>
          <div className="text-3xl font-bold">{stats.clips_count}개</div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow-md">
          <div className="text-lg font-medium text-gray-500">자막</div>
          <div className="text-3xl font-bold">{stats.subtitles_count}개</div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow-md">
          <div className="text-lg font-medium text-gray-500">반복 영상</div>
          <div className="text-3xl font-bold">{stats.repeat_videos_count}개</div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow-md">
          <div className="text-lg font-medium text-gray-500">총 영상 길이</div>
          <div className="text-3xl font-bold">{formatDuration(stats.total_duration)}</div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 bg-white p-4 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4">최근 활동</h2>
          
          {recentActivities.length === 0 ? (
            <p className="text-gray-500">최근 활동이 없습니다.</p>
          ) : (
            <div className="divide-y">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="py-3 flex justify-between items-center">
                  <div>
                    <div className="font-medium">{activity.action}</div>
                    <div className="text-sm text-gray-500">{activity.item}</div>
                  </div>
                  <div className="text-sm text-gray-500">
                    {formatTimestamp(activity.timestamp)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4">빠른 링크</h2>
          
          <div className="space-y-2">
            <Link 
              href="/videos" 
              className="block w-full p-3 bg-blue-600 text-white text-center rounded hover:bg-blue-700"
            >
              영상 관리
            </Link>
            
            <Link 
              href="/subtitles" 
              className="block w-full p-3 bg-green-600 text-white text-center rounded hover:bg-green-700"
            >
              자막 관리
            </Link>
            
            <Link 
              href="/generator" 
              className="block w-full p-3 bg-purple-600 text-white text-center rounded hover:bg-purple-700"
            >
              반복 영상 생성
            </Link>
            
            <Link 
              href="/thumbnails" 
              className="block w-full p-3 bg-yellow-600 text-white text-center rounded hover:bg-yellow-700"
            >
              썸네일 생성
            </Link>
          </div>
          
          <div className="mt-6 p-4 bg-gray-100 rounded">
            <h3 className="font-medium mb-2">도움말</h3>
            <p className="text-sm text-gray-600 mb-2">
              영어 쉐도잉을 위한 반복 영상을 생성하는 방법:
            </p>
            <ol className="text-sm text-gray-600 list-decimal list-inside pl-2 space-y-1">
              <li>YouTube 영상을 다운로드하거나 영상 파일을 업로드합니다.</li>
              <li>자막을 추출하고 필요시 번역을 추가합니다.</li>
              <li>원하는 문장을 선택하고 반복 설정을 구성합니다.</li>
              <li>반복 영상을 생성하고 다운로드합니다.</li>
            </ol>
          </div>
        </div>
      </div>
      
      <div className="mt-6 text-center">
        <Link href="/" className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
          홈으로
        </Link>
      </div>
    </div>
  );
} 