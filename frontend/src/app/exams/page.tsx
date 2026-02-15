'use client';

import Link from 'next/link';
import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import { EXAM_TRACKS, type ExamId } from './_data/tracks';
import {
  BookOpen,
  ArrowLeft,
  LogOut,
  GraduationCap,
  Globe,
  Building2,
  BadgeCheck,
  TrendingUp,
  Flame,
  Target,
  type LucideIcon,
} from 'lucide-react';

type ExamModule = {
  id: ExamId;
  title: string;
  subtitle: string;
  description: string;
  icon: LucideIcon;
  color: string;
  href: string;
};

const examModules: ExamModule[] = [
  {
    id: 'ielts',
    title: 'IELTS',
    subtitle: 'Academic / General Training',
    description: 'Foco em 4 habilidades, avaliação por band score (1–9).',
    icon: Globe,
    color: 'from-teal-500 to-emerald-600',
    href: '/exams/ielts',
  },
  {
    id: 'toefl',
    title: 'TOEFL iBT',
    subtitle: 'Acadêmico (universidades)',
    description: 'Leitura, Listening, Speaking e Writing em contexto acadêmico.',
    icon: GraduationCap,
    color: 'from-blue-500 to-cyan-600',
    href: '/exams/toefl',
  },
  {
    id: 'toeic',
    title: 'TOEIC',
    subtitle: 'Business / Workplace',
    description: 'Foco em inglês para trabalho (Listening/Reading e opcional Speaking/Writing).',
    icon: Building2,
    color: 'from-amber-500 to-orange-500',
    href: '/exams/toeic',
  },
  {
    id: 'cambridge',
    title: 'Cambridge',
    subtitle: 'B2 First / C1 Advanced / C2 Proficiency',
    description: 'Qualificações alinhadas ao CEFR (B2–C2).',
    icon: BadgeCheck,
    color: 'from-purple-500 to-indigo-600',
    href: '/exams/cambridge',
  },
];

const clamp = (value: number) => Math.max(0, Math.min(100, value));

export default function ExamsHubPage() {
  const { user, stats, isLoading, fetchUser, fetchStats, logout } = useAuthStore();
  const router = useRouter();

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

  const moduleReadiness = useMemo(() => {
    return examModules.map((module) => {
      const targets = EXAM_TRACKS[module.id].targets;
      const wordsProgress = clamp(((stats?.total_words_learned ?? 0) / targets.wordsLearned) * 100);
      const streakProgress = clamp(((stats?.current_streak ?? 0) / targets.streakDays) * 100);
      const dailyProgress = clamp(stats?.daily_goal_progress ?? 0);

      const readiness = Math.round(wordsProgress * 0.45 + streakProgress * 0.25 + dailyProgress * 0.3);

      const weakest = [
        { label: 'vocabulário', value: wordsProgress, href: '/study' },
        { label: 'consistência', value: streakProgress, href: '/study' },
        { label: 'meta diária', value: dailyProgress, href: '/dashboard' },
      ].sort((a, b) => a.value - b.value)[0];

      return {
        ...module,
        wordsProgress,
        streakProgress,
        dailyProgress,
        readiness,
        weakest,
      };
    });
  }, [stats]);

  const averageReadiness = useMemo(() => {
    if (!moduleReadiness.length) return 0;
    return Math.round(
      moduleReadiness.reduce((sum, module) => sum + module.readiness, 0) / moduleReadiness.length
    );
  }, [moduleReadiness]);

  const recommendedExam = useMemo(() => {
    if (!moduleReadiness.length) return null;
    return moduleReadiness.reduce((best, current) =>
      current.readiness > best.readiness ? current : best
    );
  }, [moduleReadiness]);

  const weakestExam = useMemo(() => {
    if (!moduleReadiness.length) return null;
    return moduleReadiness.reduce((lowest, current) =>
      current.readiness < lowest.readiness ? current : lowest
    );
  }, [moduleReadiness]);

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
            href="/dashboard"
            className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar
          </Link>
        </div>

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Preparação para Exames</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Trilhas e prática orientada para IELTS, TOEFL, TOEIC e Cambridge, aproveitando seus estudos de vocabulário,
            frases, leitura e jogos.
          </p>
        </div>

        <section className="mb-8 bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 mb-1">
                <TrendingUp className="h-4 w-4" />
                Prontidão média
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{averageReadiness}%</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {stats?.total_words_learned ?? 0} palavras dominadas
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 mb-1">
                <Target className="h-4 w-4" />
                Melhor encaixe agora
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {recommendedExam ? recommendedExam.title : '—'}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {recommendedExam ? `Foco imediato: ${recommendedExam.weakest.label}` : 'Sem dados'}
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 mb-1">
                <Flame className="h-4 w-4" />
                Lacuna principal
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {weakestExam ? weakestExam.title : '—'}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {weakestExam ? `${weakestExam.readiness}% de prontidão` : 'Sem dados'}
              </div>
            </div>
          </div>
        </section>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {moduleReadiness.map((module) => {
            const Icon = module.icon;
            return (
              <Link
                key={module.id}
                href={module.href}
                className={`bg-gradient-to-r ${module.color} text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]`}
              >
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
                    <Icon className="h-7 w-7" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold">{module.title}</h3>
                    <p className="text-white/80 text-sm">{module.subtitle}</p>
                  </div>
                </div>

                <p className="mt-4 text-white/90 text-sm leading-relaxed">{module.description}</p>

                <div className="mt-4">
                  <div className="flex items-center justify-between text-xs text-white/90 mb-1">
                    <span>Prontidão estimada</span>
                    <span>{module.readiness}%</span>
                  </div>
                  <div className="h-2 bg-white/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-white rounded-full transition-all duration-500"
                      style={{ width: `${module.readiness}%` }}
                    />
                  </div>
                </div>

                <div className="mt-3 text-xs text-white/90">
                  Foco recomendado: <span className="font-semibold capitalize">{module.weakest.label}</span>
                </div>
              </Link>
            );
          })}
        </div>

        <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
          <h2 className="font-bold text-gray-900 dark:text-white mb-2">Próximos passos da semana</h2>
          <ul className="text-gray-600 dark:text-gray-400 text-sm space-y-1">
            <li>• Fechar a meta diária hoje: {stats?.words_studied_today ?? 0}/{stats?.daily_goal ?? 20} palavras.</li>
            <li>• Consolidar streak: você está em {stats?.current_streak ?? 0} dias seguidos.</li>
            <li>
              • Entrar no exame recomendado ({recommendedExam?.title ?? 'IELTS'}) e concluir a Trilha Guiada da Semana.
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
}
