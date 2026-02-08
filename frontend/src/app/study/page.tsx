'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { studyApi, wordsApi } from '@/lib/api';
import {
  BookOpen,
  ArrowLeft,
  Volume2,
  RotateCcw,
  Check,
  X,
  AlertTriangle,
  Zap,
  Target,
  Settings,
  Play,
  Sparkles,
  TrendingUp,
  Book,
  Flame,
  Award,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';

interface Word {
  id: number;
  english: string;
  ipa: string | null;
  portuguese: string;
  level: string;

  // Informações gramaticais e semânticas
  word_type: string | null;
  definition_en: string | null;
  definition_pt: string | null;
  synonyms: string | null;
  antonyms: string | null;

  // Exemplos e uso
  example_en: string | null;
  example_pt: string | null;
  example_sentences: string | null;
  usage_notes: string | null;
  collocations: string | null;
}

interface StudyCard {
  word: Word;
  direction: string;
  is_new: boolean;
}

interface StudySession {
  cards: StudyCard[];
  total_new: number;
  total_review: number;
  session_size: number;
}

interface SessionStats {
  easy: number;
  medium: number;
  hard: number;
}

interface StudyConfig {
  size: number;
  direction: 'en_to_pt' | 'pt_to_en' | 'mixed';
  level?: string;
  mode: 'mixed' | 'new' | 'review';
}

interface ExampleSentence {
  en: string;
  pt: string;
}

export default function StudyPage() {
  const { user, isLoading: authLoading, fetchUser, fetchStats, stats: userStats } = useAuthStore();
  const router = useRouter();

  // Configuration screen
  const [showConfig, setShowConfig] = useState(true);
  const [config, setConfig] = useState<StudyConfig>({
    size: 10,
    direction: 'mixed',
    mode: 'mixed',
  });
  const [availableLevels, setAvailableLevels] = useState<string[]>([]);
  const [recommendedLevel, setRecommendedLevel] = useState<string | null>(null);

  // Study session
  const [session, setSession] = useState<StudySession | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [studiedCount, setStudiedCount] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [stats, setStats] = useState<SessionStats>({ easy: 0, medium: 0, hard: 0 });
  const [showFeedback, setShowFeedback] = useState(false);
  const [lastDifficulty, setLastDifficulty] = useState<'easy' | 'medium' | 'hard' | null>(null);
  const [currentStreak, setCurrentStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);

  // Sentence practice mode
  const [showSentencePractice, setShowSentencePractice] = useState(false);
  const [generatedSentence, setGeneratedSentence] = useState<string>('');

  useEffect(() => {
    fetchUser();
    fetchStats();
  }, [fetchUser, fetchStats]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  // Load available levels
  useEffect(() => {
    const loadLevels = async () => {
      try {
        const response = await wordsApi.getLevels();
        setAvailableLevels(response.data);
      } catch (error) {
        console.error('Erro ao carregar níveis:', error);
      }
    };
    loadLevels();
  }, []);

  // Determine recommended level
  useEffect(() => {
    const wordsStudied = userStats?.total_words_studied ?? userStats?.total_words_learned;
    if (wordsStudied) {
      const wordsLearned = wordsStudied;
      if (wordsLearned < 500) setRecommendedLevel('A1');
      else if (wordsLearned < 1000) setRecommendedLevel('A2');
      else if (wordsLearned < 1500) setRecommendedLevel('B1');
      else if (wordsLearned < 2000) setRecommendedLevel('B2');
      else if (wordsLearned < 2500) setRecommendedLevel('C1');
      else setRecommendedLevel('C2');
    } else {
      setRecommendedLevel('A1');
    }
  }, [userStats]);

  const loadSession = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: {
        size: number;
        direction: StudyConfig['direction'];
        mode: StudyConfig['mode'];
        level?: string;
      } = {
        size: config.size,
        direction: config.direction,
        mode: config.mode,
        ...(config.level ? { level: config.level } : {}),
      };

      const response = await studyApi.getSession(params);
      setSession(response.data);
      setCurrentIndex(0);
      setIsFlipped(false);
      setStudiedCount(0);
      setSessionComplete(false);
      setStats({ easy: 0, medium: 0, hard: 0 });
      setCurrentStreak(0);
      setBestStreak(0);
      setShowConfig(false);
    } catch (error) {
      console.error('Erro ao carregar sessão:', error);
      toast.error('Erro ao carregar sessão de estudo');
    } finally {
      setIsLoading(false);
    }
  }, [config]);

  const startNewSession = () => {
    void loadSession();
  };

  const handleFlip = () => {
    if (!isSubmitting) {
      setIsFlipped(!isFlipped);
    }
  };

  const handleDifficulty = useCallback(async (difficulty: 'easy' | 'medium' | 'hard') => {
    if (!session || isSubmitting) return;

    const currentCard = session.cards[currentIndex];
    setIsSubmitting(true);
    setLastDifficulty(difficulty);
    setShowFeedback(true);

    // Update stats
    setStats(prev => ({
      ...prev,
      [difficulty]: prev[difficulty] + 1
    }));

    // Update streak
    if (difficulty === 'easy') {
      const newStreak = currentStreak + 1;
      setCurrentStreak(newStreak);
      if (newStreak > bestStreak) {
        setBestStreak(newStreak);
      }
    } else {
      setCurrentStreak(0);
    }

    try {
      await studyApi.submitReview({
        word_id: currentCard.word.id,
        difficulty,
        direction: currentCard.direction,
      });

      setStudiedCount((prev) => prev + 1);

      // Wait a bit for feedback animation
      setTimeout(() => {
        setShowFeedback(false);
        setLastDifficulty(null);
        setShowSentencePractice(false);
        setGeneratedSentence('');

        // Next card or finish
        if (currentIndex < session.cards.length - 1) {
          setCurrentIndex((prev) => prev + 1);
          setIsFlipped(false);
        } else {
          setSessionComplete(true);
          fetchStats();
        }
        setIsSubmitting(false);
      }, 600);
    } catch (error) {
      console.error('Erro ao registrar revisão:', error);
      toast.error('Erro ao salvar progresso');
      setIsSubmitting(false);
      setShowFeedback(false);
      setLastDifficulty(null);
    }
  }, [bestStreak, currentIndex, currentStreak, fetchStats, isSubmitting, session]);

  // Função para processar tradução palavra-por-palavra
  const formatWordByWordTranslation = (ptTranslation: string): JSX.Element | null => {
    if (!ptTranslation) return null;
    
    // Verifica se a tradução já está no formato [palavra] [palavra]
    const hasWordByWord = ptTranslation.includes('[') && ptTranslation.includes(']');
    
    if (hasWordByWord) {
      const parts = ptTranslation.split(/(\[[^\]]+\])/);
      return (
        <span className="inline-flex flex-wrap gap-1">
          {parts.map((part, idx) => {
            if (part.startsWith('[') && part.endsWith(']')) {
              const word = part.slice(1, -1);
              return (
                <span key={idx} className="inline-block px-1.5 py-0.5 bg-white/20 rounded text-xs">
                  {word}
                </span>
              );
            }
            return <span key={idx} className="text-xs opacity-80">{part}</span>;
          })}
        </span>
      );
    }
    
    // Caso contrário, mostra o texto normal
    return <span className="text-xs opacity-80">{ptTranslation}</span>;
  };

  // Detecta tipo de palavra baseado em padrões
  const detectWordType = (word: string): string => {
    const lowerWord = word.toLowerCase();

    // Verbos: terminações comuns
    if (lowerWord.endsWith('ing') || lowerWord.endsWith('ed') ||
        lowerWord.endsWith('ate') || lowerWord.endsWith('ize') ||
        lowerWord.endsWith('ify')) {
      return 'verb';
    }

    // Adjetivos: terminações comuns
    if (lowerWord.endsWith('ful') || lowerWord.endsWith('less') ||
        lowerWord.endsWith('ous') || lowerWord.endsWith('ive') ||
        lowerWord.endsWith('able') || lowerWord.endsWith('ible') ||
        lowerWord.endsWith('al') || lowerWord.endsWith('ic')) {
      return 'adjective';
    }

    // Advérbios
    if (lowerWord.endsWith('ly')) {
      return 'adverb';
    }

    // Substantivos: terminações comuns
    if (lowerWord.endsWith('tion') || lowerWord.endsWith('ness') ||
        lowerWord.endsWith('ment') || lowerWord.endsWith('ity') ||
        lowerWord.endsWith('er') || lowerWord.endsWith('or') ||
        lowerWord.endsWith('ism') || lowerWord.endsWith('ist')) {
      return 'noun';
    }

    // Palavras curtas comuns (artigos, preposições, etc)
    if (word.length <= 3) {
      return 'short';
    }

    return 'noun'; // Padrão: substantivo
  };

  const handleSentencePractice = useCallback(() => {
    if (!session) return;

    const currentCard = session.cards[currentIndex];
    const word = currentCard.word;

    // Use existing example or generate a smart one
    if (word.example_en) {
      setGeneratedSentence(word.example_en);
    } else {
      // Detecta tipo de palavra
      const wordType = detectWordType(word.english);

      // Templates inteligentes baseados no tipo
      const templates: Record<string, string[]> = {
        verb: [
          `I ${word.english} every morning.`,
          `She usually ${word.english}s on weekends.`,
          `They will ${word.english} tomorrow.`,
          `We should ${word.english} more often.`,
          `He ${word.english}ed yesterday.`,
        ],
        noun: [
          `The ${word.english} is very important.`,
          `I bought a new ${word.english} yesterday.`,
          `This ${word.english} looks great!`,
          `She has a beautiful ${word.english}.`,
          `That ${word.english} is expensive.`,
        ],
        adjective: [
          `She is very ${word.english}.`,
          `The weather is ${word.english} today.`,
          `It looks ${word.english} from here.`,
          `This book is quite ${word.english}.`,
          `He seems ${word.english}.`,
        ],
        adverb: [
          `He speaks ${word.english}.`,
          `She smiled ${word.english}.`,
          `They work ${word.english}.`,
          `The car moved ${word.english}.`,
        ],
        short: [
          `This is ${word.english} example.`,
          `Look ${word.english} that!`,
          `Put it ${word.english} here.`,
        ]
      };

      const templateList = templates[wordType] || templates.noun;
      const randomTemplate = templateList[Math.floor(Math.random() * templateList.length)];
      setGeneratedSentence(randomTemplate);
    }

    setShowSentencePractice(true);
  }, [currentIndex, session]);

  // Keyboard shortcuts
  useEffect(() => {
    if (showConfig || sessionComplete) return;

    const handleKeyPress = (e: KeyboardEvent) => {
      if (isSubmitting) return;

      // Space to flip card
      if (e.code === 'Space' && !isFlipped) {
        e.preventDefault();
        setIsFlipped(true);
      }

      // Number keys for difficulty (only when flipped)
      if (isFlipped) {
        if (e.key === '1') void handleDifficulty('hard');
        if (e.key === '2') void handleDifficulty('medium');
        if (e.key === '3') void handleDifficulty('easy');
      }

      // S for sentence practice
      if (e.key === 's' || e.key === 'S') {
        if (isFlipped && session) {
          e.preventDefault();
          handleSentencePractice();
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleDifficulty, handleSentencePractice, isFlipped, isSubmitting, session, sessionComplete, showConfig]);

  const parseExampleSentences = (rawExamples: string | null): ExampleSentence[] => {
    if (!rawExamples) return [];

    try {
      const parsed = JSON.parse(rawExamples) as unknown;
      if (!Array.isArray(parsed)) return [];

      return parsed
        .map((item) => {
          if (typeof item !== 'object' || item === null) return null;
          const en = 'en' in item && typeof item.en === 'string' ? item.en : '';
          const pt = 'pt' in item && typeof item.pt === 'string' ? item.pt : '';
          if (!en) return null;
          return { en, pt };
        })
        .filter((item): item is ExampleSentence => item !== null);
    } catch {
      return [];
    }
  };

  const speakWord = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 0.8;
      speechSynthesis.speak(utterance);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  // Configuration Screen
  if (showConfig) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary-50 to-indigo-100">
        <header className="bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4 flex items-center gap-4">
            <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-2">
              <Settings className="h-6 w-6 text-primary-600" />
              <span className="font-bold text-gray-900">Configurar Sessão de Estudo</span>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-4 py-8 max-w-2xl">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="bg-white rounded-2xl shadow-xl p-8"
          >
            {/* Tamanho da Sessão */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Tamanho da Sessão
              </label>
              <div className="grid grid-cols-4 gap-3">
                {[5, 10, 20, 30].map((size) => (
                  <button
                    key={size}
                    type="button"
                    onClick={() => setConfig({ ...config, size })}
                    className={`py-3 px-4 rounded-lg font-semibold transition ${
                      config.size === size
                        ? 'bg-primary-600 text-white shadow-lg'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Recomendado: 10-20 cards para melhor retenção
              </p>
            </div>

            {/* Modo de Estudo */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Modo de Estudo
              </label>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, mode: 'mixed' })}
                  className={`w-full p-4 rounded-lg text-left transition ${
                    config.mode === 'mixed'
                      ? 'bg-primary-600 text-white shadow-lg'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Sparkles className="h-5 w-5" />
                    <div>
                      <div className="font-semibold">Misto (Recomendado)</div>
                      <div className="text-sm opacity-80">Palavras novas + revisões</div>
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, mode: 'new' })}
                  className={`w-full p-4 rounded-lg text-left transition ${
                    config.mode === 'new'
                      ? 'bg-primary-600 text-white shadow-lg'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Book className="h-5 w-5" />
                    <div>
                      <div className="font-semibold">Apenas Palavras Novas</div>
                      <div className="text-sm opacity-80">Expanda seu vocabulário</div>
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, mode: 'review' })}
                  className={`w-full p-4 rounded-lg text-left transition ${
                    config.mode === 'review'
                      ? 'bg-primary-600 text-white shadow-lg'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <TrendingUp className="h-5 w-5" />
                    <div>
                      <div className="font-semibold">Apenas Revisões</div>
                      <div className="text-sm opacity-80">Reforce o que já aprendeu</div>
                    </div>
                  </div>
                </button>
              </div>
            </div>

            {/* Direção */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Direção de Tradução
              </label>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, direction: 'mixed' })}
                  className={`w-full p-3 rounded-lg text-left transition ${
                    config.direction === 'mixed'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span className="font-medium">🔄 Misto (EN ↔ PT)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, direction: 'en_to_pt' })}
                  className={`w-full p-3 rounded-lg text-left transition ${
                    config.direction === 'en_to_pt'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span className="font-medium">🇺🇸 Inglês → Português</span>
                </button>
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, direction: 'pt_to_en' })}
                  className={`w-full p-3 rounded-lg text-left transition ${
                    config.direction === 'pt_to_en'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span className="font-medium">🇧🇷 Português → Inglês</span>
                </button>
              </div>
            </div>

            {/* Nível (Opcional) */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Filtrar por Nível (Opcional)
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setConfig({ ...config, level: undefined })}
                  className={`px-4 py-2 rounded-lg font-medium transition ${
                    !config.level
                      ? 'bg-gray-700 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Todos
                </button>
                {availableLevels.map((level) => (
                  <button
                    key={level}
                    type="button"
                    onClick={() => setConfig({ ...config, level })}
                    className={`px-4 py-2 rounded-lg font-medium transition relative ${
                      config.level === level
                        ? 'bg-primary-600 text-white'
                        : level === recommendedLevel
                        ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {level}
                    {level === recommendedLevel && config.level !== level && (
                      <Sparkles className="w-3 h-3 absolute -top-1 -right-1 text-yellow-400" />
                    )}
                  </button>
                ))}
              </div>
              {recommendedLevel && (
                <p className="text-xs text-emerald-600 mt-2 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  Nível {recommendedLevel} recomendado para você
                </p>
              )}
            </div>

            {/* Start Button */}
            <button
              type="button"
              onClick={startNewSession}
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-primary-600 to-indigo-600 text-white py-4 rounded-xl font-bold text-lg hover:from-primary-700 hover:to-indigo-700 transition shadow-lg disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  Carregando...
                </>
              ) : (
                <>
                  <Play className="h-6 w-6" />
                  Iniciar Sessão
                </>
              )}
            </button>
          </motion.div>
        </main>
      </div>
    );
  }

  if (!session || session.cards.length === 0) {
    const emptyMessage =
      config.mode === 'review'
        ? 'Você não tem palavras para revisar agora.'
        : config.mode === 'new'
        ? 'Não há palavras novas disponíveis agora.'
        : 'Você não tem palavras disponíveis para estudar agora.';

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center px-4">
          <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check className="h-12 w-12 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Tudo em dia! 🎉
          </h2>
          <p className="text-gray-600 mb-6">
            {emptyMessage}
            <br />
            Volte mais tarde ou explore novas palavras.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              type="button"
              onClick={() => setShowConfig(true)}
              className="px-6 py-3 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition"
            >
              Configurar Nova Sessão
            </button>
            <Link
              href="/dashboard"
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition"
            >
              Voltar ao Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (sessionComplete) {
    const totalCards = stats.easy + stats.medium + stats.hard;
    const accuracyScore = ((stats.easy * 3 + stats.medium * 2 + stats.hard * 1) / (totalCards * 3)) * 100;

    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-center bg-white rounded-2xl p-8 shadow-xl max-w-md mx-4"
        >
          <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <Check className="h-12 w-12 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Sessão Completa! 🎉
          </h2>
          <p className="text-gray-600 mb-6">
            Você estudou <strong>{studiedCount} palavras</strong> nesta sessão.
          </p>

          {/* Session Statistics */}
          <div className="bg-gray-50 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-center gap-2 mb-3">
              <Target className="h-5 w-5 text-primary-600" />
              <span className="font-semibold text-gray-700">Desempenho</span>
            </div>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.easy}</div>
                <div className="text-xs text-gray-500">Fácil</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{stats.medium}</div>
                <div className="text-xs text-gray-500">Médio</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stats.hard}</div>
                <div className="text-xs text-gray-500">Difícil</div>
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600">
                Score: <span className="font-bold text-primary-600">{accuracyScore.toFixed(0)}%</span>
              </div>
            </div>
          </div>

          {/* Best Streak */}
          {bestStreak > 0 && (
            <div className="bg-orange-50 rounded-xl p-4 mb-6">
              <div className="flex items-center justify-center gap-2">
                <Flame className="h-5 w-5 text-orange-500" />
                <span className="text-sm text-gray-700">
                  Melhor sequência: <strong className="text-orange-600">{bestStreak} acertos</strong>
                </span>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={() => setShowConfig(true)}
              className="px-6 py-3 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition flex items-center justify-center gap-2"
            >
              <RotateCcw className="h-5 w-5" />
              Nova Sessão
            </button>
            <Link
              href="/dashboard"
              className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition block"
            >
              Voltar ao Dashboard
            </Link>
          </div>
        </motion.div>
      </div>
    );
  }

  const currentCard = session.cards[currentIndex];
  const isEnToPort = currentCard.direction === 'en_to_pt';
  const frontText = isEnToPort ? currentCard.word.english : currentCard.word.portuguese;
  const backText = isEnToPort ? currentCard.word.portuguese : currentCard.word.english;
  const showIpa = isEnToPort && currentCard.word.ipa;

  const remainingNew = session.cards.slice(currentIndex).filter(c => c.is_new).length;
  const remainingReview = session.cards.slice(currentIndex).filter(c => !c.is_new).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <button
            type="button"
            onClick={() => {
              if (confirm('Deseja sair? Seu progresso será salvo.')) {
                router.push('/dashboard');
              }
            }}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Sair</span>
          </button>

          <div className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-primary-600" />
            <span className="font-bold text-gray-900">Estudar</span>
          </div>

          <div className="text-sm text-gray-500">
            {currentIndex + 1} / {session.cards.length}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 h-1">
          <motion.div
            className="bg-primary-600 h-1"
            initial={{ width: 0 }}
            animate={{ width: `${((currentIndex + 1) / session.cards.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </header>

      {/* Card Container */}
      <main className="container mx-auto px-4 py-8 flex flex-col items-center">
        {/* Session Stats Mini */}
        <div className="mb-4 flex flex-wrap items-center justify-center gap-3 text-sm">
          <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-lg shadow-sm">
            <Zap className="h-4 w-4 text-yellow-500" />
            <span className="font-semibold text-gray-700">{studiedCount}</span>
            <span className="text-gray-500">estudadas</span>
          </div>

          {remainingNew > 0 && (
            <div className="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg font-medium flex items-center gap-1">
              <Book className="h-4 w-4" />
              {remainingNew} novas
            </div>
          )}

          {remainingReview > 0 && (
            <div className="px-3 py-2 bg-amber-100 text-amber-700 rounded-lg font-medium flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              {remainingReview} revisões
            </div>
          )}

          {currentStreak > 0 && (
            <div className="px-3 py-2 bg-orange-100 text-orange-700 rounded-lg font-medium flex items-center gap-1">
              <Flame className="h-4 w-4" />
              {currentStreak} sequência
            </div>
          )}

          <div className="px-3 py-2 bg-purple-100 text-purple-700 rounded-lg font-medium">
            Nível {currentCard.word.level}
          </div>
        </div>

        {/* Flashcard */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ x: 50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -50, opacity: 0 }}
            className="w-full max-w-lg"
          >
            <div
              className={`card-flip cursor-pointer ${isFlipped ? 'flipped' : ''} ${
                showFeedback ? 'pointer-events-none' : ''
              }`}
              onClick={handleFlip}
            >
              <div className="card-flip-inner min-h-[400px]">
                {/* Front */}
                <div className="card-front bg-white rounded-2xl shadow-xl p-8 flex flex-col items-center justify-center min-h-[400px]">
                  <p className="text-sm text-gray-500 mb-4">
                    {isEnToPort ? 'Inglês' : 'Português'}
                  </p>
                  <h2 className="text-4xl font-bold text-gray-900 mb-4 text-center">
                    {frontText}
                  </h2>
                  {showIpa && (
                    <p className="text-xl text-gray-500 mb-4">/{currentCard.word.ipa}/</p>
                  )}
                  {isEnToPort && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        speakWord(currentCard.word.english);
                      }}
                      className="p-3 bg-gray-100 rounded-full hover:bg-gray-200 transition"
                      aria-label="Ouvir pronúncia"
                    >
                      <Volume2 className="h-6 w-6 text-gray-600" />
                    </button>
                  )}
                  <p className="mt-6 text-sm text-gray-400">
                    Clique para ver a resposta
                  </p>
                  <p className="mt-2 text-xs text-gray-300">
                    ou pressione <kbd className="px-2 py-1 bg-gray-100 text-gray-600 rounded">Espaço</kbd>
                  </p>
                </div>

                {/* Back */}
                <div className="card-back bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl shadow-xl p-4 overflow-y-auto max-h-[700px] text-white">
                  <div className="space-y-2 pb-2">
                    {/* Cabeçalho */}
                    <div className="text-center border-b border-white/20 pb-2">
                      <p className="text-xs opacity-70 mb-0.5">
                        {isEnToPort ? 'Português' : 'Inglês'}
                      </p>
                      <h2 className="text-2xl font-bold mb-1">
                        {backText}
                      </h2>
                      {!isEnToPort && currentCard.word.ipa && (
                        <p className="text-base opacity-80 mb-1">/{currentCard.word.ipa}/</p>
                      )}
                      {currentCard.word.word_type && (
                        <span className="inline-block px-2.5 py-0.5 bg-white/20 rounded-full text-xs font-semibold uppercase">
                          {currentCard.word.word_type}
                        </span>
                      )}
                    </div>

                    {/* Definição */}
                    {(currentCard.word.definition_en || currentCard.word.definition_pt) && (
                      <div className="bg-white/10 rounded-lg p-2">
                        <p className="text-xs uppercase tracking-wide opacity-70 mb-1">DEFINIÇÃO</p>
                        {isEnToPort && currentCard.word.definition_pt && (
                          <p className="text-sm leading-relaxed">{currentCard.word.definition_pt}</p>
                        )}
                        {!isEnToPort && currentCard.word.definition_en && (
                          <p className="text-sm leading-relaxed">{currentCard.word.definition_en}</p>
                        )}
                      </div>
                    )}

                    {/* Sinônimos e Antônimos */}
                    {(currentCard.word.synonyms || currentCard.word.antonyms) && (
                      <div className="space-y-1.5">
                        {currentCard.word.synonyms && (
                          <div className="bg-white/10 rounded-lg p-2">
                            <p className="text-xs uppercase tracking-wide opacity-70 mb-1">SINÔNIMOS</p>
                            <p className="text-sm">{currentCard.word.synonyms}</p>
                          </div>
                        )}
                        {currentCard.word.antonyms && (
                          <div className="bg-white/10 rounded-lg p-2">
                            <p className="text-xs uppercase tracking-wide opacity-70 mb-1">ANTÔNIMOS</p>
                            <p className="text-sm">{currentCard.word.antonyms}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Exemplos */}
                    {currentCard.word.example_sentences ? (
                      <div className="bg-white/10 rounded-lg p-2">
                        <p className="text-xs uppercase tracking-wide opacity-70 mb-1.5">EXEMPLOS</p>
                        <div className="space-y-2">
                          {parseExampleSentences(currentCard.word.example_sentences).slice(0, 2).map((ex, idx: number) => (
                            <div key={idx} className="border-b border-white/10 last:border-0 pb-2 last:pb-0">
                              <p className="text-sm italic font-medium mb-0.5">&quot;{ex.en}&quot;</p>
                              <div className="leading-relaxed text-xs mb-1">
                                {formatWordByWordTranslation(ex.pt)}
                              </div>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  speakWord(ex.en);
                                }}
                                className="flex items-center gap-1 px-2 py-1 bg-white/20 hover:bg-white/30 rounded text-xs transition"
                              >
                                <Volume2 className="h-3 w-3" />
                                Ouvir frase
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : currentCard.word.example_en && (
                      <div className="bg-white/10 rounded-lg p-3">
                        <p className="text-xs uppercase tracking-wide opacity-70 mb-2">EXEMPLOS</p>
                        <p className="text-sm italic font-medium mb-1">&quot;{currentCard.word.example_en}&quot;</p>
                        {currentCard.word.example_pt && (
                          <div className="mt-2 leading-relaxed text-xs mb-2">
                            {formatWordByWordTranslation(currentCard.word.example_pt)}
                          </div>
                        )}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            speakWord(currentCard.word.example_en || '');
                          }}
                          className="flex items-center gap-1 px-2 py-1 bg-white/20 hover:bg-white/30 rounded text-xs transition mt-2"
                        >
                          <Volume2 className="h-3 w-3" />
                          Ouvir frase
                        </button>
                      </div>
                    )}

                    {/* Collocations */}
                    {currentCard.word.collocations && (
                      <div className="bg-white/10 rounded-lg p-2">
                        <p className="text-xs uppercase tracking-wide opacity-70 mb-1">COLOCAÇÕES COMUNS</p>
                        <div className="flex flex-wrap gap-1">
                          {JSON.parse(currentCard.word.collocations).slice(0, 4).map((coll: string, idx: number) => (
                            <span key={idx} className="px-2 py-1 bg-white/20 rounded text-xs">
                              {coll}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Notas de uso */}
                    {currentCard.word.usage_notes && (
                      <div className="bg-amber-500/20 rounded-lg p-2 border border-amber-300/30">
                        <p className="text-xs uppercase tracking-wide opacity-90 mb-0.5 flex items-center gap-1">
                          <Zap className="h-3 w-3" /> Dicas de Uso
                        </p>
                        <p className="text-xs leading-relaxed">{currentCard.word.usage_notes}</p>
                      </div>
                    )}

                    {/* Difficulty Buttons - Inside card back */}
                    {isFlipped && (
                      <div className="pt-3 border-t border-white/20 mt-3">
                        <p className="text-center text-xs opacity-80 mb-3">
                          Como foi? Você lembrou da resposta?
                        </p>
                        <div className="grid grid-cols-3 gap-2">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDifficulty('hard');
                            }}
                            disabled={isSubmitting}
                            className={`p-3 rounded-lg bg-red-500/20 border border-red-300/30 text-white hover:bg-red-500/30 disabled:opacity-50 transition-all text-xs font-semibold ${
                              showFeedback && lastDifficulty === 'hard' ? 'ring-2 ring-red-300' : ''
                            }`}
                          >
                            <X className="h-4 w-4 mx-auto mb-1" />
                            <span className="block">Difícil</span>
                            <span className="block text-[10px] mt-0.5 opacity-70 font-normal">revisar hoje</span>
                            <kbd className="block text-[10px] mt-1 px-1.5 py-0.5 bg-red-500/20 rounded opacity-60">1</kbd>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDifficulty('medium');
                            }}
                            disabled={isSubmitting}
                            className={`p-3 rounded-lg bg-yellow-500/20 border border-yellow-300/30 text-white hover:bg-yellow-500/30 disabled:opacity-50 transition-all text-xs font-semibold ${
                              showFeedback && lastDifficulty === 'medium' ? 'ring-2 ring-yellow-300' : ''
                            }`}
                          >
                            <AlertTriangle className="h-4 w-4 mx-auto mb-1" />
                            <span className="block">Médio</span>
                            <span className="block text-[10px] mt-0.5 opacity-70 font-normal">revisar amanhã</span>
                            <kbd className="block text-[10px] mt-1 px-1.5 py-0.5 bg-yellow-500/20 rounded opacity-60">2</kbd>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDifficulty('easy');
                            }}
                            disabled={isSubmitting}
                            className={`p-3 rounded-lg bg-green-500/20 border border-green-300/30 text-white hover:bg-green-500/30 disabled:opacity-50 transition-all text-xs font-semibold ${
                              showFeedback && lastDifficulty === 'easy' ? 'ring-2 ring-green-300' : ''
                            }`}
                          >
                            <Check className="h-4 w-4 mx-auto mb-1" />
                            <span className="block">Fácil</span>
                            <span className="block text-[10px] mt-0.5 opacity-70 font-normal">revisar em 3 dias</span>
                            <kbd className="block text-[10px] mt-1 px-1.5 py-0.5 bg-green-500/20 rounded opacity-60">3</kbd>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* Sentence Practice Mode */}
        {isFlipped && showSentencePractice && generatedSentence && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="mt-6 w-full max-w-lg bg-indigo-50 border-2 border-indigo-200 rounded-xl p-6"
          >
            <div className="flex items-center gap-2 mb-3">
              <Award className="h-5 w-5 text-indigo-600" />
              <span className="font-semibold text-indigo-900">Exemplo em Contexto</span>
            </div>
            <p className="text-gray-800 italic mb-2">&quot;{generatedSentence}&quot;</p>
            {currentCard.word.example_pt && (
              <p className="text-gray-600 text-sm">
                {currentCard.word.example_pt}
              </p>
            )}
            <button
              type="button"
              onClick={() => speakWord(generatedSentence)}
              className="mt-3 flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm"
            >
              <Volume2 className="h-4 w-4" />
              Ouvir frase
            </button>
          </motion.div>
        )}

        {/* Sentence Practice Button - Show only when not showing practice and card is flipped */}
        {isFlipped && !showSentencePractice && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="mt-6 w-full max-w-lg flex justify-center"
          >
            <button
              type="button"
              onClick={handleSentencePractice}
              className="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition text-sm font-medium flex items-center gap-2"
            >
              <Award className="h-4 w-4" />
              Ver exemplo em frase
              <kbd className="px-1.5 py-0.5 bg-indigo-200 text-indigo-800 rounded text-xs">S</kbd>
            </button>
          </motion.div>
        )}

        {/* Flip instruction when not flipped */}
        {!isFlipped && (
          <p className="mt-8 text-gray-500 text-center text-sm">
            💡 Pense na tradução e depois clique no card para conferir
          </p>
        )}
      </main>
    </div>
  );
}
