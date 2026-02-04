'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { wordsApi } from '@/lib/api';
import {
  Brain,
  BookOpen,
  Puzzle,
  Headphones,
  Trophy,
  Flame,
  ArrowLeft,
  Star,
  Zap,
  Target,
  Sparkles,
  PenTool
} from 'lucide-react';

const games = [
  {
    id: 'quiz',
    name: 'Quiz',
    description: 'Teste seu conhecimento escolhendo a tradução correta',
    icon: Brain,
    color: 'from-purple-500 to-indigo-600',
    href: '/games/quiz',
    difficulty: 'Fácil',
    xp: '10-100 XP'
  },
  {
    id: 'hangman',
    name: 'Forca',
    description: 'Adivinhe a palavra letra por letra',
    icon: Target,
    color: 'from-red-500 to-orange-600',
    href: '/games/hangman',
    difficulty: 'Médio',
    xp: '30 XP'
  },
  {
    id: 'matching',
    name: 'Combinar',
    description: 'Combine palavras em inglês com suas traduções',
    icon: Puzzle,
    color: 'from-green-500 to-emerald-600',
    href: '/games/matching',
    difficulty: 'Fácil',
    xp: '20-120 XP'
  },
  {
    id: 'dictation',
    name: 'Ditado',
    description: 'Ouça a pronúncia e escreva a palavra correta',
    icon: Headphones,
    color: 'from-blue-500 to-cyan-600',
    href: '/games/dictation',
    difficulty: 'Difícil',
    xp: '15-150 XP'
  },
  {
    id: 'sentence-builder',
    name: 'Montar Frases',
    description: 'Monte frases em inglês a partir de peças e uma dica em português',
    icon: Sparkles,
    color: 'from-green-500 to-emerald-600',
    href: '/games/sentence-builder',
    difficulty: 'Médio',
    xp: '20-80 XP'
  },
  {
    id: 'grammar-builder',
    name: 'Gramática',
    description: 'Construa frases com foco em verbos, tempos e ordem correta',
    icon: PenTool,
    color: 'from-indigo-500 to-purple-600',
    href: '/games/grammar-builder',
    difficulty: 'Médio',
    xp: '20-90 XP'
  },
  {
    id: 'flashcards',
    name: 'Flashcards',
    description: 'Estudo clássico com repetição espaçada',
    icon: BookOpen,
    color: 'from-amber-500 to-yellow-600',
    href: '/study',
    difficulty: 'Variável',
    xp: '5-20 XP'
  }
];

interface LevelCount {
  level: string;
  count: number;
}

