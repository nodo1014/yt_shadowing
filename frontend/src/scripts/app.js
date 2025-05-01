/**
 * 영어 쉐도잉 자동화 시스템 프론트엔드 스크립트
 */

// API 엔드포인트 베이스 URL
const API_BASE_URL = 'http://localhost:8000/api';

// 페이지 전환 관리
const pageManager = {
    activePageId: 'home',
    
    showPage(pageId) {
        // 모든 페이지 숨기기
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        
        // 선택한 페이지 표시
        const targetPage = document.getElementById(pageId);
        if (targetPage) {
            targetPage.classList.add('active');
            this.activePageId = pageId;
            
            // 네비게이션 활성화 상태 업데이트
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
            });
            
            const activeNavLink = document.querySelector(`.nav-link[data-page="${pageId}"]`);
            if (activeNavLink) {
                activeNavLink.classList.add('active');
            }
            
            // URL 업데이트
            history.pushState({ pageId }, '', `#${pageId}`);
        }
    },
    
    init() {
        // 네비게이션 클릭 이벤트 리스너
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const pageId = link.getAttribute('data-page');
                this.showPage(pageId);
            });
        });
        
        // 브라우저 뒤로가기/앞으로가기 처리
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.pageId) {
                this.showPage(e.state.pageId);
            } else {
                this.showPage('home');
            }
        });
        
        // 초기 페이지 로드
        const hash = window.location.hash.replace('#', '');
        this.showPage(hash || 'home');
        
        // 초기 상태 푸시
        history.replaceState({ pageId: this.activePageId }, '', hash ? `#${hash}` : '#home');
    }
};

