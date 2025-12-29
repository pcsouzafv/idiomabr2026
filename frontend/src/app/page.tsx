'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { BookOpen, Target, Zap, Trophy, ArrowRight } from 'lucide-react';

export default function Home() {
  const { user, isLoading, fetchUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/dashboard');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <nav className="flex justify-between items-center mb-16">
          <div className="flex items-center gap-2">
            <BookOpen className="h-8 w-8 text-primary-600" />
            <span className="text-2xl font-bold text-gray-900">IdiomasBR</span>
          </div>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="px-6 py-2 text-primary-600 font-semibold hover:text-primary-700 transition"
            >
              Entrar
            </Link>
            <Link
              href="/register"
              className="px-6 py-2 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition"
            >
              Criar Conta
            </Link>
          </div>
        </nav>

        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Aprenda Inglês de
            <span className="text-primary-600"> Verdade</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Domine o vocabulário essencial com flashcards inteligentes e repetição
            espaçada. Estude apenas 5-10 minutos por dia e veja resultados reais.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="px-8 py-4 bg-primary-600 text-white rounded-lg font-semibold text-lg hover:bg-primary-700 transition flex items-center justify-center gap-2"
            >
              Começar Gratuitamente
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/login"
              className="px-8 py-4 border-2 border-primary-600 text-primary-600 rounded-lg font-semibold text-lg hover:bg-primary-50 transition"
            >
              Já tenho conta
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-24">
          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition">
            <div className="w-14 h-14 bg-primary-100 rounded-xl flex items-center justify-center mb-4">
              <Zap className="h-7 w-7 text-primary-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Repetição Espaçada
            </h3>
            <p className="text-gray-600">
              Algoritmo inteligente que mostra as palavras no momento certo para
              fixar na memória de longo prazo.
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition">
            <div className="w-14 h-14 bg-success-500/10 rounded-xl flex items-center justify-center mb-4">
              <Target className="h-7 w-7 text-success-500" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              5.000+ Palavras
            </h3>
            <p className="text-gray-600">
              Vocabulário de alta frequência com transcrição fonética (IPA) e
              tradução para português.
            </p>
          </div>

          <div className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition">
            <div className="w-14 h-14 bg-warning-500/10 rounded-xl flex items-center justify-center mb-4">
              <Trophy className="h-7 w-7 text-warning-500" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Gamificação
            </h3>
            <p className="text-gray-600">
              Streaks diários, metas personalizadas e acompanhamento de progresso
              para manter você motivado.
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-24 text-center">
          <div className="grid grid-cols-3 gap-8 max-w-3xl mx-auto">
            <div>
              <div className="text-4xl font-bold text-primary-600">5000+</div>
              <div className="text-gray-600">Palavras</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600">5 min</div>
              <div className="text-gray-600">Por dia</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600">100%</div>
              <div className="text-gray-600">Gratuito</div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-8 mt-24">
        <div className="container mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <BookOpen className="h-6 w-6" />
            <span className="text-xl font-bold">IdiomasBR</span>
          </div>
          <p className="text-gray-400">
            © 2024 IdiomasBR. Feito com ❤️ para aprendizes de inglês.
          </p>
        </div>
      </footer>
    </div>
  );
}