export default function GamesPage() {
  const { stats } = useAuthStore();
  const [selectedLevel, setSelectedLevel] = useState<string | null>(null);
  const [levelCounts, setLevelCounts] = useState<LevelCount[]>([]);
  const [isLoadingCounts, setIsLoadingCounts] = useState(true);
  const [recommendedLevel, setRecommendedLevel] = useState<string | null>(null);

  const levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

  // Buscar contagem de palavras por nível
  useEffect(() => {
    const fetchLevelCounts = async () => {
      try {
        setIsLoadingCounts(true);
        const counts: LevelCount[] = [];

        for (const level of levels) {
          const response = await wordsApi.getWords({
            level,
            per_page: 1,
            page: 1,
          });
          counts.push({
            level,
            count: response.data.total || 0,
          });
        }

        setLevelCounts(counts);
      } catch (error) {
        console.error('Erro ao buscar contagem de níveis:', error);
      } finally {
        setIsLoadingCounts(false);
      }
    };

    fetchLevelCounts();
  }, []);

  // Determinar nível recomendado baseado nas estatísticas do usuário
  useEffect(() => {
    const wordsStudied = stats?.total_words_studied ?? stats?.total_words_learned;
    if (wordsStudied) {
      const wordsLearned = wordsStudied;

      // Lógica simples: cada nível tem ~1000 palavras
      // Recomendar o próximo nível baseado no progresso
      if (wordsLearned < 500) {
        setRecommendedLevel('A1');
      } else if (wordsLearned < 1000) {
        setRecommendedLevel('A2');
      } else if (wordsLearned < 1500) {
        setRecommendedLevel('B1');
      } else if (wordsLearned < 2000) {
        setRecommendedLevel('B2');
      } else if (wordsLearned < 2500) {
        setRecommendedLevel('C1');
      } else {
        setRecommendedLevel('C2');
      }
    } else {
      setRecommendedLevel('A1'); // Padrão para novos usuários
    }
  }, [stats]);

  const getLevelCount = (level: string): number => {
    const found = levelCounts.find((lc) => lc.level === level);
    return found ? found.count : 0;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-gray-400 hover:text-white transition">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Zap className="w-7 h-7 text-yellow-400" />
              Centro de Jogos
            </h1>
          </div>
          <Link 
            href="/stats"
            className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition"
          >
            <Trophy className="w-5 h-5" />
            Ranking
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Filtro de Nível */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-300">Filtrar por nível:</h2>
            {selectedLevel && (
              <button
                onClick={() => setSelectedLevel(null)}
                className="text-sm text-gray-400 hover:text-white transition flex items-center gap-1"
              >
                <span>Limpar filtro</span>
                <span className="text-lg">×</span>
              </button>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedLevel(null)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                selectedLevel === null
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Todos os níveis
            </button>
            {levels.map((level) => {
              const count = getLevelCount(level);
              const isRecommended = level === recommendedLevel;
              const isLowCount = count < 500;

              return (
                <button
                  key={level}
                  onClick={() => setSelectedLevel(level)}
                  className={`px-4 py-2.5 rounded-lg font-medium transition relative ${
                    selectedLevel === level
                      ? 'bg-indigo-600 text-white shadow-lg'
                      : isRecommended
                      ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white hover:from-emerald-500 hover:to-teal-500'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {isRecommended && selectedLevel !== level && (
                      <Sparkles className="w-4 h-4" />
                    )}
                    <span className="font-bold">{level}</span>
                    {!isLoadingCounts && (
                      <span
                        className={`text-xs ${
                          selectedLevel === level
                            ? 'text-indigo-200'
                            : isRecommended && selectedLevel !== level
                            ? 'text-emerald-100'
                            : 'text-gray-400'
                        }`}
                      >
                        ({count})
                      </span>
                    )}
                  </div>
                  {isRecommended && selectedLevel !== level && (
                    <span className="absolute -top-2 -right-2 bg-yellow-400 text-gray-900 text-xs px-1.5 py-0.5 rounded-full font-bold">
                      !
                    </span>
                  )}
                  {isLowCount && !isLoadingCounts && (
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-orange-400 rounded-full"></div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Legenda */}
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-400">
            {recommendedLevel && (
              <div className="flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-emerald-400" />
                <span>
                  <span className="text-emerald-400 font-medium">{recommendedLevel}</span> = Recomendado
                  para você
                </span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 bg-orange-400 rounded-full"></div>
              <span>Menos de 500 palavras</span>
            </div>
          </div>
        </div>

        {/* Grid de Jogos */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {games.map((game, index) => (
            <motion.div
              key={game.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Link
                href={selectedLevel ? `${game.href}?level=${selectedLevel}` : game.href}
                className="block"
              >
                <div className="bg-gray-800 rounded-2xl overflow-hidden border border-gray-700 hover:border-gray-600 transition group relative">
                  {/* Badge de nível filtrado */}
                  {selectedLevel && (
                    <div className="absolute top-3 right-3 z-10 bg-indigo-500 text-white text-xs font-bold px-2.5 py-1 rounded-full shadow-lg flex items-center gap-1">
                      <Target className="w-3 h-3" />
                      <span>Nível {selectedLevel}</span>
                    </div>
                  )}

                  {/* Header com gradiente */}
                  <div className={`bg-gradient-to-r ${game.color} p-6`}>
                    <game.icon className="w-12 h-12 text-white mb-2" />
                    <h3 className="text-2xl font-bold text-white">{game.name}</h3>
                  </div>
                  
                  {/* Conteúdo */}
                  <div className="p-6">
                    <p className="text-gray-400 mb-4">{game.description}</p>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          game.difficulty === 'Fácil' ? 'bg-green-500/20 text-green-400' :
                          game.difficulty === 'Médio' ? 'bg-yellow-500/20 text-yellow-400' :
                          game.difficulty === 'Difícil' ? 'bg-red-500/20 text-red-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {game.difficulty}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-yellow-400">
                        <Star className="w-4 h-4" />
                        <span className="text-sm font-medium">{game.xp}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Botão */}
                  <div className="px-6 pb-6">
                    <div className="w-full py-3 bg-gray-700 group-hover:bg-gray-600 rounded-lg text-center text-white font-medium transition">
                      Jogar Agora →
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* Desafio Diário */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-8"
        >
          <div className="bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30 rounded-2xl p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-yellow-500/20 rounded-xl">
                <Flame className="w-8 h-8 text-yellow-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-white">Desafio Diário</h3>
                <p className="text-gray-300">Complete o desafio de hoje e ganhe bônus de XP!</p>
              </div>
              <Link
                href="/challenges"
                className="px-6 py-3 bg-yellow-500 hover:bg-yellow-400 text-gray-900 font-bold rounded-lg transition"
              >
                Ver Desafio
              </Link>
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
