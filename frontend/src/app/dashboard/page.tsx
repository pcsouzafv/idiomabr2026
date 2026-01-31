'use client';

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import {
  BookOpen,
  FileText,
  LogOut,
  Play,
  Search,
  Flame,
  Target,
  TrendingUp,
  Award,
  Gamepad2,
  Trophy,
  Star,
  Brain,
  Shield,
  GraduationCap,
  MessageCircle,
} from 'lucide-react';

export default function DashboardPage() {
  const { user, stats, isLoading, fetchUser, fetchStats, logout } = useAuthStore();
  const router = useRouter();
  const progressBarRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  useEffect(() => {
    if (user) {
      fetchStats();
    }
  }, [user, fetchStats]);

  useEffect(() => {
    const banner = Array.from(document.querySelectorAll('div')).find(
      (div) =>
        div.textContent?.includes('Telefone para envio de lições') &&
        div.querySelector('input[type="tel"]') &&
        div.querySelector('button')
    );
    if (banner) {
      banner.remove();
    }
  }, []);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const progressPercentage = stats?.daily_goal_progress || 0;

  useEffect(() => {
    if (progressBarRef.current) {
      progressBarRef.current.style.width = `${Math.min(100, progressPercentage)}%`;
    }
  }, [progressPercentage]);

  if (isLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50 transition-colors">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary-600 dark:text-primary-400" />
            <span className="text-xl font-bold text-gray-900 dark:text-white">IdiomasBR</span>
          </Link>

          <div className="flex items-center gap-4">
            <span className="text-gray-600 dark:text-gray-300">Olá, {user.name.split(' ')[0]}</span>
            <ThemeToggle />
            <button
              onClick={handleLogout}
              className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
              title="Sair"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Welcome & Streak */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Olá, {user.name}! 👋
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Pronto para aprender mais palavras hoje?
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {/* Streak */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                <Flame className="h-6 w-6 text-orange-500 dark:text-orange-400 streak-fire" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats?.current_streak || 0}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">dias seguidos</p>
              </div>
            </div>
          </div>

          {/* Words Studied */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                <Award className="h-6 w-6 text-green-500 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats?.total_words_studied || 0}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">palavras estudadas</p>
              </div>
            </div>
          </div>

          {/* Words Mastered */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
                <Trophy className="h-6 w-6 text-yellow-500 dark:text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats?.total_words_learned || 0}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">palavras dominadas</p>
              </div>
            </div>
          </div>

          {/* To Review Today */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <TrendingUp className="h-6 w-6 text-blue-500 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats?.words_to_review_today || 0}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">para revisar</p>
              </div>
            </div>
          </div>

          {/* Studied Today */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                <Target className="h-6 w-6 text-purple-500 dark:text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats?.words_studied_today || 0}/{stats?.daily_goal || 20}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">meta do dia</p>
              </div>
            </div>
          </div>
        </div>

        {/* Daily Goal Progress */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm mb-8 transition-colors">
          <div className="flex justify-between items-center mb-3">
            <span className="font-semibold text-gray-700 dark:text-gray-300">Progresso do dia</span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {stats?.words_studied_today || 0} de {stats?.daily_goal || 20} palavras
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4">
            <div
              ref={progressBarRef}
              className="bg-gradient-to-r from-primary-500 to-primary-600 dark:from-primary-400 dark:to-primary-500 h-4 rounded-full transition-all duration-500 progress-bar"
            ></div>
          </div>
          {progressPercentage >= 100 && (
            <p className="mt-2 text-green-600 dark:text-green-400 font-semibold text-center">
              🎉 Parabéns! Você atingiu sua meta de hoje!
            </p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link
            href="/study"
            className="bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Play className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Estudar Agora</h3>
                <p className="text-primary-100">
                  {(stats?.words_to_review_today || 0) > 0
                    ? `${stats?.words_to_review_today} palavras para revisar`
                    : 'Aprenda novas palavras'}
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/sentences"
            className="bg-gradient-to-r from-blue-500 to-cyan-600 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Brain className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Estudar Frases com IA</h3>
                <p className="text-blue-100">
                  Professor de IA personalizado
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/conversation"
            className="bg-gradient-to-r from-violet-500 to-purple-600 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <MessageCircle className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Conversação com IA 🎙️</h3>
                <p className="text-violet-100">
                  Pratique inglês falando com IA
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/challenges"
            className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Target className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Desafio Diário</h3>
                <p className="text-emerald-100">
                  Complete e ganhe XP extra!
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/games"
            className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Gamepad2 className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Jogos</h3>
                <p className="text-purple-100">
                  Quiz, Forca, Ditado e mais!
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/stats"
            className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Trophy className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Conquistas</h3>
                <p className="text-yellow-100">
                  XP, níveis e ranking
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/words"
            className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02] border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center">
                <Search className="h-8 w-8 text-gray-600 dark:text-gray-300" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Explorar Palavras</h3>
                <p className="text-gray-500 dark:text-gray-400">
                  {stats?.new_words_available || 5000}+ palavras disponíveis
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/achievements"
            className="bg-gradient-to-r from-pink-500 to-rose-500 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Star className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Minhas Conquistas</h3>
                <p className="text-pink-100">
                  Desbloqueie conquistas especiais
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/videos"
            className="bg-gradient-to-r from-red-500 to-pink-600 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                <Play className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Vídeo Aulas</h3>
                <p className="text-red-100">
                  Assista aulas em vídeo
                </p>
              </div>
            </div>
          </Link>

          <Link
            href="/texts"
            className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02] border border-gray-200 dark:border-gray-700"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-xl flex items-center justify-center">
                <FileText className="h-8 w-8 text-gray-600 dark:text-gray-300" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Leitura & Escrita</h3>
                <p className="text-gray-500 dark:text-gray-400">Pratique textos e receba correções</p>
              </div>
            </div>
          </Link>

          <Link
            href="/exams"
            className="bg-gradient-to-r from-slate-800 to-slate-950 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]"
          >
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-white/10 rounded-xl flex items-center justify-center">
                <GraduationCap className="h-8 w-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold">Preparação para Exames</h3>
                <p className="text-slate-200">IELTS, TOEFL, TOEIC e Cambridge</p>
              </div>
            </div>
          </Link>

          {/* Admin Panel - Só aparece para admins */}
          {user.is_admin && (
            <Link
              href="/admin"
              className="bg-gradient-to-r from-slate-700 to-slate-900 text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02] border-2 border-yellow-400"
            >
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 bg-yellow-400/20 rounded-xl flex items-center justify-center">
                  <Shield className="h-8 w-8 text-yellow-400" />
                </div>
                <div>
                  <h3 className="text-xl font-bold flex items-center gap-2">
                    Painel Admin
                    <span className="text-xs bg-yellow-400 text-slate-900 px-2 py-0.5 rounded-full font-bold">ADMIN</span>
                  </h3>
                  <p className="text-slate-300">
                    Gerenciar sistema
                  </p>
                </div>
              </div>
            </Link>
          )}
        </div>

        {/* Quick Tips */}
        <div className="mt-8 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-xl p-6 border border-amber-200 dark:border-amber-800">
          <h3 className="font-bold text-amber-800 dark:text-amber-300 mb-2">💡 Dica do dia</h3>
          <p className="text-amber-700 dark:text-amber-200">
            Estudar um pouco todos os dias é mais efetivo do que sessões longas esporádicas.
            Apenas 5-10 minutos diários fazem uma grande diferença!
          </p>
        </div>
      </main>
    </div>
  );
}
