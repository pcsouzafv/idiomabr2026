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
  register: (data: { email: string; name: string; password: string; phone_number: string }) =>
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
  
  updateMe: (data: { name?: string; daily_goal?: number; phone_number?: string }) =>
    api.put('/api/auth/me', data),

  changePassword: (data: { current_password: string; new_password: string }) =>
    api.post('/api/auth/change-password', data),

  forgotPassword: (data: { email: string }) =>
    api.post('/api/auth/forgot-password', data),

  resetPassword: (data: { token: string; new_password: string }) =>
    api.post('/api/auth/reset-password', data),
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

  startSentenceBuilder: (params?: { num_sentences?: number; level?: string }) =>
    api.post('/api/games/sentence-builder/start', null, { params }),
  submitSentenceBuilder: (data: { session_id: string; answers: { item_id: string; tokens: string[] }[]; time_spent?: number }) =>
    api.post('/api/games/sentence-builder/submit', data),

  startGrammarBuilder: (params?: { num_sentences?: number; tense?: string; level?: number }) =>
    api.post('/api/games/grammar-builder/start', null, { params }),
  submitGrammarBuilder: (data: { session_id: string; answers: { item_id: string; tokens: string[] }[]; time_spent?: number }) =>
    api.post('/api/games/grammar-builder/submit', data),
};

export const statsApi = {
  getOverview: () => api.get('/api/stats/me'),
  getAllAchievements: () => api.get('/api/stats/achievements'),
  getMyAchievements: () => api.get('/api/stats/achievements/me'),
  getLeaderboard: (params?: { limit?: number }) =>
    api.get('/api/stats/leaderboard', { params }),
  getDailyChallenge: () => api.get('/api/stats/daily-challenge'),
};

// Exams AI (mini-simulados + análise)
export const examsAiApi = {
  generate: (data: {
    exam: string;
    skill?: string;
    num_questions?: number;
    level?: string;
  }) => api.post('/api/exams/ai/generate', data),

  analyze: (data: {
    exam: string;
    skill?: string;
    level?: string;
    questions: Array<{ id: string; type: string; prompt: string; options?: string[] | null }>;
    answers: Array<{ id: string; answer: string }>;
  }) => api.post('/api/exams/ai/analyze', data),
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

// Conversation (DeepSeek chat + OpenAI TTS)
export const conversationApi = {
  // Text-to-Speech
  textToSpeech: (data: {
    text: string;
    voice_id?: string;
    model_id?: string;
    voice_settings?: any;
  }) => api.post('/api/conversation/tts', data, { responseType: 'blob' }),

  getVoices: () => api.get('/api/conversation/voices'),

  // Conversational AI
  startConversation: (data?: {
    system_prompt?: string;
    agent_id?: string;
    initial_message?: string;
  }) => api.post('/api/conversation/start', data || {}),

  startLesson: (data: {
    questions: string[];
    native_language?: string;
    target_language?: string;
    topic?: string;
    num_questions?: number;
  }) => api.post('/api/conversation/lesson/start', data),

  generateLesson: (data: { topic: string; num_questions?: number }) =>
    api.post('/api/conversation/lesson/generate', data),

  sendMessage: (conversationId: string, data: { message: string }) =>
    api.post(`/api/conversation/${conversationId}/message`, data),

  sendLessonMessage: (conversationId: string, data: { message: string }) =>
    api.post(`/api/conversation/lesson/${conversationId}/message`, data),

  analyzePronunciation: (data: FormData) =>
    api.post('/api/conversation/pronunciation', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  transcribeAudio: (data: FormData) =>
    api.post('/api/conversation/stt', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  getHistory: (conversationId: string) =>
    api.get(`/api/conversation/${conversationId}/history`),

  endConversation: (conversationId: string, data?: { feedback?: string }) =>
    api.post(`/api/conversation/${conversationId}/end`, data || {}),

  listActiveConversations: () => api.get('/api/conversation/active/list'),

  listLessonAttempts: (params?: { limit?: number }) =>
    api.get('/api/conversation/lesson/attempts', { params }),

  getLessonAttemptDetails: (attemptId: number) =>
    api.get(`/api/conversation/lesson/attempts/${attemptId}`),
};

export default api;
