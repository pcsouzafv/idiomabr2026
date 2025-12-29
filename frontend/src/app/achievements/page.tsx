'use client';

import { useState, useEffect } from 'react';
import { statsApi } from '@/lib/api';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Trophy, Star, Lock, ChevronLeft } from 'lucide-react';

interface Achievement {
  id: number;
  name: string;
  description: string;
  icon: string;
  type: string;
  requirement: number;
  xp_reward: number;
}

interface UserAchievement {
  achievement: Achievement;
  unlocked_at: string;
}

interface UserStats {
  words_learned: number;
  longest_streak: number;
  games_played: number;
  best_quiz_score: number;
  best_matching_time: number;
  level: number;
}

export default function AchievementsPage() {
  const router = useRouter();
  const [allAchievements, setAllAchievements] = useState<Achievement[]>([]);
  const [unlockedAchievements, setUnlockedAchievements] = useState<UserAchievement[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [achievementsRes, userAchievementsRes, statsRes] = await Promise.all([
        statsApi.getAllAchievements(),
        statsApi.getMyAchievements(),
        statsApi.getOverview(),
      ]);

      setAllAchievements(achievementsRes.data);
      setUnlockedAchievements(userAchievementsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Erro ao carregar conquistas:', error);
    } finally {
      setLoading(false);
    }
  };

  const isUnlocked = (achievementId: number) => {
    return unlockedAchievements.some((ua) => ua.achievement.id === achievementId);
  };

  const getProgress = (achievement: Achievement): number => {
    if (!stats) return 0;

    switch (achievement.type) {
      case 'words':
        return Math.min(100, (stats.words_learned / achievement.requirement) * 100);
      case 'streak':
        return Math.min(100, (stats.longest_streak / achievement.requirement) * 100);
      case 'games':
        return Math.min(100, (stats.games_played / achievement.requirement) * 100);
      case 'perfect':
        const perfectCount = 0; // TODO: Track perfect scores
        return Math.min(100, (perfectCount / achievement.requirement) * 100);
      case 'speed':
        if (!stats.best_matching_time) return 0;
        return stats.best_matching_time <= achievement.requirement ? 100 : 0;
      case 'level':
        return Math.min(100, (stats.level / achievement.requirement) * 100);
      default:
        return 0;
    }
  };

  const getCurrentValue = (achievement: Achievement): number => {
    if (!stats) return 0;

    switch (achievement.type) {
      case 'words':
        return stats.words_learned;
      case 'streak':
        return stats.longest_streak;
      case 'games':
        return stats.games_played;
      case 'perfect':
        return 0; // TODO: Track perfect scores
      case 'speed':
        return stats.best_matching_time || 0;
      case 'level':
        return stats.level;
      default:
        return 0;
    }
  };

  const getTypeLabel = (type: string): string => {
    const labels: { [key: string]: string } = {
      words: 'Palavras',
      streak: 'Streak',
      games: 'Jogos',
      perfect: 'Perfeição',
      speed: 'Velocidade',
      level: 'Nível',
    };
    return labels[type] || type;
  };

  const getTypeColor = (type: string): string => {
    const colors: { [key: string]: string } = {
      words: 'blue',
      streak: 'orange',
      games: 'purple',
      perfect: 'yellow',
      speed: 'green',
      level: 'pink',
    };
    return colors[type] || 'gray';
  };

  const filteredAchievements =
    filter === 'all'
      ? allAchievements
      : filter === 'unlocked'
      ? allAchievements.filter((a) => isUnlocked(a.id))
      : allAchievements.filter((a) => !isUnlocked(a.id));

  const groupedAchievements = filteredAchievements.reduce((acc, achievement) => {
    if (!acc[achievement.type]) {
      acc[achievement.type] = [];
    }
    acc[achievement.type].push(achievement);
    return acc;
  }, {} as { [key: string]: Achievement[] });

  const unlockedCount = unlockedAchievements.length;
  const totalCount = allAchievements.length;
  const completionPercentage = totalCount > 0 ? (unlockedCount / totalCount) * 100 : 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/dashboard')}
            className="mb-4 flex items-center text-gray-600 hover:text-gray-900"
          >
            <ChevronLeft className="w-5 h-5 mr-1" />
            Voltar ao Dashboard
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-gray-900 mb-2">
                🏆 Conquistas
              </h1>
              <p className="text-gray-600">
                Desbloqueie conquistas e ganhe XP extra!
              </p>
            </div>
          </div>
        </div>

        {/* Progress Overview */}
        <div className="bg-gradient-to-r from-yellow-400 to-orange-500 rounded-xl p-6 mb-8 text-white shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold">
                {unlockedCount} de {totalCount} Conquistas
              </h2>
              <p className="text-yellow-100">
                {completionPercentage.toFixed(1)}% completado
              </p>
            </div>
            <Trophy className="w-16 h-16 opacity-75" />
          </div>
          <div className="w-full bg-white/30 rounded-full h-4">
            <div
              className="bg-white h-4 rounded-full transition-all duration-500"
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-8">
          <div className="flex space-x-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                filter === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Todas ({totalCount})
            </button>
            <button
              onClick={() => setFilter('unlocked')}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                filter === 'unlocked'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Desbloqueadas ({unlockedCount})
            </button>
            <button
              onClick={() => setFilter('locked')}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                filter === 'locked'
                  ? 'bg-gray-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Bloqueadas ({totalCount - unlockedCount})
            </button>
          </div>
        </div>

        {/* Achievements by Type */}
        {Object.entries(groupedAchievements).map(([type, achievements]) => {
          const color = getTypeColor(type);
          return (
            <div key={type} className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                <span
                  className={`w-3 h-3 rounded-full bg-${color}-500 mr-3`}
                  style={{
                    backgroundColor:
                      color === 'blue'
                        ? '#3B82F6'
                        : color === 'orange'
                        ? '#F97316'
                        : color === 'purple'
                        ? '#A855F7'
                        : color === 'yellow'
                        ? '#EAB308'
                        : color === 'green'
                        ? '#10B981'
                        : color === 'pink'
                        ? '#EC4899'
                        : '#6B7280',
                  }}
                />
                {getTypeLabel(type)}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {achievements.map((achievement) => {
                  const unlocked = isUnlocked(achievement.id);
                  const progress = getProgress(achievement);
                  const currentValue = getCurrentValue(achievement);

                  return (
                    <div
                      key={achievement.id}
                      className={`bg-white rounded-xl p-6 shadow-sm transition-all ${
                        unlocked
                          ? 'border-2 border-yellow-400 shadow-lg'
                          : 'border border-gray-200 opacity-75'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div className="text-4xl">{achievement.icon}</div>
                        {unlocked ? (
                          <Star className="w-6 h-6 text-yellow-500 fill-yellow-500" />
                        ) : (
                          <Lock className="w-6 h-6 text-gray-400" />
                        )}
                      </div>

                      <h3 className="text-lg font-bold text-gray-900 mb-2">
                        {achievement.name}
                      </h3>
                      <p className="text-sm text-gray-600 mb-4">
                        {achievement.description}
                      </p>

                      {/* Progress Bar */}
                      {!unlocked && (
                        <div className="mb-3">
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>Progresso</span>
                            <span>
                              {currentValue} / {achievement.requirement}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`bg-${color}-500 h-2 rounded-full transition-all duration-500`}
                              style={{
                                width: `${progress}%`,
                                backgroundColor:
                                  color === 'blue'
                                    ? '#3B82F6'
                                    : color === 'orange'
                                    ? '#F97316'
                                    : color === 'purple'
                                    ? '#A855F7'
                                    : color === 'yellow'
                                    ? '#EAB308'
                                    : color === 'green'
                                    ? '#10B981'
                                    : color === 'pink'
                                    ? '#EC4899'
                                    : '#6B7280',
                              }}
                            />
                          </div>
                        </div>
                      )}

                      {/* XP Reward */}
                      <div
                        className={`flex items-center justify-between text-sm ${
                          unlocked ? 'text-yellow-600' : 'text-gray-500'
                        }`}
                      >
                        <span className="font-semibold">
                          +{achievement.xp_reward} XP
                        </span>
                        {unlocked && (
                          <span className="text-green-600 font-semibold">
                            ✓ Desbloqueada
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {filteredAchievements.length === 0 && (
          <div className="text-center py-12">
            <Trophy className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 text-lg">
              Nenhuma conquista encontrada neste filtro
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
