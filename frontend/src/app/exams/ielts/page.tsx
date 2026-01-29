'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import ExamAiCoach from '../_components/ExamAiCoach';
import {
  BookOpen,
  ArrowLeft,
  LogOut,
  Globe,
  Headphones,
  FileText,
  PenLine,
  Mic,
  Play,
} from 'lucide-react';

export default function IELTSPage() {
  const { user, isLoading, fetchUser, logout } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50 transition-colors">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary-600 dark:text-primary-400" />
            <span className="text-xl font-bold text-gray-900 dark:text-white">IdiomasBR</span>
          </Link>

          <div className="flex items-center gap-4">
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

      <main className="container mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-6">
          <Link
            href="/exams"
            className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" />
            Exames
          </Link>
        </div>

        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <Globe className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">IELTS</h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Preparação para IELTS Academic/General Training, com foco em 4 habilidades (Reading, Listening, Writing e Speaking).
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
            <h2 className="font-bold text-gray-900 dark:text-white mb-2">Estrutura (visão geral)</h2>
            <ul className="text-gray-600 dark:text-gray-400 text-sm space-y-1">
              <li>• 4 partes: Listening, Reading, Writing e Speaking.</li>
              <li>• Duração total aproximada: ~2h45 (varia por modalidade).</li>
              <li>• Academic vs General Training: Reading e Writing mudam; Listening e Speaking são os mesmos.</li>
              <li>• Pontuação: Band score de 1 a 9.</li>
            </ul>
            <p className="mt-3 text-xs text-gray-500 dark:text-gray-500">
              Observação: detalhes podem mudar; confira sempre as páginas oficiais antes da prova.
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
            <h2 className="font-bold text-gray-900 dark:text-white mb-3">Praticar agora</h2>
            <div className="space-y-3">
              <Link href="/study" className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/40 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                <Play className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white text-sm">Vocabulário (flashcards)</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Band-building com repetição espaçada</div>
                </div>
              </Link>

              <Link href="/texts" className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/40 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                <FileText className="h-4 w-4 text-gray-700 dark:text-gray-200" />
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white text-sm">Reading + Writing</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Treine leitura e produção de texto</div>
                </div>
              </Link>

              <Link href="/sentences" className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-700/40 hover:bg-gray-100 dark:hover:bg-gray-700 transition">
                <Headphones className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <div>
                  <div className="font-semibold text-gray-900 dark:text-white text-sm">Listening + Speaking guiado</div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">Use IA para treinar respostas e pronúncia</div>
                </div>
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-6 grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm transition-colors">
            <div className="flex items-center gap-2 mb-2">
              <Headphones className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <h3 className="font-bold text-gray-900 dark:text-white">Listening</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Foco em entender ideias principais, detalhes e atitudes do falante.</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm transition-colors">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="h-5 w-5 text-gray-700 dark:text-gray-200" />
              <h3 className="font-bold text-gray-900 dark:text-white">Reading</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Skimming, scanning, inferência e vocabulário em contexto.</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm transition-colors">
            <div className="flex items-center gap-2 mb-2">
              <PenLine className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <h3 className="font-bold text-gray-900 dark:text-white">Writing</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Coesão, coerência, vocabulário e gramática sob tempo.</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm transition-colors">
            <div className="flex items-center gap-2 mb-2">
              <Mic className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              <h3 className="font-bold text-gray-900 dark:text-white">Speaking</h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Fluência, pronúncia, vocabulário e desenvolvimento de respostas.</p>
          </div>
        </div>

        <div className="mt-6">
          <ExamAiCoach exam="ielts" />
        </div>
      </main>
    </div>
  );
}
