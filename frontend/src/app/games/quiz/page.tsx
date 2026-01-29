'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
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
import { gamesApi, wordsApi } from '@/lib/api';

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

interface WordDetails {
  id: number;
  english: string;
  ipa: string | null;
  portuguese: string;
  level: string;

  word_type: string | null;
  definition_en: string | null;
  definition_pt: string | null;
  synonyms: string | null;
  antonyms: string | null;

  example_en: string | null;
  example_pt: string | null;
  example_sentences: string | null;
  usage_notes: string | null;
  collocations: string | null;

  tags: string | null;
  audio_url: string | null;

  is_learned: boolean;
  next_review: string | null;
  total_reviews: number;
  correct_count: number;
}

function splitList(raw: string | null | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function buildFallbackExample(wordEn: string, wordPt: string) {
  const safeEn = wordEn.trim();
  const safePt = wordPt.trim();
  return {
    example_en: `The word "${safeEn}" means "${safePt}".`,
    example_pt: `A palavra "${safeEn}" significa "${safePt}".`,
  };
}

export default function QuizPage() {
  const searchParams = useSearchParams();
  const level = searchParams.get('level');
  
  const [session, setSession] = useState<QuizSession | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  // -1 = timeout
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [timeLeft, setTimeLeft] = useState(30);
  const [timerActive, setTimerActive] = useState(false);

  const [baseTotal, setBaseTotal] = useState<number>(0);
  const [repeatQueue, setRepeatQueue] = useState<QuizQuestion[]>([]);
  const repeatWordIdsRef = useRef<Set<number>>(new Set());
  const repeatQueueRef = useRef<QuizQuestion[]>([]);

  const answersRef = useRef<number[]>([]);

  const [wordDetails, setWordDetails] = useState<WordDetails | null>(null);
  const [wordDetailsLoading, setWordDetailsLoading] = useState(false);

  const isAnswered = selectedAnswer !== null;
  const isTimeout = selectedAnswer === -1;

  const isReviewPhase = baseTotal ? currentIndex >= baseTotal : false;

  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  useEffect(() => {
    repeatQueueRef.current = repeatQueue;
  }, [repeatQueue]);

  const startQuiz = useCallback(async () => {
    try {
      setLoading(true);
      const response = await gamesApi.startQuiz({
        num_questions: 10,
        level: level ?? undefined,
      });
      const data: QuizSession = response.data;
      setSession(data);
      setBaseTotal(data.questions.length);
      setRepeatQueue([]);
      repeatWordIdsRef.current = new Set();
      setCurrentIndex(0);
      setAnswers([]);
      setSelectedAnswer(null);
      setShowResult(false);
      setIsCorrect(null);
      setResult(null);
      setWordDetails(null);
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
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [timerActive, timeLeft, currentIndex]);

  const loadWordDetails = useCallback(async (wordId: number) => {
    try {
      setWordDetailsLoading(true);
      const response = await wordsApi.getWord(wordId);
      setWordDetails(response.data as WordDetails);
    } catch (error) {
      console.error('Error loading word details:', error);
      setWordDetails(null);
    } finally {
      setWordDetailsLoading(false);
    }
  }, []);

  const handleTimeout = () => {
    if (!session) return;
    if (selectedAnswer !== null) return;

    setSelectedAnswer(-1);
    setTimerActive(false);
    setIsCorrect(false);
    loadWordDetails(session.questions[currentIndex].word_id);

    setAnswers((prev) => {
      const newAnswers = [...prev, -1]; // -1 indica timeout

      // Só agenda repetição durante a fase “principal” (antes da revisão)
      if (currentIndex < baseTotal) {
        const q = session.questions[currentIndex];
        if (!repeatWordIdsRef.current.has(q.word_id)) {
          repeatWordIdsRef.current.add(q.word_id);
          setRepeatQueue((rq) => [...rq, q]);
        }
      }

      return newAnswers;
    });
  };

  const handleAnswer = async (optionIndex: number) => {
    if (selectedAnswer !== null || !session) return;

    setSelectedAnswer(optionIndex);
    setTimerActive(false);

    const question = session.questions[currentIndex];
    const correct = question.options[optionIndex] === question.correct_answer;
    setIsCorrect(correct);
    loadWordDetails(question.word_id);

    if (correct && !isReviewPhase) {
      // Animação de acerto (somente no quiz “principal”)
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 },
      });
    }

    if (!correct && currentIndex < baseTotal) {
      if (!repeatWordIdsRef.current.has(question.word_id)) {
        repeatWordIdsRef.current.add(question.word_id);
        setRepeatQueue((rq) => [...rq, question]);
      }
    }

    setAnswers((prev) => [...prev, optionIndex]);
  };

  const advanceAfterAnswer = () => {
    if (!session) return;
    if (selectedAnswer === null) return;

    // Se terminou a fase principal e há itens para revisar,
    // adiciona uma “revisão rápida” ao final (não conta na pontuação).
    const queuedRepeats = repeatQueueRef.current;

    if (currentIndex === baseTotal - 1 && queuedRepeats.length > 0) {
      setSession((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          questions: [...prev.questions, ...queuedRepeats],
          total: prev.total + queuedRepeats.length,
        };
      });
      setRepeatQueue([]);
      setCurrentIndex((i) => i + 1);
      setSelectedAnswer(null);
      setIsCorrect(null);
      setWordDetails(null);
      setTimeLeft(30);
      setTimerActive(true);
      return;
    }

    if (currentIndex < session.questions.length - 1) {
      setCurrentIndex((i) => i + 1);
      setSelectedAnswer(null);
      setIsCorrect(null);
      setWordDetails(null);
      setTimeLeft(30);
      setTimerActive(true);
      return;
    }

    submitQuiz(answersRef.current);
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

            {result.incorrect_words.length > 0 && (
              <div className="bg-gray-700/30 border border-gray-700 rounded-xl p-4 mb-6 text-left">
                <p className="text-gray-200 font-medium mb-3">Para revisar</p>
                <div className="space-y-2 max-h-40 overflow-auto pr-1">
                  {result.incorrect_words.slice(0, 8).map((item, idx) => (
                    <div key={`${item.word}-${idx}`} className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-white font-semibold">{item.word}</p>
                        <p className="text-xs text-gray-400">
                          Correto: <span className="text-gray-200">{item.correct_answer}</span>
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-400">Você</p>
                        <p className="text-xs text-gray-200">{item.your_answer}</p>
                      </div>
                    </div>
                  ))}
                </div>
                {result.incorrect_words.length > 8 && (
                  <p className="text-xs text-gray-500 mt-3">
                    +{result.incorrect_words.length - 8} outras
                  </p>
                )}
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

  const chosenText = (() => {
    if (!isAnswered) return null;
    if (selectedAnswer === -1) return '(tempo esgotado)';
    return question.options[selectedAnswer] ?? null;
  })();

  const synonyms = splitList(wordDetails?.synonyms);
  const antonyms = splitList(wordDetails?.antonyms);
  const tags = splitList(wordDetails?.tags);

  const effectiveExample = (() => {
    const en = wordDetails?.example_en;
    const pt = wordDetails?.example_pt;
    if (en || pt) {
      return {
        example_en: en,
        example_pt: pt,
      };
    }
    return buildFallbackExample(question.english, question.correct_answer);
  })();

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
              {isReviewPhase && (
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-medium mb-3">
                  <Zap className="w-4 h-4" />
                  Revisão rápida (não conta na pontuação)
                </div>
              )}
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

            {/* Explicação */}
            {isAnswered && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800/60 border border-gray-700 rounded-2xl p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      {isTimeout ? (
                        <Clock className="w-5 h-5 text-yellow-400" />
                      ) : isCorrect ? (
                        <CheckCircle className="w-5 h-5 text-green-400" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                      <p className="text-white font-semibold">
                        {isTimeout ? 'Tempo esgotado' : isCorrect ? 'Correto' : 'Quase lá'}
                      </p>
                    </div>

                    <p className="text-sm text-gray-300">
                      <span className="text-gray-400">Tradução correta:</span>{' '}
                      <span className="font-semibold text-white">{question.correct_answer}</span>
                    </p>
                    <p className="text-sm text-gray-400">
                      Sua resposta: <span className="text-gray-200">{chosenText}</span>
                    </p>
                  </div>

                  <button
                    onClick={() => speakWord(question.english)}
                    className="px-3 py-2 rounded-xl bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium transition"
                  >
                    Ouvir
                  </button>
                </div>

                <div className="mt-4 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="bg-gray-900/30 rounded-xl p-3 border border-gray-700/60">
                      <p className="text-xs text-gray-400 mb-1">Definição (PT)</p>
                      <p className="text-sm text-gray-200">
                        {wordDetailsLoading
                          ? 'Carregando...'
                          : wordDetails?.definition_pt || 'Sem definição cadastrada ainda.'}
                      </p>
                    </div>
                    <div className="bg-gray-900/30 rounded-xl p-3 border border-gray-700/60">
                      <p className="text-xs text-gray-400 mb-1">Definition (EN)</p>
                      <p className="text-sm text-gray-200">
                        {wordDetailsLoading
                          ? 'Carregando...'
                          : wordDetails?.definition_en || 'No definition available yet.'}
                      </p>
                    </div>
                  </div>

                  {wordDetails?.usage_notes && (
                    <div className="bg-gray-900/30 rounded-xl p-3 border border-gray-700/60">
                      <p className="text-xs text-gray-400 mb-1">Dica de uso</p>
                      <p className="text-sm text-gray-200">{wordDetails.usage_notes}</p>
                    </div>
                  )}

                  <div className="bg-gray-900/30 rounded-xl p-3 border border-gray-700/60">
                    <p className="text-xs text-gray-400 mb-2">Exemplo</p>
                    <p className="text-sm text-gray-200">{effectiveExample.example_en}</p>
                    <p className="text-sm text-gray-400 mt-1">{effectiveExample.example_pt}</p>
                  </div>

                  {(synonyms.length > 0 || antonyms.length > 0) && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {synonyms.length > 0 && (
                        <div className="bg-gray-900/30 rounded-xl p-3 border border-gray-700/60">
                          <p className="text-xs text-gray-400 mb-2">Sinônimos</p>
                          <div className="flex flex-wrap gap-2">
                            {synonyms.slice(0, 8).map((s) => (
                              <span
                                key={s}
                                className="px-2 py-1 rounded-lg bg-gray-700/60 text-gray-200 text-xs"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {antonyms.length > 0 && (
                        <div className="bg-gray-900/30 rounded-xl p-3 border border-gray-700/60">
                          <p className="text-xs text-gray-400 mb-2">Antônimos</p>
                          <div className="flex flex-wrap gap-2">
                            {antonyms.slice(0, 8).map((s) => (
                              <span
                                key={s}
                                className="px-2 py-1 rounded-lg bg-gray-700/60 text-gray-200 text-xs"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 text-xs text-gray-400">
                    {wordDetails?.word_type && (
                      <span className="px-2 py-1 rounded-lg bg-gray-700/60 text-gray-200">
                        {wordDetails.word_type}
                      </span>
                    )}
                    {wordDetails?.level && (
                      <span className="px-2 py-1 rounded-lg bg-gray-700/60 text-gray-200">
                        Nível {wordDetails.level}
                      </span>
                    )}
                    {tags.slice(0, 6).map((t) => (
                      <span key={t} className="px-2 py-1 rounded-lg bg-gray-700/60 text-gray-200">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Próximo */}
            {isAnswered && (
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    // Solta o usuário para seguir (ou finalizar) quando ele estiver pronto.
                    advanceAfterAnswer();
                  }}
                  className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition"
                >
                  {currentIndex < session.questions.length - 1 ? 'Próxima' : 'Finalizar'}
                </button>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
