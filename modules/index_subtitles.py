#!/usr/bin/env python3
"""
파일: index_subtitles.py
설명: 자막 파일을 색인화하여 텍스트 내용을 추출하고 구성합니다
입력: SRT 자막 파일 경로, 출력 형식(json 또는 sqlite)
출력: 색인화된 자막이 포함된 subtitle_index.json 또는 SQLite 데이터베이스
라이브러리: pysrt, json, sqlite3, re, os
업데이트: 
  - 2025-05-01: 초기 버전

이 모듈은 SRT 자막 파일을 처리하고 HTML 태그를 제거한 후
쉽게 검색하고 검색할 수 있도록 자막의 색인된 데이터베이스를 생성합니다.
"""

import os
import re
import json
import pysrt
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("subtitle_indexer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SubtitleIndexer:
    """자막 내용을 색인화하고 관리하는 클래스"""
    
    def __init__(self, subtitle_dir: str, output_format: str = 'json'):
        """
        SubtitleIndexer 초기화
        
        인자:
            subtitle_dir: SRT 파일이 포함된 디렉토리
            output_format: 색인을 저장할 형식(json 또는 sqlite)
        """
        self.subtitle_dir = Path(subtitle_dir)
        self.output_format = output_format
        self.subtitle_index = {}
        self.db_conn = None
        
    def clean_text(self, text: str) -> str:
        """
        HTML 태그를 제거하고 자막 텍스트 정리
        
        인자:
            text: 원본 자막 텍스트
            
        반환:
            HTML 태그가 제거된 정리된 텍스트
        """
        # HTML 태그 제거
        clean = re.sub(r'<[^>]+>', '', text)
        # 여러 공백과 줄바꿈 제거
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
    
    def process_srt_file(self, srt_path: Path) -> List[Dict]:
        """
        단일 SRT 파일을 처리하고 자막 데이터 추출
        
        인자:
            srt_path: SRT 파일 경로
            
        반환:
            타이밍과 텍스트가 포함된 자막 항목 리스트
        """
        try:
            logger.info(f"자막 파일 처리 중: {srt_path}")
            subs = pysrt.open(srt_path)
            
            video_name = srt_path.stem
            subtitle_data = []
            
            for sub in subs:
                start_time = sub.start.to_time()
                end_time = sub.end.to_time()
                text = self.clean_text(sub.text)
                
                if text:  # 빈 자막 건너뛰기
                    subtitle_data.append({
                        "text": text,
                        "start_time": str(start_time),
                        "end_time": str(end_time),
                        "duration": (end_time.hour * 3600 + end_time.minute * 60 + end_time.second) - 
                                  (start_time.hour * 3600 + start_time.minute * 60 + start_time.second)
                    })
            
            return subtitle_data
            
        except Exception as e:
            logger.error(f"{srt_path} 처리 중 오류 발생: {str(e)}")
            return []
    
    def index_subtitles(self) -> None:
        """
        지정된 디렉토리 및 모든 하위 디렉토리의 모든 자막 파일 색인화
        """
        logger.info(f"다음 위치에서 자막 색인화 중: {self.subtitle_dir}")
        
        if not self.subtitle_dir.exists():
            logger.error(f"자막 디렉토리가 존재하지 않음: {self.subtitle_dir}")
            return
        
        # 하위 디렉토리까지 모두 탐색
        for srt_file in self.subtitle_dir.rglob('*.srt'):
            video_name = srt_file.stem
            subtitle_data = self.process_srt_file(srt_file)
            
            if subtitle_data:
                self.subtitle_index[video_name] = subtitle_data
        
        if self.subtitle_index:
            self._save_index()
            logger.info(f"{len(self.subtitle_index)}개의 자막 파일 색인화 완료")
        else:
            logger.warning("색인화된 자막 데이터가 없습니다")
    
    def initialize_db(self) -> None:
        """자막 저장을 위한 SQLite 데이터베이스 초기화"""
        try:
            self.db_conn = sqlite3.connect('subtitle_index.db')
            cursor = self.db_conn.cursor()
            
            # 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_name TEXT UNIQUE
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS subtitles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER,
                text TEXT,
                start_time TEXT,
                end_time TEXT,
                duration REAL,
                FOREIGN KEY (video_id) REFERENCES videos (id)
            )
            ''')
            
            # 더 빠른 검색을 위한 텍스트 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_subtitle_text ON subtitles (text)')
            
            self.db_conn.commit()
        except Exception as e:
            logger.error(f"데이터베이스 초기화 오류: {str(e)}")
            if self.db_conn:
                self.db_conn.close()
            self.db_conn = None
    
    def _save_index(self) -> None:
        """자막 색인을 지정된 출력 형식으로 저장"""
        if self.output_format == 'json':
            self._save_to_json()
        elif self.output_format == 'sqlite':
            self._save_to_sqlite()
        else:
            logger.error(f"지원되지 않는 출력 형식: {self.output_format}")
    
    def _save_to_json(self) -> None:
        """자막 색인을 JSON 파일로 저장"""
        try:
            output_file = Path('subtitle_index.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.subtitle_index, f, ensure_ascii=False, indent=2)
            
            logger.info(f"자막 색인을 다음 위치에 저장: {output_file.absolute()}")
        except Exception as e:
            logger.error(f"JSON 저장 중 오류 발생: {str(e)}")
    
    def _save_to_sqlite(self) -> None:
        """자막 색인을 SQLite 데이터베이스에 저장"""
        try:
            if not self.db_conn:
                self.initialize_db()
                
            if not self.db_conn:
                logger.error("데이터베이스 연결 초기화 실패")
                return
                
            cursor = self.db_conn.cursor()
            
            for video_name, subtitles in self.subtitle_index.items():
                # 비디오 삽입 및 ID 가져오기
                cursor.execute('INSERT OR IGNORE INTO videos (video_name) VALUES (?)', (video_name,))
                cursor.execute('SELECT id FROM videos WHERE video_name = ?', (video_name,))
                video_id = cursor.fetchone()[0]
                
                # 자막 삽입
                for sub in subtitles:
                    cursor.execute('''
                    INSERT INTO subtitles (video_id, text, start_time, end_time, duration)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (
                        video_id,
                        sub['text'],
                        sub['start_time'],
                        sub['end_time'],
                        sub['duration']
                    ))
            
            self.db_conn.commit()
            logger.info("자막 색인을 SQLite 데이터베이스에 저장했습니다")
            
        except Exception as e:
            logger.error(f"SQLite 저장 중 오류 발생: {str(e)}")
        finally:
            if self.db_conn:
                self.db_conn.close()
    
    def search_subtitles(self, query: str, limit: int = 10) -> List[Dict]:
        """
        색인화된 자막에서 일치하는 텍스트 검색
        
        인자:
            query: 검색할 텍스트
            limit: 반환할 최대 결과 수
            
        반환:
            일치하는 자막 항목 리스트
        """
        results = []
        
        if self.output_format == 'json':
            # 메모리에 없는 경우 JSON에서 로드
            if not self.subtitle_index:
                try:
                    with open('subtitle_index.json', 'r', encoding='utf-8') as f:
                        self.subtitle_index = json.load(f)
                except Exception as e:
                    logger.error(f"자막 색인 로드 중 오류 발생: {str(e)}")
                    return results
            
            # 메모리에서 검색
            for video_name, subtitles in self.subtitle_index.items():
                for sub in subtitles:
                    if query.lower() in sub['text'].lower():
                        results.append({
                            'video_name': video_name,
                            'subtitle': sub
                        })
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break
                    
        elif self.output_format == 'sqlite':
            try:
                conn = sqlite3.connect('subtitle_index.db')
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT v.video_name, s.text, s.start_time, s.end_time, s.duration
                FROM subtitles s
                JOIN videos v ON s.video_id = v.id
                WHERE s.text LIKE ?
                LIMIT ?
                ''', (f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    video_name, text, start_time, end_time, duration = row
                    results.append({
                        'video_name': video_name,
                        'subtitle': {
                            'text': text,
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': duration
                        }
                    })
                    
                conn.close()
                
            except Exception as e:
                logger.error(f"SQLite 검색 중 오류 발생: {str(e)}")
        
        return results

def main():
    """자막 색인기를 실행하는 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='자막 파일 색인화')
    parser.add_argument('--subtitle-dir', type=str, required=True, 
                        help='SRT 자막 파일이 포함된 디렉토리')
    parser.add_argument('--format', type=str, choices=['json', 'sqlite'], default='json',
                        help='출력 형식 (기본값: json)')
    args = parser.parse_args()
    
    indexer = SubtitleIndexer(args.subtitle_dir, args.format)
    indexer.index_subtitles()

if __name__ == "__main__":
    main()
