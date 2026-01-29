import { create } from 'zustand';
import { authApi, studyApi } from '@/lib/api';

interface User {
  id: number;
  email: string;
  phone_number?: string | null;
  name: string;
  daily_goal: number;
  current_streak: number;
  last_study_date: string | null;
  is_admin?: boolean;
}

interface ProgressStats {
  total_words_studied: number;
  total_words_learned: number;
  words_studied_today: number;
  current_streak: number;
  words_to_review_today: number;
  new_words_available: number;
  daily_goal: number;
  daily_goal_progress: number;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  stats: ProgressStats | null;
  
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string, phoneNumber: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  fetchStats: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('token') : null,
  isLoading: true,
  stats: null,
  
  setUser: (user) => set({ user }),
  
  setToken: (token) => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
    set({ token });
  },
  
  login: async (email: string, password: string) => {
    const response = await authApi.login({ username: email, password });
    const { access_token } = response.data;
    
    localStorage.setItem('token', access_token);
    set({ token: access_token });
    
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data, isLoading: false });
  },
  
  register: async (email: string, name: string, password: string, phoneNumber: string) => {
    await authApi.register({ email, name, password, phone_number: phoneNumber });
    // Após registro, fazer login automaticamente
    const loginResponse = await authApi.login({ username: email, password });
    const { access_token } = loginResponse.data;
    
    localStorage.setItem('token', access_token);
    set({ token: access_token });
    
    const userResponse = await authApi.getMe();
    set({ user: userResponse.data, isLoading: false });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, stats: null });
  },
  
  fetchUser: async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        set({ isLoading: false });
        return;
      }
      
      const response = await authApi.getMe();
      set({ user: response.data, isLoading: false });
    } catch {
      localStorage.removeItem('token');
      set({ user: null, token: null, isLoading: false });
    }
  },
  
  fetchStats: async () => {
    try {
      const response = await studyApi.getStats();
      set({ stats: response.data });
    } catch (error) {
      console.error('Erro ao buscar estatísticas:', error);
    }
  },
}));
