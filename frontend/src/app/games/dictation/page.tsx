'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  ArrowLeft, 
  RefreshCw,
  Trophy,
  Star,
  Volume2,
  CheckCircle,
  XCircle,
  SkipForward
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { gamesApi } from '@/lib/api';

interface DictationWord {
  word_id: number;
  word: string;
  ipa: string;
  hint: string;
}

interface DictationSession {
  session_id: string;
  words: DictationWord[];
  total: number;
}

interface AchievementSummary {
  id: number;
  name: string;
  icon: string;
  xp_reward: number;
}

interface DictationResult {
  score: number;
  total: number;
  percentage: number;
  xp_earned: number;
  results: Array<{
    word_id: number;
    your_answer: string;
    correct_answer: string;
    is_correct: boolean;
  }>;
  new_achievements: AchievementSummary[];
}

export default function DictationPage() {
  const searchParams = useSearchParams();
  const level = searchParams.get('level');
  
  const [session, setSession] = useState<DictationSession | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<string[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [wordResult, setWordResult] = useState<'correct' | 'wrong' | null>(null);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<DictationResult | null>(null);
  const [showHint, setShowHint] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const startSession = useCallback(async () => {
    try {
      setLoading(true);
      setResult(null);
      setCurrentIndex(0);
      setAnswers([]);
      setCurrentAnswer('');
      setShowResult(false);
      setWordResult(null);
      
      const response = await gamesApi.startDictation({
        num_words: 10,
        level: level ?? undefined,
      });
      setSession(response.data);
    } catch (error) {
      console.error('Error starting session:', error);
    } finally {
      setLoading(false);
    }
  }, [level]);

  useEffect(() => {
    startSession();
  }, [startSession]);

  useEffect(() => {
    if (inputRef.current && !showResult) {
      inputRef.current.focus();
    }
  }, [currentIndex, showResult]);

  const speakWord = (word: string, rate: number = 1) => {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    utterance.rate = rate;
    speechSynthesis.speak(utterance);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session || wordResult !== null) return;

    const currentWord = session.words[currentIndex];
    const isCorrect = currentAnswer.toLowerCase().trim() === currentWord.word.toLowerCase();
    
    setWordResult(isCorrect ? 'correct' : 'wrong');
    
    if (isCorrect) {
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 }
      });
    }

    const newAnswers = [...answers, currentAnswer];
    setAnswers(newAnswers);

    // Esperar e ir para próxima
    setTimeout(() => {
      if (currentIndex < session.words.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setCurrentAnswer('');
        setWordResult(null);
        setShowHint(false);
      } else {
        submitSession(newAnswers);
      }
    }, 2000);
  };

  const skipWord = () => {
    if (!session || wordResult !== null) return;
    
    const newAnswers = [...answers, ''];
    setAnswers(newAnswers);
    setWordResult('wrong');

    setTimeout(() => {
      if (currentIndex < session.words.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setCurrentAnswer('');
        setWordResult(null);
        setShowHint(false);
      } else {
        submitSession(newAnswers);
      }
    }, 2000);
  };

  const submitSession = async (finalAnswers: string[]) => {
    if (!session) return;

    try {
      const payload = {
        session_id: session.session_id,
        answers: session.words.map((word, idx) => ({
          word_id: word.word_id,
          answer: finalAnswers[idx] ?? '',
        })),
      };
      const response = await gamesApi.submitDictation(payload);
      const data: DictationResult = response.data;
      setResult(data);
      setShowResult(true);
      
      if (data.percentage >= 80) {
        confetti({
          particleCount: 200,
          spread: 100,
          origin: { y: 0.6 }
        });
      }
    } catch (error) {
      console.error('Error submitting session:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-300">Preparando ditado...</p>
        </div>
      </div>
    );
  }

  if (showResult && result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-gray-800 rounded-2xl p-8 max-w-md w-full border border-gray-700"
        >
          <div className="text-center">
            <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-4 ${
              result.percentage >= 80 ? 'bg-green-500/20' : 
              result.percentage >= 50 ? 'bg-yellow-500/20' : 'bg-red-500/20'
            }`}>
              <Trophy className={`w-10 h-10 ${
                result.percentage >= 80 ? 'text-green-400' : 
                result.percentage >= 50 ? 'text-yellow-400' : 'text-red-400'
              }`} />
            </div>
            
            <h2 className="text-2xl font-bold text-white mb-2">
              {result.percentage >= 80 ? 'Excelente!' : 
               result.percentage >= 50 ? 'Bom trabalho!' : 'Continue praticando!'}
            </h2>
            
            <p className="text-gray-400 mb-6">
              Você acertou {result.score} de {result.total} palavras
            </p>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-700/50 rounded-xl p-4">
                <div className="flex items-center justify-center gap-2 text-yellow-400 mb-1">
                  <Star className="w-5 h-5" />
                  <span className="text-2xl font-bold">+{result.xp_earned}</span>
                </div>
                <p className="text-sm text-gray-400">XP Ganho</p>
              </div>
                <div className="bg-gray-700/50 rounded-xl p-4">
                  <div className="text-2xl font-bold text-indigo-400 mb-1">
                    {result.percentage.toFixed(0)}%
                  </div>
                  <p className="text-sm text-gray-400">Precisão</p>
                </div>
              </div>

            {/* Resumo das palavras */}
            <div className="bg-gray-700/30 rounded-xl p-4 mb-6 max-h-48 overflow-y-auto">
              <h3 className="text-sm font-medium text-gray-400 mb-2">Resumo:</h3>
              {result.results.map((item) => {
                const dictWord = session?.words.find((word) => word.word_id === item.word_id);
                return (
                  <div key={item.word_id} className="flex items-center justify-between py-1 text-sm">
                    <span className="text-white">{dictWord?.word ?? `Palavra ${item.word_id}`}</span>
                    <span className={item.is_correct ? 'text-green-400' : 'text-red-400'}>
                      {item.your_answer || '(pulou)'}
                    </span>
                  </div>
                );
              })}
            </div>

            {result.new_achievements.length > 0 && (
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4 mb-6 text-left">
                <p className="text-purple-300 font-medium mb-2">Novas Conquistas!</p>
                {result.new_achievements.map((achievement) => (
                  <div key={achievement.id} className="text-sm text-purple-100 mb-1 last:mb-0">
                    {achievement.icon} {achievement.name} (+{achievement.xp_reward} XP)
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-3">
              <Link
                href="/games"
                className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition"
              >
                Voltar
              </Link>
              <button
                onClick={startSession}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium transition flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Jogar Novamente
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    );
  }

  if (!session || session.words.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-300 mb-4">Não foi possível carregar o ditado.</p>
          <Link href="/games" className="text-indigo-400 hover:text-indigo-300">
            Voltar aos jogos
          </Link>
        </div>
      </div>
    );
  }

  const currentWord = session.words[currentIndex];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/games" className="text-gray-400 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          
          <h1 className="text-xl font-bold text-white">Ditado</h1>
          
          <div className="text-gray-400">
            {currentIndex + 1} / {session.words.length}
          </div>
        </div>
        
        {/* Barra de progresso */}
        <div className="h-1 bg-gray-700">
          <motion.div
            className="h-full bg-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${((currentIndex + 1) / session.words.length) * 100}%` }}
          />
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="space-y-8"
          >
            {/* Instruções */}
            <div className="text-center">
              <p className="text-gray-400 mb-4">Ouça a palavra e escreva em inglês:</p>
            </div>

            {/* Botões de áudio */}
            <div className="flex justify-center gap-4">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => speakWord(currentWord.word)}
                className="flex flex-col items-center gap-2 p-6 bg-blue-500/20 border-2 border-blue-500 rounded-2xl text-blue-400 hover:bg-blue-500/30 transition"
              >
                <Volume2 className="w-12 h-12" />
                <span className="text-sm font-medium">Normal</span>
              </motion.button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => speakWord(currentWord.word, 0.5)}
                className="flex flex-col items-center gap-2 p-6 bg-gray-700 border-2 border-gray-600 rounded-2xl text-gray-300 hover:bg-gray-600 transition"
              >
                <Volume2 className="w-12 h-12" />
                <span className="text-sm font-medium">Lento</span>
              </motion.button>
            </div>

            {/* Dica */}
            <div className="text-center">
              {showHint ? (
                <p className="text-gray-400">
                  <span className="text-gray-500">Dica:</span> {currentWord.hint}
                </p>
              ) : (
                <button
                  onClick={() => setShowHint(true)}
                  className="text-indigo-400 hover:text-indigo-300 text-sm"
                >
                  Mostrar dica
                </button>
              )}
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={currentAnswer}
                  onChange={(e) => setCurrentAnswer(e.target.value)}
                  disabled={wordResult !== null}
                  placeholder="Digite a palavra..."
                  className={`w-full px-6 py-4 bg-gray-800 border-2 rounded-xl text-xl text-center font-medium text-white placeholder-gray-500 focus:outline-none transition ${
                    wordResult === 'correct' ? 'border-green-500 bg-green-500/10' :
                    wordResult === 'wrong' ? 'border-red-500 bg-red-500/10' :
                    'border-gray-700 focus:border-indigo-500'
                  }`}
                  autoComplete="off"
                  autoCapitalize="off"
                  spellCheck="false"
                />
                
                {wordResult !== null && (
                  <div className="absolute right-4 top-1/2 -translate-y-1/2">
                    {wordResult === 'correct' ? (
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    ) : (
                      <XCircle className="w-6 h-6 text-red-400" />
                    )}
                  </div>
                )}
              </div>

              {/* Resultado da palavra */}
              {wordResult === 'wrong' && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center"
                >
                  <p className="text-gray-400">A resposta correta era:</p>
                  <p className="text-2xl font-bold text-white">{currentWord.word}</p>
                  <p className="text-gray-500">/{currentWord.ipa}/</p>
                </motion.div>
              )}

              {/* Botões */}
              {wordResult === null && (
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={skipWord}
                    className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition flex items-center justify-center gap-2"
                  >
                    <SkipForward className="w-4 h-4" />
                    Pular
                  </button>
                  <button
                    type="submit"
                    disabled={!currentAnswer.trim()}
                    className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-medium transition"
                  >
                    Verificar
                  </button>
                </div>
              )}
            </form>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
