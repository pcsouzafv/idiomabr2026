'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { statsApi } from '@/lib/api';
import {
  ArrowLeft,
  Target,
  Trophy,
  Zap,
  CheckCircle2,
  Clock,
  TrendingUp,
} from 'lucide-react';

interface DailyChallenge {
  id: number;
  challenge_type: string;
  target: number;
  xp_reward: number;
  description: string;
  progress: number;
  completed: boolean;
}

export default function ChallengesPage() {
  const { user, isLoading: authLoading, fetchUser } = useAuthStore();
  const router = useRouter();

  const [challenge, setChallenge] = useState<DailyChallenge | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    const loadChallenge = async () => {
      if (!user) return;

      try {
        setIsLoading(true);
        const response = await statsApi.getDailyChallenge();
        setChallenge(response.data);
      } catch (error) {
        console.error('Erro ao carregar desafio diário:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      loadChallenge();
    }
  }, [user]);

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const progressPercentage = challenge
    ? Math.min(100, (challenge.progress / challenge.target) * 100)
    : 0;

  const getChallengeIcon = (type: string) => {
    switch (type) {
      case 'reviews':
        return <TrendingUp className="h-8 w-8" />;
      case 'quiz':
        return <Target className="h-8 w-8" />;
      case 'perfect':
        return <Trophy className="h-8 w-8" />;
      case 'words':
        return <Zap className="h-8 w-8" />;
      case 'games':
        return <Target className="h-8 w-8" />;
      default:
        return <Target className="h-8 w-8" />;
    }
  };

  const getChallengeColor = (type: string) => {
    switch (type) {
      case 'reviews':
        return 'from-blue-500 to-indigo-600';
      case 'quiz':
        return 'from-purple-500 to-pink-600';
      case 'perfect':
        return 'from-yellow-500 to-orange-500';
      case 'words':
        return 'from-green-500 to-emerald-600';
      case 'games':
        return 'from-red-500 to-rose-600';
      default:
        return 'from-primary-500 to-primary-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Voltar</span>
          </Link>

          <div className="flex items-center gap-2">
            <Trophy className="h-6 w-6 text-primary-600" />
            <span className="font-bold text-gray-900">Desafio Diário</span>
          </div>

          <div className="w-20"></div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-2xl">
        {/* Challenge Card */}
        {challenge && (
          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            {/* Challenge Header */}
            <div
              className={`bg-gradient-to-r ${getChallengeColor(
                challenge.challenge_type
              )} text-white p-8`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="w-16 h-16 bg-white/20 rounded-xl flex items-center justify-center">
                  {getChallengeIcon(challenge.challenge_type)}
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    <Zap className="h-5 w-5" />
                    <span className="text-2xl font-bold">+{challenge.xp_reward} XP</span>
                  </div>
                  {challenge.completed && (
                    <div className="flex items-center gap-1 text-sm mt-1">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Completo!</span>
                    </div>
                  )}
                </div>
              </div>

              <h2 className="text-2xl font-bold mb-2">Desafio de Hoje</h2>
              <p className="text-white/90">{challenge.description}</p>
            </div>

            {/* Progress Section */}
            <div className="p-8">
              <div className="mb-6">
                <div className="flex justify-between items-center mb-3">
                  <span className="font-semibold text-gray-700">Progresso</span>
                  <span className="text-sm text-gray-500">
                    {challenge.progress} / {challenge.target}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className={`bg-gradient-to-r ${getChallengeColor(
                      challenge.challenge_type
                    )} h-4 rounded-full transition-all duration-500`}
                    style={{ width: `${progressPercentage}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-sm text-gray-500 text-center">
                  {progressPercentage.toFixed(0)}% completo
                </p>
              </div>

              {/* Status Message */}
              {challenge.completed ? (
                <div className="bg-green-50 border-2 border-green-200 rounded-xl p-6 text-center">
                  <div className="flex justify-center mb-3">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="h-8 w-8 text-green-600" />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-green-800 mb-2">
                    Parabéns!
                  </h3>
                  <p className="text-green-700 mb-4">
                    Você completou o desafio de hoje e ganhou{' '}
                    <strong>+{challenge.xp_reward} XP</strong>!
                  </p>
                  <p className="text-sm text-green-600">
                    Continue assim e volte amanhã para um novo desafio.
                  </p>
                </div>
              ) : (
                <div className="bg-amber-50 border-2 border-amber-200 rounded-xl p-6 text-center">
                  <div className="flex justify-center mb-3">
                    <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center">
                      <Clock className="h-8 w-8 text-amber-600" />
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-amber-800 mb-2">
                    Continue Progredindo!
                  </h3>
                  <p className="text-amber-700 mb-2">
                    Faltam apenas{' '}
                    <strong>{challenge.target - challenge.progress}</strong> para
                    completar o desafio.
                  </p>
                  <p className="text-sm text-amber-600">
                    Complete hoje para não perder sua sequência!
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="mt-8 space-y-3">
                <Link
                  href="/study"
                  className="block w-full bg-gradient-to-r from-primary-500 to-primary-600 text-white text-center rounded-xl py-4 font-semibold hover:shadow-lg transition"
                >
                  Estudar Agora
                </Link>
                <Link
                  href="/games"
                  className="block w-full bg-white text-gray-700 text-center rounded-xl py-4 font-semibold border-2 border-gray-200 hover:border-primary-300 hover:bg-gray-50 transition"
                >
                  Jogar
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Info Section */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-200">
          <h3 className="font-bold text-blue-800 mb-2 flex items-center gap-2">
            <Target className="h-5 w-5" />
            Como funcionam os Desafios Diários?
          </h3>
          <ul className="text-blue-700 space-y-2 text-sm">
            <li className="flex gap-2">
              <span className="text-blue-500">•</span>
              <span>Um novo desafio é gerado automaticamente todos os dias</span>
            </li>
            <li className="flex gap-2">
              <span className="text-blue-500">•</span>
              <span>Complete para ganhar XP extra e manter sua sequência</span>
            </li>
            <li className="flex gap-2">
              <span className="text-blue-500">•</span>
              <span>Os desafios variam de revisões, jogos, e aprendizado de novas palavras</span>
            </li>
            <li className="flex gap-2">
              <span className="text-blue-500">•</span>
              <span>Seu progresso é atualizado automaticamente conforme você estuda</span>
            </li>
          </ul>
        </div>
      </main>
    </div>
  );
}
