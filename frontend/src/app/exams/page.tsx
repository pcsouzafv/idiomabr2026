'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import {
  BookOpen,
  ArrowLeft,
  LogOut,
  GraduationCap,
  Globe,
  Building2,
  BadgeCheck,
} from 'lucide-react';

const examModules = [
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

export default function ExamsHubPage() {
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

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {examModules.map((m) => {
            const Icon = m.icon;
            return (
              <Link
                key={m.id}
                href={m.href}
                className={`bg-gradient-to-r ${m.color} text-white rounded-xl p-6 shadow-lg hover:shadow-xl transition transform hover:scale-[1.02]`}
              >
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center">
                    <Icon className="h-7 w-7" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold">{m.title}</h3>
                    <p className="text-white/80 text-sm">{m.subtitle}</p>
                  </div>
                </div>
                <p className="mt-4 text-white/90 text-sm leading-relaxed">{m.description}</p>
              </Link>
            );
          })}
        </div>

        <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
          <h2 className="font-bold text-gray-900 dark:text-white mb-2">Como vamos evoluir (profissional)</h2>
          <ul className="text-gray-600 dark:text-gray-400 text-sm space-y-1">
            <li>• Mapear tipos de questão por exame e habilidade (Reading/Listening/Writing/Speaking).</li>
            <li>• Reusar a base atual: palavras → vocabulário; textos → reading; frases/ditado → listening.</li>
            <li>• Próximo passo (quando você quiser): adicionar “simulados” cronometrados e rubricas de escrita.</li>
          </ul>
        </div>
      </main>
    </div>
  );
}
