'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import api from '@/lib/api';
import { wordsApi } from '@/lib/api';
import { ArrowLeft, FileText, Filter, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface StudyTextListItem {
  id: number;
  title: string;
  level: string;
  word_count: number;
}

export default function TextsPage() {
  const { user, isLoading: authLoading, fetchUser } = useAuthStore();
  const router = useRouter();

  const [items, setItems] = useState<StudyTextListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedLevel, setSelectedLevel] = useState('');
  const [levels, setLevels] = useState<string[]>([]);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      void load(selectedLevel);
    }
  }, [user, selectedLevel]);

  useEffect(() => {
    const loadLevels = async () => {
      try {
        const res = await wordsApi.getLevels();
        setLevels(res.data);
      } catch (e) {
        console.error(e);
      }
    };
    void loadLevels();
  }, []);

  const load = async (level?: string) => {
    setIsLoading(true);
    try {
      const res = await api.get('/api/texts/', {
        params: { limit: 50, level: level || undefined },
      });
      setItems(res.data);
    } catch (e) {
      console.error(e);
      toast.error('Erro ao carregar textos');
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50 transition-colors">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="min-w-0 flex items-center gap-4">
            <Link
              href="/dashboard"
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition"
              aria-label="Voltar ao Dashboard"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="h-6 w-6 text-primary-600 dark:text-primary-400 shrink-0" />
              <span className="font-bold text-gray-900 dark:text-white truncate">Slow Listening & Speaking Practice</span>
            </div>
          </div>

          <ThemeToggle />
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 sm:py-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 sm:p-6 mb-6 transition-colors">
          <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-3">
            Estudando através de textos com áudio
          </h2>
          <div className="space-y-3 text-sm sm:text-base text-gray-700 dark:text-gray-300 leading-relaxed">
            <p>
              Estudar através de textos com áudio é o método mais indicado para iniciantes ou até mesmo para quem já
              avançou um pouco nos estudos. A leitura de textos acompanhados da tradução e do áudio ajudam a se
              familiarizar ao idioma sem ter a necessidade de memorizar regras e estruturas gramaticais.
            </p>
            <p>
              O objetivo deste método é que você aprenda um novo idioma da mesma forma que você aprendeu o português,
              absorvendo-o, se acostumando com os padrões da língua, sem a necessidade de decorar centenas de regras
              gramaticais.
            </p>
            <p>
              Não se preocupe em memorizar as palavras, os cartões de memória te ajudarão a adquirir vocabulário. Os
              textos com áudio te ajudarão a aprender novas palavras e seus significados dentro de seus próprios
              contextos, bem como a ouvir a correta pronúncia de cada uma enquanto as lê.
            </p>
            <p>
              Você precisará ter disciplina, portanto mesmo que você somente consiga estudar alguns minutos por dia,
              faça-o, pois o importante não é o quanto você estuda em um só dia, mas que você estude todos os dias.
            </p>
            <p className="font-semibold text-gray-900 dark:text-white">
              Lembre-se, estudar idiomas é uma maratona e não uma corrida de velocidade.
            </p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 sm:p-6 transition-colors">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
            <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">Textos disponíveis</h2>

            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-400 dark:text-gray-500" />
              <select
                value={selectedLevel}
                onChange={(e) => setSelectedLevel(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                aria-label="Filtrar por nível"
              >
                <option value="">Todos os níveis</option>
                {levels.map((level) => (
                  <option key={level} value={level}>
                    Nível {level}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
          ) : items.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-300">Nenhum texto cadastrado ainda.</p>
          ) : (
            <div className="space-y-3">
              {items.map((t) => (
                <Link
                  key={t.id}
                  href={`/texts/${t.id}`}
                  className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary-300 dark:hover:border-primary-600 hover:bg-gray-50 dark:hover:bg-gray-900/40 transition"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-900 dark:text-white break-words">{t.title}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{t.word_count} palavras</p>
                    </div>
                    <span className="text-xs font-semibold px-2 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-200 rounded shrink-0">
                      {t.level}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
