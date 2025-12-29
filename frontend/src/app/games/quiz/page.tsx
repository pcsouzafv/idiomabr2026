'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  ArrowLeft, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Star,
  Zap,
  Trophy,
  RefreshCw
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { gamesApi } from '@/lib/api';

interface QuizQuestion {
  word_id: number;
  english: string;
  ipa: string;
  options: string[];
  correct_answer: string;
}

interface QuizSession {
  session_id: string;
  questions: QuizQuestion[];
  total: number;
}

interface AchievementSummary {
  id: number;
  name: string;
  description: string;
  icon: string;
  xp_reward: number;
}

interface QuizResult {
  score: number;
  total: number;
  percentage: number;
  xp_earned: number;
  correct_words: string[];
  incorrect_words: Array<{ word: string; your_answer: string; correct_answer: string }>;
  new_achievements: AchievementSummary[];
}

export default function QuizPage() {
  const searchParams = useSearchParams();
  const level = searchParams.get('level');
  
  const [session, setSession] = useState<QuizSession | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [timeLeft, setTimeLeft] = useState(30);
  const [timerActive, setTimerActive] = useState(false);

  const startQuiz = useCallback(async () => {
    try {
      setLoading(true);
      const response = await gamesApi.startQuiz({
        num_questions: 10,
        level: level ?? undefined,
      });
      const data: QuizSession = response.data;
      setSession(data);
      setCurrentIndex(0);
      setAnswers([]);
      setSelectedAnswer(null);
      setShowResult(false);
      setIsCorrect(null);
      setResult(null);
      setTimeLeft(30);
      setTimerActive(true);
    } catch (error) {
      console.error('Error starting quiz:', error);
    } finally {
      setLoading(false);
    }
  }, [level]);

  useEffect(() => {
    startQuiz();
  }, [startQuiz]);

  // Timer
  useEffect(() => {
    if (!timerActive || timeLeft <= 0) return;

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // Tempo esgotado - próxima questão
          handleTimeout();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timerActive, timeLeft, currentIndex]);

  const handleTimeout = () => {
    if (!session) return;
    const newAnswers = [...answers, -1]; // -1 indica timeout
    setAnswers(newAnswers);
    
    if (currentIndex < session.questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setTimeLeft(30);
    } else {
      submitQuiz(newAnswers);
    }
  };

  const handleAnswer = async (optionIndex: number) => {
    if (selectedAnswer !== null || !session) return;
    
    setSelectedAnswer(optionIndex);
    setTimerActive(false);
    
    const question = session.questions[currentIndex];
    const correct = question.options[optionIndex] === question.correct_answer;
    setIsCorrect(correct);
    
    if (correct) {
      // Animação de acerto
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 }
      });
    }
    
    const newAnswers = [...answers, optionIndex];
    setAnswers(newAnswers);
    
    // Esperar um pouco para mostrar o resultado
    setTimeout(() => {
      if (currentIndex < session.questions.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setSelectedAnswer(null);
        setIsCorrect(null);
        setTimeLeft(30);
        setTimerActive(true);
      } else {
        submitQuiz(newAnswers);
      }
    }, 1500);
  };

  const submitQuiz = async (finalAnswers: number[]) => {
    if (!session) return;
    
    try {
      const response = await gamesApi.submitQuiz({
        session_id: session.session_id,
        answers: finalAnswers,
      });
      const data: QuizResult = response.data;
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
      console.error('Error submitting quiz:', error);
    }
  };

  const speakWord = (word: string) => {
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    speechSynthesis.speak(utterance);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-300">Preparando quiz...</p>
        </div>
      </div>
    );
  }

  if (showResult && result) {
    const accuracy = result.percentage;
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-gray-800 rounded-2xl p-8 max-w-md w-full border border-gray-700"
        >
          <div className="text-center">
            <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-4 ${
              accuracy >= 80 ? 'bg-green-500/20' : accuracy >= 50 ? 'bg-yellow-500/20' : 'bg-red-500/20'
            }`}>
              <Trophy className={`w-10 h-10 ${
                accuracy >= 80 ? 'text-green-400' : accuracy >= 50 ? 'text-yellow-400' : 'text-red-400'
              }`} />
            </div>
            
            <h2 className="text-2xl font-bold text-white mb-2">
              {accuracy >= 80 ? 'Excelente!' : accuracy >= 50 ? 'Bom trabalho!' : 'Continue praticando!'}
            </h2>
            
            <p className="text-gray-400 mb-6">
              Você acertou {result.score} de {result.total} questões
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
                  {accuracy.toFixed(0)}%
                </div>
                <p className="text-sm text-gray-400">Precisão</p>
              </div>
            </div>

            {result.new_achievements.length > 0 && (
              <div className="bg-purple-500/20 border border-purple-500/30 rounded-xl p-4 mb-6">
                <p className="text-purple-400 font-medium mb-2">Novas Conquistas!</p>
                {result.new_achievements.map((ach) => (
                  <p key={ach.id} className="text-white">{ach.name}</p>
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
                onClick={startQuiz}
                className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition flex items-center justify-center gap-2"
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

  if (!session || session.questions.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-300 mb-4">Não foi possível carregar o quiz.</p>
          <Link href="/games" className="text-indigo-400 hover:text-indigo-300">
            Voltar aos jogos
          </Link>
        </div>
      </div>
    );
  }

  const question = session.questions[currentIndex];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/games" className="text-gray-400 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          
          <div className="flex items-center gap-4">
            {/* Timer */}
            <div className={`flex items-center gap-2 px-3 py-1 rounded-lg ${
              timeLeft <= 10 ? 'bg-red-500/20 text-red-400' : 'bg-gray-700 text-gray-300'
            }`}>
              <Clock className="w-4 h-4" />
              <span className="font-mono font-bold">{timeLeft}s</span>
            </div>
            
            {/* Progresso */}
            <div className="text-gray-400">
              {currentIndex + 1} / {session.questions.length}
            </div>
          </div>
        </div>
        
        {/* Barra de progresso */}
        <div className="h-1 bg-gray-700">
          <motion.div
            className="h-full bg-indigo-500"
            initial={{ width: 0 }}
            animate={{ width: `${((currentIndex + 1) / session.questions.length) * 100}%` }}
          />
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="space-y-8"
          >
            {/* Pergunta */}
            <div className="text-center">
              <p className="text-gray-400 mb-2">Qual é a tradução de:</p>
              <button
                onClick={() => speakWord(question.english)}
                className="group"
              >
                <h2 className="text-4xl font-bold text-white mb-2 group-hover:text-indigo-400 transition">
                  {question.english}
                </h2>
                <p className="text-lg text-gray-500">/{question.ipa}/</p>
              </button>
              <p className="text-sm text-gray-500 mt-2">Clique na palavra para ouvir</p>
            </div>

            {/* Opções */}
            <div className="space-y-3">
              {question.options.map((option, index) => {
                let buttonClass = 'bg-gray-800 border-gray-700 hover:border-indigo-500 text-white';
                
                if (selectedAnswer !== null) {
                  if (option === question.correct_answer) {
                    buttonClass = 'bg-green-500/20 border-green-500 text-green-400';
                  } else if (index === selectedAnswer && !isCorrect) {
                    buttonClass = 'bg-red-500/20 border-red-500 text-red-400';
                  } else {
                    buttonClass = 'bg-gray-800/50 border-gray-700 text-gray-500';
                  }
                }

                return (
                  <motion.button
                    key={index}
                    whileHover={selectedAnswer === null ? { scale: 1.02 } : {}}
                    whileTap={selectedAnswer === null ? { scale: 0.98 } : {}}
                    onClick={() => handleAnswer(index)}
                    disabled={selectedAnswer !== null}
                    className={`w-full p-4 rounded-xl border-2 text-left font-medium transition ${buttonClass}`}
                  >
                    <div className="flex items-center justify-between">
                      <span>{option}</span>
                      {selectedAnswer !== null && option === question.correct_answer && (
                        <CheckCircle className="w-6 h-6 text-green-400" />
                      )}
                      {selectedAnswer === index && !isCorrect && (
                        <XCircle className="w-6 h-6 text-red-400" />
                      )}
                    </div>
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
