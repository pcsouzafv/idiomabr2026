'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Trophy,
  Star,
  Flame,
  Target,
  BookOpen,
  Zap,
  Medal,
  Crown,
  TrendingUp,
  Calendar
} from 'lucide-react';
import { statsApi } from '@/lib/api';

interface UserStats {
  id: number;
  user_id: number;
  total_xp: number;
  level: number;
  words_learned: number;
  words_mastered: number;
  total_reviews: number;
  correct_answers: number;
  games_played: number;
  games_won: number;
  longest_streak: number;
  best_quiz_score: number;
  best_hangman_streak: number;
  best_matching_time: number | null;
  xp_to_next_level: number;
  level_progress: number;
}

interface UserAchievement {
  achievement: {
    id: number;
    name: string;
    description: string;
    icon: string;
    xp_reward: number;
    type: string;
  };
  unlocked_at: string;
}

interface LeaderboardEntry {
  rank: number;
  user_id: number;
  name: string;
  total_xp: number;
  level: number;
  words_learned: number;
}

interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  user_rank?: number;
}

export default function StatsPage() {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [achievements, setAchievements] = useState<UserAchievement[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [userRank, setUserRank] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'achievements' | 'leaderboard'>('overview');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, achievementsRes, leaderboardRes] = await Promise.all([
        statsApi.getOverview(),
        statsApi.getMyAchievements(),
        statsApi.getLeaderboard({ limit: 20 })
      ]);

      setStats(statsRes.data);
      setAchievements(achievementsRes.data);
      const leaderboardData: LeaderboardResponse = leaderboardRes.data;
      setLeaderboard(leaderboardData.entries);
      setUserRank(leaderboardData.user_rank ?? null);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const accuracy = stats && stats.total_reviews > 0
    ? (stats.correct_answers / stats.total_reviews) * 100
    : 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-16 h-16 border-4 border-yellow-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-300">Carregando estatísticas...</p>
        </div>
      </div>
    );
  }

  const xpProgress = stats ? stats.level_progress : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/dashboard" className="text-gray-400 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Trophy className="w-7 h-7 text-yellow-400" />
            Estatísticas
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-8">
          {(['overview', 'achievements', 'leaderboard'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                activeTab === tab
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'overview' ? 'Visão Geral' : 
               tab === 'achievements' ? 'Conquistas' : 'Ranking'}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && stats && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Level Card */}
            <div className="bg-gradient-to-r from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-gray-400 mb-1">Seu Nível</p>
                  <div className="flex items-center gap-3">
                    <span className="text-5xl font-bold text-white">{stats.level}</span>
                    <div>
                      <div className="flex items-center gap-1 text-yellow-400">
                        <Star className="w-5 h-5" />
                        <span className="font-bold">{stats.total_xp} XP</span>
                      </div>
                      <p className="text-sm text-gray-400">
                        {stats.xp_to_next_level} XP para nível {stats.level + 1}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="w-24 h-24 rounded-full bg-indigo-500/20 border-4 border-indigo-500 flex items-center justify-center">
                  <Zap className="w-12 h-12 text-indigo-400" />
                </div>
              </div>
              
              {/* XP Progress Bar */}
              <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${xpProgress}%` }}
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                />
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-orange-400 mb-2">
                  <Flame className="w-5 h-5" />
                  <span className="text-sm font-medium">Maior streak</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats.longest_streak}</p>
                <p className="text-xs text-gray-500">dias consecutivos</p>
              </div>
              
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-green-400 mb-2">
                  <BookOpen className="w-5 h-5" />
                  <span className="text-sm font-medium">Palavras</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats.words_learned}</p>
                <p className="text-xs text-gray-500">aprendidas</p>
              </div>
              
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-purple-400 mb-2">
                  <Target className="w-5 h-5" />
                  <span className="text-sm font-medium">Jogos</span>
                </div>
                <p className="text-3xl font-bold text-white">{stats.games_played}</p>
                <p className="text-xs text-gray-500">jogados</p>
              </div>
              
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <div className="flex items-center gap-2 text-yellow-400 mb-2">
                  <TrendingUp className="w-5 h-5" />
                  <span className="text-sm font-medium">Precisão</span>
                </div>
                <p className="text-3xl font-bold text-white">{accuracy.toFixed(0)}%</p>
                <p className="text-xs text-gray-500">respostas corretas</p>
              </div>
            </div>

            {/* More Stats */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">Estatísticas Detalhadas</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-gray-700">
                  <span className="text-gray-400">Maior streak</span>
                  <span className="text-white font-medium">{stats.longest_streak} dias</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-700">
                  <span className="text-gray-400">Total de revisões</span>
                  <span className="text-white font-medium">{stats.total_reviews}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-700">
                  <span className="text-gray-400">Jogos vencidos</span>
                  <span className="text-white font-medium">{stats.games_won}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-700">
                  <span className="text-gray-400">Melhor pontuação no Quiz</span>
                  <span className="text-white font-medium">{stats.best_quiz_score}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-700">
                  <span className="text-gray-400">Melhor streak na Forca</span>
                  <span className="text-white font-medium">{stats.best_hangman_streak}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-gray-400">Melhor tempo no Matching</span>
                  <span className="text-white font-medium">
                    {stats.best_matching_time ? `${stats.best_matching_time}s` : '--'}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Achievements Tab */}
        {activeTab === 'achievements' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex justify-between items-center mb-4">
              <p className="text-gray-400">
                Conquistas desbloqueadas: {achievements.length}
              </p>
            </div>

            <div className="grid gap-4">
              {achievements.map((achievement) => {
                const reward = achievement.achievement;
                return (
                  <div
                    key={reward.id}
                    className="bg-gray-800 rounded-xl p-4 border border-yellow-500/30 bg-yellow-500/5"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl bg-yellow-500/20 text-yellow-400">
                        {reward.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-white">{reward.name}</h3>
                        <p className="text-sm text-gray-500">{reward.description}</p>
                        <p className="text-xs text-yellow-500/70 mt-1 flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Conquistada em {new Date(achievement.unlocked_at).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-yellow-400">
                          <Star className="w-4 h-4" />
                          <span className="font-bold">+{reward.xp_reward}</span>
                        </div>
                        <span className="text-xs text-gray-500">XP</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Leaderboard Tab */}
        {activeTab === 'leaderboard' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {userRank && (
              <p className="text-gray-400">Sua posição atual: #{userRank}</p>
            )}
            {/* Top 3 */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              {[1, 0, 2].map((position, idx) => {
                const entry = leaderboard[position];
                if (!entry) return null;
                const colors = [
                  'from-gray-400/20 to-gray-500/20 border-gray-400',
                  'from-yellow-500/20 to-yellow-600/20 border-yellow-500',
                  'from-orange-600/20 to-orange-700/20 border-orange-600'
                ];
                const icons = [
                  <Medal key="silver" className="w-8 h-8 text-gray-400" />,
                  <Crown key="gold" className="w-8 h-8 text-yellow-400" />,
                  <Medal key="bronze" className="w-8 h-8 text-orange-600" />
                ];
                const isCurrent = stats && entry.user_id === stats.user_id;
                return (
                  <div
                    key={entry.user_id}
                    className={`bg-gradient-to-b ${colors[idx]} border rounded-xl p-4 text-center ${
                      idx === 1 ? 'transform -translate-y-4' : ''
                    } ${isCurrent ? 'ring-2 ring-indigo-400' : ''}`}
                  >
                    <div className="mb-2">{icons[idx]}</div>
                    <p className="font-bold text-white truncate">
                      {entry.name}
                      {isCurrent && <span className="text-xs ml-1">(você)</span>}
                    </p>
                    <p className="text-sm text-gray-400">Nível {entry.level}</p>
                    <div className="flex items-center justify-center gap-1 text-yellow-400 mt-2">
                      <Star className="w-4 h-4" />
                      <span className="font-bold">{entry.total_xp}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Rest of leaderboard */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              {leaderboard.slice(3).map((entry) => (
                <div
                  key={entry.user_id}
                  className={`flex items-center gap-4 p-4 border-b border-gray-700 last:border-0 ${
                    stats && entry.user_id === stats.user_id ? 'bg-indigo-500/10' : ''
                  }`}
                >
                  <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm font-bold text-gray-400">
                    {entry.rank}
                  </div>
                  <div className="flex-1">
                    <p className={`font-medium ${stats && entry.user_id === stats.user_id ? 'text-indigo-400' : 'text-white'}`}>
                      {entry.name}
                      {stats && entry.user_id === stats.user_id && <span className="text-xs ml-2">(você)</span>}
                    </p>
                    <p className="text-sm text-gray-500">Nível {entry.level}</p>
                  </div>
                  <div className="flex items-center gap-1 text-yellow-400">
                    <Star className="w-4 h-4" />
                    <span className="font-bold">{entry.total_xp}</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