// API 요청 관리
const api = {
    async get(endpoint) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`);
            if (!response.ok) {
                throw new Error(`API 요청 실패: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API 오류:', error);
            throw error;
        }
    },
    
    async post(endpoint, data) {
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`API 요청 실패: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API 오류:', error);
            throw error;
        }
    }
};

// 모달 관리
const modal = {
    show(modalId, options = {}) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            // 커스텀 메시지 설정
            if (options.message) {
                const messageElement = modalElement.querySelector('.modal-message');
                if (messageElement) {
                    messageElement.textContent = options.message;
                }
            }
            
            // 모달 열기
            modalElement.classList.add('active');
            
            // 닫기 이벤트 설정
            const closeButtons = modalElement.querySelectorAll('.close-modal, .modal-close-btn');
            closeButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    this.hide(modalId);
                    if (options.onClose) {
                        options.onClose();
                    }
                });
            });
            
            // ESC 키로 닫기
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    this.hide(modalId);
                    document.removeEventListener('keydown', escHandler);
                    if (options.onClose) {
                        options.onClose();
                    }
                }
            };
            document.addEventListener('keydown', escHandler);
            
            // 배경 클릭으로 닫기
            modalElement.addEventListener('click', (e) => {
                if (e.target === modalElement) {
                    this.hide(modalId);
                    if (options.onClose) {
                        options.onClose();
                    }
                }
            });
        }
    },
    
    hide(modalId) {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            modalElement.classList.remove('active');
        }
    }
};

// 비디오 추출 기능
const videoExtractor = {
    init() {
        const extractForm = document.getElementById('extract-form');
        if (extractForm) {
            extractForm.addEventListener('submit', this.handleExtractSubmit.bind(this));
        }
    },
    
    async handleExtractSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        // 진행 상태 표시
        const progressBar = document.querySelector('.progress-fill');
        const statusText = document.querySelector('.task-status');
        
        try {
            // 폼 데이터를 객체로 변환
            const data = {
                url: formData.get('video_url'),
                start: formData.get('start_time'),
                end: formData.get('end_time'),
                output: formData.get('output_name') || `clip_${Date.now()}.mp4`,
                subtitle_only: formData.get('subtitle_only') === 'on'
            };
            
            // 진행 상태 초기화
            progressBar.style.width = '0%';
            statusText.textContent = '비디오 추출 준비 중...';
            
            // 추출 API 호출
            const response = await api.post('/videos/extract', data);
            
            // 작업 ID 가져오기
            const taskId = response.task_id;
            
            // 진행 상태 폴링 시작
            this.pollTaskStatus(taskId, progressBar, statusText);
            
        } catch (error) {
            console.error('비디오 추출 오류:', error);
            modal.show('error-modal', {
                message: '비디오 추출 중 오류가 발생했습니다: ' + error.message
            });
        }
    },
    
    async pollTaskStatus(taskId, progressBar, statusText) {
        try {
            const response = await api.get(`/videos/status/${taskId}`);
            
            // 진행 상태 업데이트
            progressBar.style.width = `${response.progress}%`;
            statusText.textContent = response.status;
            
            if (response.state === 'PENDING' || response.state === 'PROGRESS') {
                // 계속 폴링
                setTimeout(() => {
                    this.pollTaskStatus(taskId, progressBar, statusText);
                }, 1000);
            } else if (response.state === 'SUCCESS') {
                // 성공 완료
                progressBar.style.width = '100%';
                statusText.textContent = '완료!';
                
                modal.show('success-modal', {
                    message: '비디오가 성공적으로 추출되었습니다.'
                });
                
                // 필요한 경우 파일 목록 새로고침
                this.refreshFileList();
                
            } else if (response.state === 'FAILURE') {
                // 실패
                statusText.textContent = '실패: ' + response.error;
                modal.show('error-modal', {
                    message: '비디오 추출에 실패했습니다: ' + response.error
                });
            }
        } catch (error) {
            console.error('상태 확인 오류:', error);
            statusText.textContent = '상태 확인 중 오류 발생';
        }
    },
    
    async refreshFileList() {
        try {
            const clips = await api.get('/videos/clips');
            const clipsList = document.getElementById('clips-list');
            
            if (clipsList) {
                // 목록 초기화
                clipsList.innerHTML = '';
                
                // 새로운 항목 추가
                clips.forEach(clip => {
                    const item = document.createElement('div');
                    item.className = 'media-item';
                    
                    item.innerHTML = `
                        <div class="media-thumbnail">
                            <i class="fas fa-file-video"></i>
                        </div>
                        <div class="media-info">
                            <div class="media-title">${clip.name}</div>
                            <div class="media-meta">${clip.duration} | ${clip.size}</div>
                        </div>
                    `;
                    
                    // 클릭 이벤트 - 상세 정보 표시
                    item.addEventListener('click', () => {
                        this.showClipDetails(clip);
                    });
                    
                    clipsList.appendChild(item);
                });
            }
        } catch (error) {
            console.error('파일 목록 가져오기 오류:', error);
        }
    },
    
    showClipDetails(clip) {
        // 상세 정보를 모달로 표시
        const detailsModal = document.getElementById('clip-details-modal');
        
        if (detailsModal) {
            // 상세 정보 채우기
            const titleElement = detailsModal.querySelector('.modal-title');
            const videoElement = detailsModal.querySelector('video');
            const detailsElement = detailsModal.querySelector('.clip-details');
            
            if (titleElement) titleElement.textContent = clip.name;
            if (videoElement) {
                videoElement.src = `/api/videos/stream/${encodeURIComponent(clip.path)}`;
                videoElement.poster = clip.thumbnail || '';
            }
            
            if (detailsElement) {
                detailsElement.innerHTML = `
                    <p><strong>파일명:</strong> ${clip.name}</p>
                    <p><strong>길이:</strong> ${clip.duration}</p>
                    <p><strong>크기:</strong> ${clip.size}</p>
                    <p><strong>해상도:</strong> ${clip.width}x${clip.height}</p>
                    <p><strong>생성일:</strong> ${new Date(clip.created_at).toLocaleString()}</p>
                `;
            }
            
            // 모달 표시
            modal.show('clip-details-modal');
        }
    }
};

// 자막 관리 기능
const subtitleManager = {
    init() {
        const subtitleForm = document.getElementById('subtitle-form');
        if (subtitleForm) {
            subtitleForm.addEventListener('submit', this.handleSubtitleSubmit.bind(this));
        }
        
        // 초기 자막 목록 로드
        this.loadSubtitleList();
    },
    
    async handleSubtitleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        try {
            // 폼 데이터 준비
            const data = {
                video_id: formData.get('video_id'),
                language: formData.get('language') || 'en',
                translate_to: formData.get('translate_to') || 'ko',
                auto_translate: formData.get('auto_translate') === 'on'
            };
            
            // 자막 추출 API 호출
            const response = await api.post('/subtitles/extract', data);
            
            // 성공 메시지 표시
            modal.show('success-modal', {
                message: '자막이 성공적으로 추출되었습니다.'
            });
            
            // 자막 목록 새로고침
            this.loadSubtitleList();
            
        } catch (error) {
            console.error('자막 추출 오류:', error);
            modal.show('error-modal', {
                message: '자막 추출 중 오류가 발생했습니다: ' + error.message
            });
        }
    },
    
    async loadSubtitleList() {
        try {
            const subtitles = await api.get('/subtitles/list');
            const subtitlesList = document.getElementById('subtitles-list');
            
            if (subtitlesList) {
                // 목록 초기화
                subtitlesList.innerHTML = '';
                
                // 새로운 항목 추가
                subtitles.forEach(subtitle => {
                    const item = document.createElement('div');
                    item.className = 'media-item';
                    
                    item.innerHTML = `
                        <div class="media-thumbnail">
                            <i class="fas fa-file-alt"></i>
                        </div>
                        <div class="media-info">
                            <div class="media-title">${subtitle.name}</div>
                            <div class="media-meta">${subtitle.language} | ${subtitle.lines} lines</div>
                        </div>
                    `;
                    
                    // 클릭 이벤트
                    item.addEventListener('click', () => {
                        this.viewSubtitle(subtitle.id);
                    });
                    
                    subtitlesList.appendChild(item);
                });
            }
        } catch (error) {
            console.error('자막 목록 가져오기 오류:', error);
        }
    },
    
    async viewSubtitle(subtitleId) {
        try {
            // 자막 상세 정보 가져오기
            const subtitle = await api.get(`/subtitles/${subtitleId}`);
            
            // 모달에 데이터 표시
            const subtitleModal = document.getElementById('subtitle-view-modal');
            if (subtitleModal) {
                const titleElement = subtitleModal.querySelector('.modal-title');
                const contentElement = subtitleModal.querySelector('.subtitle-content');
                
                if (titleElement) titleElement.textContent = subtitle.name;
                if (contentElement) {
                    // 자막 내용 표시
                    const subtitleHtml = subtitle.content.map(line => {
                        return `
                            <div class="subtitle-line">
                                <div class="subtitle-time">${line.start} --> ${line.end}</div>
                                <div class="subtitle-text">${line.text}</div>
                                ${line.translation ? `<div class="subtitle-translation">${line.translation}</div>` : ''}
                            </div>
                        `;
                    }).join('');
                    
                    contentElement.innerHTML = subtitleHtml;
                }
                
                // 모달 표시
                modal.show('subtitle-view-modal');
            }
        } catch (error) {
            console.error('자막 상세정보 가져오기 오류:', error);
            modal.show('error-modal', {
                message: '자막 정보를 가져오는 중 오류가 발생했습니다: ' + error.message
            });
        }
    }
};

// 반복 영상 생성 기능
const repeatVideoGenerator = {
    init() {
        const repeatForm = document.getElementById('repeat-form');
        if (repeatForm) {
            repeatForm.addEventListener('submit', this.handleRepeatSubmit.bind(this));
        }
        
        // 클립 목록 로드
        this.loadClipOptions();
        
        // 자막 목록 로드
        this.loadSubtitleOptions();
    },
    
    async loadClipOptions() {
        try {
            const clips = await api.get('/videos/clips');
            const clipSelect = document.getElementById('clip-select');
            
            if (clipSelect) {
                // 옵션 초기화
                clipSelect.innerHTML = '<option value="">선택하세요</option>';
                
                // 옵션 추가
                clips.forEach(clip => {
                    const option = document.createElement('option');
                    option.value = clip.id;
                    option.textContent = clip.name;
                    clipSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('클립 목록 가져오기 오류:', error);
        }
    },
    
    async loadSubtitleOptions() {
        try {
            const subtitles = await api.get('/subtitles/list');
            const subtitleSelect = document.getElementById('subtitle-select');
            
            if (subtitleSelect) {
                // 옵션 초기화
                subtitleSelect.innerHTML = '<option value="">선택하세요</option>';
                
                // 옵션 추가
                subtitles.forEach(subtitle => {
                    const option = document.createElement('option');
                    option.value = subtitle.id;
                    option.textContent = subtitle.name;
                    subtitleSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('자막 목록 가져오기 오류:', error);
        }
    },
    
    async handleRepeatSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        // 진행 상태 표시
        const progressBar = document.querySelector('.progress-fill');
        const statusText = document.querySelector('.task-status');
        
        try {
            // 폼 데이터를 객체로 변환
            const data = {
                clip_id: formData.get('clip_id'),
                subtitle_id: formData.get('subtitle_id'),
                repeat_count: parseInt(formData.get('repeat_count')) || 3,
                subtitle_mode: formData.getAll('subtitle_mode') || ['no_subtitle', 'en', 'en_ko'],
                output_name: formData.get('output_name') || `repeat_${Date.now()}.mp4`,
                level: formData.get('level') || 'intermediate'
            };
            
            // 진행 상태 초기화
            if (progressBar) progressBar.style.width = '0%';
            if (statusText) statusText.textContent = '반복 영상 생성 준비 중...';
            
            // 반복 영상 생성 API 호출
            const response = await api.post('/videos/generate-repeat', data);
            
            // 작업 ID 가져오기
            const taskId = response.task_id;
            
            // 진행 상태 폴링 시작
            this.pollTaskStatus(taskId, progressBar, statusText);
            
        } catch (error) {
            console.error('반복 영상 생성 오류:', error);
            modal.show('error-modal', {
                message: '반복 영상 생성 중 오류가 발생했습니다: ' + error.message
            });
        }
    },
    
    async pollTaskStatus(taskId, progressBar, statusText) {
        try {
            const response = await api.get(`/videos/status/${taskId}`);
            
            // 진행 상태 업데이트
            if (progressBar) progressBar.style.width = `${response.progress}%`;
            if (statusText) statusText.textContent = response.status;
            
            if (response.state === 'PENDING' || response.state === 'PROGRESS') {
                // 계속 폴링
                setTimeout(() => {
                    this.pollTaskStatus(taskId, progressBar, statusText);
                }, 1000);
            } else if (response.state === 'SUCCESS') {
                // 성공 완료
                if (progressBar) progressBar.style.width = '100%';
                if (statusText) statusText.textContent = '완료!';
                
                modal.show('success-modal', {
                    message: '반복 영상이 성공적으로 생성되었습니다.'
                });
                
                // 필요한 경우 파일 목록 새로고침
                this.loadOutputVideos();
                
            } else if (response.state === 'FAILURE') {
                // 실패
                if (statusText) statusText.textContent = '실패: ' + response.error;
                modal.show('error-modal', {
                    message: '반복 영상 생성에 실패했습니다: ' + response.error
                });
            }
        } catch (error) {
            console.error('상태 확인 오류:', error);
            if (statusText) statusText.textContent = '상태 확인 중 오류 발생';
        }
    },
    
    async loadOutputVideos() {
        try {
            const videos = await api.get('/videos/outputs');
            const videosList = document.getElementById('output-videos-list');
            
            if (videosList) {
                // 목록 초기화
                videosList.innerHTML = '';
                
                // 새로운 항목 추가
                videos.forEach(video => {
                    const item = document.createElement('div');
                    item.className = 'media-item';
                    
                    item.innerHTML = `
                        <div class="media-thumbnail">
                            <i class="fas fa-file-video"></i>
                        </div>
                        <div class="media-info">
                            <div class="media-title">${video.name}</div>
                            <div class="media-meta">${video.duration} | ${video.size}</div>
                        </div>
                    `;
                    
                    // 클릭 이벤트 - 비디오 재생
                    item.addEventListener('click', () => {
                        this.playOutputVideo(video);
                    });
                    
                    videosList.appendChild(item);
                });
            }
        } catch (error) {
            console.error('출력 비디오 목록 가져오기 오류:', error);
        }
    },
    
    playOutputVideo(video) {
        // 비디오 플레이어 모달 표시
        const playerModal = document.getElementById('video-player-modal');
        
        if (playerModal) {
            // 비디오 설정
            const videoElement = playerModal.querySelector('video');
            const titleElement = playerModal.querySelector('.modal-title');
            
            if (videoElement) {
                videoElement.src = `/api/videos/stream/${encodeURIComponent(video.path)}`;
                videoElement.poster = video.thumbnail || '';
            }
            
            if (titleElement) {
                titleElement.textContent = video.name;
            }
            
            // 모달 표시
            modal.show('video-player-modal', {
                onClose: () => {
                    // 모달 닫을 때 비디오 정지
                    if (videoElement) {
                        videoElement.pause();
                    }
                }
            });
        }
    }
};

// 최종 영상 병합 기능
const finalVideoMerger = {
    init() {
        const mergeForm = document.getElementById('merge-form');
        if (mergeForm) {
            mergeForm.addEventListener('submit', this.handleMergeSubmit.bind(this));
        }
        
        // 출력 비디오 목록 로드
        this.loadOutputOptions();
    },
    
    async loadOutputOptions() {
        try {
            const videos = await api.get('/videos/outputs');
            const videoSelect = document.getElementById('output-video-select');
            
            if (videoSelect) {
                // 옵션 초기화
                videoSelect.innerHTML = '<option value="">선택하세요</option>';
                
                // 옵션 추가
                videos.forEach(video => {
                    const option = document.createElement('option');
                    option.value = video.id;
                    option.textContent = video.name;
                    videoSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('출력 비디오 목록 가져오기 오류:', error);
        }
    },
    
    async handleMergeSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        
        // 진행 상태 표시
        const progressBar = document.querySelector('.progress-fill');
        const statusText = document.querySelector('.task-status');
        
        try {
            // 폼 데이터를 객체로 변환
            const data = {
                output_video_id: formData.get('output_video_id'),
                title: formData.get('title'),
                watermark: formData.get('watermark'),
                add_intro: formData.get('add_intro') === 'on',
                add_outro: formData.get('add_outro') === 'on',
                output_name: formData.get('output_name') || `final_${Date.now()}.mp4`,
                quality: formData.get('quality') || 'high'
            };
            
            // 진행 상태 초기화
            if (progressBar) progressBar.style.width = '0%';
            if (statusText) statusText.textContent = '최종 영상 병합 준비 중...';
            
            // 병합 API 호출
            const response = await api.post('/videos/merge-final', data);
            
            // 작업 ID 가져오기
            const taskId = response.task_id;
            
            // 진행 상태 폴링 시작
            this.pollTaskStatus(taskId, progressBar, statusText);
            
        } catch (error) {
            console.error('최종 영상 병합 오류:', error);
            modal.show('error-modal', {
                message: '최종 영상 병합 중 오류가 발생했습니다: ' + error.message
            });
        }
    },
    
    async pollTaskStatus(taskId, progressBar, statusText) {
        try {
            const response = await api.get(`/videos/status/${taskId}`);
            
            // 진행 상태 업데이트
            if (progressBar) progressBar.style.width = `${response.progress}%`;
            if (statusText) statusText.textContent = response.status;
            
            if (response.state === 'PENDING' || response.state === 'PROGRESS') {
                // 계속 폴링
                setTimeout(() => {
                    this.pollTaskStatus(taskId, progressBar, statusText);
                }, 1000);
            } else if (response.state === 'SUCCESS') {
                // 성공 완료
                if (progressBar) progressBar.style.width = '100%';
                if (statusText) statusText.textContent = '완료!';
                
                modal.show('success-modal', {
                    message: '최종 영상이 성공적으로 생성되었습니다.'
                });
                
                // 필요한 경우 파일 목록 새로고침
                this.loadFinalVideos();
                
            } else if (response.state === 'FAILURE') {
                // 실패
                if (statusText) statusText.textContent = '실패: ' + response.error;
                modal.show('error-modal', {
                    message: '최종 영상 생성에 실패했습니다: ' + response.error
                });
            }
        } catch (error) {
            console.error('상태 확인 오류:', error);
            if (statusText) statusText.textContent = '상태 확인 중 오류 발생';
        }
    },
    
    async loadFinalVideos() {
        try {
            const videos = await api.get('/videos/finals');
            const videosList = document.getElementById('final-videos-list');
            
            if (videosList) {
                // 목록 초기화
                videosList.innerHTML = '';
                
                // 새로운 항목 추가
                videos.forEach(video => {
                    const item = document.createElement('div');
                    item.className = 'media-item';
                    
                    item.innerHTML = `
                        <div class="media-thumbnail">
                            <i class="fas fa-file-video"></i>
                        </div>
                        <div class="media-info">
                            <div class="media-title">${video.name}</div>
                            <div class="media-meta">${video.duration} | ${video.size}</div>
                        </div>
                    `;
                    
                    // 클릭 이벤트 - 비디오 재생
                    item.addEventListener('click', () => {
                        this.playFinalVideo(video);
                    });
                    
                    videosList.appendChild(item);
                });
            }
        } catch (error) {
            console.error('최종 비디오 목록 가져오기 오류:', error);
        }
    },
    
    playFinalVideo(video) {
        // 비디오 플레이어 모달 표시
        const playerModal = document.getElementById('video-player-modal');
        
        if (playerModal) {
            // 비디오 설정
            const videoElement = playerModal.querySelector('video');
            const titleElement = playerModal.querySelector('.modal-title');
            
            if (videoElement) {
                videoElement.src = `/api/videos/stream/${encodeURIComponent(video.path)}`;
                videoElement.poster = video.thumbnail || '';
            }
            
            if (titleElement) {
                titleElement.textContent = video.name;
            }
            
            // 모달 표시
            modal.show('video-player-modal', {
                onClose: () => {
                    // 모달 닫을 때 비디오 정지
                    if (videoElement) {
                        videoElement.pause();
                    }
                }
            });
        }
    }
};

// 발음 연습 기능
const pronunciationPractice = {
    mediaRecorder: null,
    audioChunks: [],
    isRecording: false,
    currentAudioBlob: null,
    selectedClipId: null,
    
    init() {
        // 발음 연습 페이지 요소들
        const recordButton = document.getElementById('record-button');
        const stopButton = document.getElementById('stop-button');
        const playbackButton = document.getElementById('playback-button');
        const clipSelect = document.getElementById('pronunciation-clip-select');
        const compareButton = document.getElementById('compare-button');
        
        // 녹음 버튼 이벤트
        if (recordButton) {
            recordButton.addEventListener('click', this.startRecording.bind(this));
        }
        
        // 정지 버튼 이벤트
        if (stopButton) {
            stopButton.addEventListener('click', this.stopRecording.bind(this));
        }
        
        // 재생 버튼 이벤트
        if (playbackButton) {
            playbackButton.addEventListener('click', this.playRecording.bind(this));
        }
        
        // 비교 버튼 이벤트
        if (compareButton) {
            compareButton.addEventListener('click', this.compareAudio.bind(this));
        }
        
        // 클립 선택시 이벤트
        if (clipSelect) {
            clipSelect.addEventListener('change', this.loadSelectedClip.bind(this));
            
            // 초기 클립 목록 로딩
            this.loadClipOptions();
        }
        
        // 발음 연습 결과 표시 영역 초기화
        this.resetPracticeResults();
    },
    
    async loadClipOptions() {
        try {
            const clips = await api.get('/videos/clips');
            const clipSelect = document.getElementById('pronunciation-clip-select');
            
            if (clipSelect) {
                // 옵션 초기화
                clipSelect.innerHTML = '<option value="">클립을 선택하세요</option>';
                
                // 옵션 추가
                clips.forEach(clip => {
                    const option = document.createElement('option');
                    option.value = clip.id;
                    option.textContent = clip.name;
                    clipSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('클립 목록 가져오기 오류:', error);
        }
    },
    
    async loadSelectedClip() {
        const clipSelect = document.getElementById('pronunciation-clip-select');
        const videoPlayer = document.getElementById('pronunciation-video');
        const subtitleContainer = document.getElementById('pronunciation-subtitles');
        
        if (!clipSelect || !videoPlayer) return;
        
        try {
            this.selectedClipId = clipSelect.value;
            
            // 선택된 클립이 없으면 리턴
            if (!this.selectedClipId) {
                videoPlayer.src = '';
                if (subtitleContainer) subtitleContainer.innerHTML = '';
                return;
            }
            
            // 클립 정보 가져오기
            const clipInfo = await api.get(`/videos/clips/${this.selectedClipId}`);
            
            // 비디오 플레이어 설정
            videoPlayer.src = `/api/videos/stream/${encodeURIComponent(clipInfo.path)}`;
            videoPlayer.controls = true;
            
            // 자막 로드
            if (subtitleContainer && clipInfo.subtitle_id) {
                const subtitles = await api.get(`/subtitles/${clipInfo.subtitle_id}`);
                
                // 자막 표시
                this.displaySubtitles(subtitles.content);
            } else if (subtitleContainer) {
                subtitleContainer.innerHTML = '<p>이 클립에는 자막이 없습니다.</p>';
            }
            
            // 발음 연습 결과 초기화
            this.resetPracticeResults();
            
        } catch (error) {
            console.error('클립 로드 오류:', error);
            modal.show('error-modal', {
                message: '클립을 로드하는 중 오류가 발생했습니다: ' + error.message
            });
        }
    },
    
    displaySubtitles(subtitles) {
        const container = document.getElementById('pronunciation-subtitles');
        if (!container) return;
        
        // 자막 HTML 생성
        const subtitleHtml = subtitles.map(line => {
            return `
                <div class="subtitle-line" data-start="${line.start_seconds}" data-end="${line.end_seconds}">
                    <div class="subtitle-time">${line.start} - ${line.end}</div>
                    <div class="subtitle-text">${line.text}</div>
                    ${line.translation ? `<div class="subtitle-translation">${line.translation}</div>` : ''}
                </div>
            `;
        }).join('');
        
        container.innerHTML = subtitleHtml;
        
        // 비디오 시간 업데이트시 자막 활성화
        const videoPlayer = document.getElementById('pronunciation-video');
        if (videoPlayer) {
            videoPlayer.ontimeupdate = () => {
                this.highlightActiveSubtitle(videoPlayer.currentTime);
            };
        }
    },
    
    highlightActiveSubtitle(currentTime) {
        const subtitleLines = document.querySelectorAll('#pronunciation-subtitles .subtitle-line');
        
        subtitleLines.forEach(line => {
            const start = parseFloat(line.dataset.start);
            const end = parseFloat(line.dataset.end);
            
            if (currentTime >= start && currentTime <= end) {
                line.classList.add('active');
            } else {
                line.classList.remove('active');
            }
        });
    },
    
    async startRecording() {
        try {
            // 발음 연습 결과 초기화
            this.resetPracticeResults();
            
            // 사용자 미디어 요청
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // 녹음 상태 표시
            this.updateRecordingStatus(true);
            
            // MediaRecorder 설정
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];
            
            // 데이터 처리
            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };
            
            // 녹음 완료시 처리
            this.mediaRecorder.onstop = () => {
                // Blob 생성
                this.currentAudioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                
                // 오디오 플레이어 업데이트
                this.updateAudioPlayer();
                
                // 녹음 상태 표시 업데이트
                this.updateRecordingStatus(false);
                
                // 스트림 정지
                stream.getTracks().forEach(track => track.stop());
            };
            
            // 녹음 시작
            this.mediaRecorder.start();
            
        } catch (error) {
            console.error('녹음 시작 오류:', error);
            modal.show('error-modal', {
                message: '녹음을 시작할 수 없습니다. 마이크 접근 권한을 확인해주세요.'
            });
        }
    },
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.updateRecordingStatus(false);
        }
    },
    
    updateRecordingStatus(isRecording) {
        this.isRecording = isRecording;
        
        // 버튼 상태 업데이트
        const recordButton = document.getElementById('record-button');
        const stopButton = document.getElementById('stop-button');
        const recordingIndicator = document.getElementById('recording-indicator');
        
        if (recordButton) {
            recordButton.disabled = isRecording;
        }
        
        if (stopButton) {
            stopButton.disabled = !isRecording;
        }
        
        if (recordingIndicator) {
            if (isRecording) {
                recordingIndicator.classList.add('active');
                recordingIndicator.textContent = '녹음 중...';
            } else {
                recordingIndicator.classList.remove('active');
                recordingIndicator.textContent = '준비됨';
            }
        }
    },
    
    updateAudioPlayer() {
        const audioPlayer = document.getElementById('recorded-audio');
        const playbackButton = document.getElementById('playback-button');
        const compareButton = document.getElementById('compare-button');
        
        if (audioPlayer && this.currentAudioBlob) {
            // 오디오 URL 생성
            const audioURL = URL.createObjectURL(this.currentAudioBlob);
            audioPlayer.src = audioURL;
            audioPlayer.controls = true;
            
            // 버튼 활성화
            if (playbackButton) playbackButton.disabled = false;
            if (compareButton) compareButton.disabled = false;
        }
    },
    
    playRecording() {
        const audioPlayer = document.getElementById('recorded-audio');
        if (audioPlayer && audioPlayer.src) {
            audioPlayer.play();
        }
    },
    
    async compareAudio() {
        if (!this.currentAudioBlob || !this.selectedClipId) {
            modal.show('error-modal', {
                message: '비교를 위해 클립을 선택하고 음성을 녹음해주세요.'
            });
            return;
        }
        
        try {
            // 로딩 상태 표시
            const compareResults = document.getElementById('pronunciation-results');
            if (compareResults) {
                compareResults.innerHTML = '<div class="loading">발음 분석 중...</div>';
            }
            
            // FormData 생성
            const formData = new FormData();
            formData.append('audio_file', this.currentAudioBlob);
            formData.append('clip_id', this.selectedClipId);
            
            // API 호출
            const response = await fetch(`${API_BASE_URL}/pronunciation/compare`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`API 요청 실패: ${response.status}`);
            }
            
            const result = await response.json();
            
            // 결과 표시
            this.displayPronunciationResults(result);
            
        } catch (error) {
            console.error('발음 비교 오류:', error);
            modal.show('error-modal', {
                message: '발음 비교 중 오류가 발생했습니다: ' + error.message
            });
            
            // 결과 영역 초기화
            this.resetPracticeResults();
        }
    },
    
    displayPronunciationResults(results) {
        const resultsContainer = document.getElementById('pronunciation-results');
        if (!resultsContainer) return;
        
        // 전체 점수 계산 (0-100점 척도)
        const overallScore = Math.round(results.overall_score * 100);
        
        // 결과 HTML 생성
        let html = `
            <div class="results-card">
                <h3>발음 평가 결과</h3>
                <div class="score-display">
                    <div class="score-circle ${this.getScoreClass(overallScore)}">
                        <span class="score-value">${overallScore}</span>
                    </div>
                    <div class="score-label">종합 점수</div>
                </div>
                
                <div class="score-details">
                    <div class="detail-item">
                        <span class="detail-label">정확성:</span>
                        <span class="detail-value ${this.getScoreClass(results.accuracy * 100)}">${Math.round(results.accuracy * 100)}%</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">유창성:</span>
                        <span class="detail-value ${this.getScoreClass(results.fluency * 100)}">${Math.round(results.fluency * 100)}%</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">발음:</span>
                        <span class="detail-value ${this.getScoreClass(results.pronunciation * 100)}">${Math.round(results.pronunciation * 100)}%</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">속도:</span>
                        <span class="detail-value ${this.getScoreClass(results.speed_match * 100)}">${Math.round(results.speed_match * 100)}%</span>
                    </div>
                </div>
                
                <h4>단어별 평가</h4>
                <div class="word-analysis">
        `;
        
        // 단어별 평가
        if (results.word_scores && results.word_scores.length > 0) {
            html += '<div class="word-scores">';
            
            results.word_scores.forEach(word => {
                const wordScore = Math.round(word.score * 100);
                html += `<span class="word ${this.getScoreClass(wordScore)}" 
                               title="${word.word}: ${wordScore}점">${word.word}</span>`;
            });
            
            html += '</div>';
        } else {
            html += '<p>단어별 평가를 사용할 수 없습니다.</p>';
        }
        
        // 개선 제안
        html += `
                </div>
                
                <h4>개선 제안</h4>
                <div class="improvement-suggestions">
        `;
        
        if (results.suggestions && results.suggestions.length > 0) {
            html += '<ul class="suggestions-list">';
            
            results.suggestions.forEach(suggestion => {
                html += `<li>${suggestion}</li>`;
            });
            
            html += '</ul>';
        } else {
            html += '<p>개선 제안이 없습니다.</p>';
        }
        
        html += `
                </div>
            </div>
        `;
        
        // 결과 표시
        resultsContainer.innerHTML = html;
    },
    
    getScoreClass(score) {
        if (score >= 90) return 'excellent';
        if (score >= 70) return 'good';
        if (score >= 50) return 'average';
        return 'needs-improvement';
    },
    
    resetPracticeResults() {
        const resultsContainer = document.getElementById('pronunciation-results');
        if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="placeholder">발음을 녹음한 뒤 비교하면 결과가 여기에 표시됩니다.</div>';
        }
        
        const audioPlayer = document.getElementById('recorded-audio');
        const playbackButton = document.getElementById('playback-button');
        const compareButton = document.getElementById('compare-button');
        
        if (audioPlayer) audioPlayer.src = '';
        if (playbackButton) playbackButton.disabled = true;
        if (compareButton) compareButton.disabled = true;
    }
};

// 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 페이지 관리자 초기화
    pageManager.init();
    
    // 기능별 초기화
    videoExtractor.init();
    subtitleManager.init();
    repeatVideoGenerator.init();
    finalVideoMerger.init();
    pronunciationPractice.init();
});