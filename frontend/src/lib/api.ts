import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Interceptor para tratar erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  register: (data: { email: string; name: string; password: string }) =>
    api.post('/api/auth/register', data),
  
  login: (data: { username: string; password: string }) => {
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);
    return api.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
  
  getMe: () => api.get('/api/auth/me'),
  
  updateMe: (data: { name?: string; daily_goal?: number }) =>
    api.put('/api/auth/me', data),
};

// Words
export const wordsApi = {
  getWords: (params?: {
    search?: string;
    level?: string;
    tags?: string;
    page?: number;
    per_page?: number;
  }) => api.get('/api/words', { params }),
  
  getWord: (id: number) => api.get(`/api/words/${id}`),
  
  getLevels: () => api.get('/api/words/levels/list'),
  
  getTags: () => api.get('/api/words/tags/list'),
};

// Study
export const studyApi = {
  getSession: (params?: { size?: number; direction?: string; mode?: string; level?: string }) =>
    api.get('/api/study/session', { params }),
  
  submitReview: (data: { word_id: number; difficulty: string; direction: string }) =>
    api.post('/api/study/review', data),
  
  getStats: () => api.get('/api/study/stats'),
  
  getHistory: (days?: number) =>
    api.get('/api/study/history', { params: { days } }),
};

export const gamesApi = {
  startQuiz: (params?: { num_questions?: number; level?: string }) =>
    api.post('/api/games/quiz/start', null, { params }),
  submitQuiz: (data: { session_id: string; answers: number[]; time_spent?: number }) =>
    api.post('/api/games/quiz/submit', data),
  startHangman: (params?: { level?: string }) =>
    api.post('/api/games/hangman/start', null, { params }),
  guessHangman: (sessionId: string, data: { letter: string }) =>
    api.post(`/api/games/hangman/${sessionId}/guess`, data),
  startMatching: (params?: { num_pairs?: number; level?: string }) =>
    api.post('/api/games/matching/start', null, { params }),
  submitMatching: (data: { session_id: string; time_spent: number; moves: number; completed: boolean }) =>
    api.post('/api/games/matching/submit', data),
  startDictation: (params?: { num_words?: number; level?: string }) =>
    api.post('/api/games/dictation/start', null, { params }),
  submitDictation: (data: { session_id: string; answers: { word_id: number; answer: string }[]; time_spent?: number }) =>
    api.post('/api/games/dictation/submit', data),
};

export const statsApi = {
  getOverview: () => api.get('/api/stats/me'),
  getAllAchievements: () => api.get('/api/stats/achievements'),
  getMyAchievements: () => api.get('/api/stats/achievements/me'),
  getLeaderboard: (params?: { limit?: number }) =>
    api.get('/api/stats/leaderboard', { params }),
  getDailyChallenge: () => api.get('/api/stats/daily-challenge'),
};

// Videos
export const videosApi = {
  getVideos: (params?: {
    page?: number;
    per_page?: number;
    level?: string;
    category?: string;
    search?: string;
    featured_only?: boolean;
    active_only?: boolean;
  }) => api.get('/api/videos', { params }),

  getVideo: (id: number) => api.get(`/api/videos/${id}`),

  createVideo: (data: {
    title: string;
    description?: string;
    youtube_url: string;
    level?: string;
    category?: string;
    tags?: string;
    duration?: number;
    is_active?: boolean;
    is_featured?: boolean;
    order_index?: number;
  }) => api.post('/api/videos', data),

  updateVideo: (id: number, data: Partial<{
    title: string;
    description: string;
    youtube_url: string;
    level: string;
    category: string;
    tags: string;
    duration: number;
    is_active: boolean;
    is_featured: boolean;
    order_index: number;
  }>) => api.put(`/api/videos/${id}`, data),

  deleteVideo: (id: number) => api.delete(`/api/videos/${id}`),

  updateProgress: (data: {
    video_id: number;
    watched_duration: number;
    completion_percentage: number;
  }) => api.post('/api/videos/progress', data),

  getMyProgress: () => api.get('/api/videos/progress/me'),

  getCategories: () => api.get('/api/videos/categories/list'),

  getLevels: () => api.get('/api/videos/levels/list'),
};

export default api;
