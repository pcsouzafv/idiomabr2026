'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  RefreshCw,
  Zap,
  Clock,
  Sparkles,
  Trash2,
  Undo2,
  Volume2,
  Flame,
  Trophy,
  Lightbulb,
} from 'lucide-react';
import { conversationApi, gamesApi } from '@/lib/api';
import { resolveMediaUrl } from '@/lib/media';

interface SentenceBuilderItem {
  item_id: string;
  word_id: number;
  focus_word: string;
  sentence_en: string;
  sentence_pt: string;
  tokens: string[];
  audio_url?: string | null;
}

interface SentenceBuilderSession {
  session_id: string;
  items: SentenceBuilderItem[];
  total: number;
}

interface SentenceBuilderResult {
  score: number;
  total: number;
  percentage: number;
  xp_earned: number;
  results: Array<{
    item_id: string;
    correct: boolean;
    expected: string;
    your_answer: string;
  }>;
}

const FUN_SUCCESS_LINES = [
  'Perfeito! Combo ativado.',
  'Mandou muito bem! Continue assim.',
  'Excelente montagem. Ritmo de campeão!',
  'Boa! Você está pegando o padrão.',
];

const FUN_RETRY_LINES = [
  'Quase lá. Ajuste e continue.',
  'Boa tentativa! Vamos para a próxima.',
  'Sem problema, isso faz parte do treino.',
  'Respira e tenta outra formação.',
];

function normalizeText(value: string): string {
  return value
    .toLowerCase()
    .replace(/[.,!?;:]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, '0');
  const seconds = Math.floor(totalSeconds % 60)
    .toString()
    .padStart(2, '0');
  return `${minutes}:${seconds}`;
}

export default function SentenceBuilderPage() {
  const searchParams = useSearchParams();
  const level = searchParams.get('level') || undefined;

  const [session, setSession] = useState<SentenceBuilderSession | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [bankTokens, setBankTokens] = useState<string[]>([]);
  const [builtTokens, setBuiltTokens] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SentenceBuilderResult | null>(null);

  const [feedback, setFeedback] = useState<'correct' | 'wrong' | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [streak, setStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);
  const [roundPoints, setRoundPoints] = useState(0);
  const [roundMessage, setRoundMessage] = useState('');
  const [elapsedSec, setElapsedSec] = useState(0);
  const [hintsUsed, setHintsUsed] = useState<Record<string, number>>({});

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentAudioUrlRef = useRef<string | null>(null);

  const startedAtRef = useRef<number>(Date.now());

  const currentItem = useMemo(() => {
    if (!session) return null;
    return session.items[currentIndex] || null;
  }, [session, currentIndex]);

  const progressLabel = useMemo(() => {
    if (!session) return '';
    return `${Math.min(currentIndex + 1, session.total)}/${session.total}`;
  }, [session, currentIndex]);

  const expectedTokensForCurrent = useMemo(() => {
    if (!currentItem?.sentence_en) return [];
    return currentItem.sentence_en.split(/\s+/).filter(Boolean);
  }, [currentItem]);

  const progressPercent = useMemo(() => {
    if (!session || session.total <= 0) return 0;
    return Math.round((Math.min(currentIndex + 1, session.total) / session.total) * 100);
  }, [currentIndex, session]);

  const loadSession = async () => {
    try {
      setLoading(true);
      setResult(null);
      setFeedback(null);
      setAnswers({});
      setCurrentIndex(0);
      setBuiltTokens([]);
      setBankTokens([]);
      setStreak(0);
      setBestStreak(0);
      setRoundPoints(0);
      setRoundMessage('');
      setElapsedSec(0);
      setHintsUsed({});
      startedAtRef.current = Date.now();

      const res = await gamesApi.startSentenceBuilder({
        level,
        num_sentences: 5,
      });
      const data: SentenceBuilderSession = res.data;
      setSession(data);

      const first = data.items[0];
      setBankTokens(first?.tokens || []);
      setBuiltTokens([]);
    } catch (e) {
      console.error('Erro ao iniciar Montar Frases:', e);
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [level]);

  useEffect(() => {
    if (!session) return;
    const item = session.items[currentIndex];
    if (!item) return;

    setFeedback(null);
    setRoundMessage('');
    setBuiltTokens([]);
    setBankTokens(item.tokens || []);
  }, [currentIndex, session]);

  useEffect(() => {
    if (!session || result) return;
    const interval = window.setInterval(() => {
      setElapsedSec(Math.max(0, Math.floor((Date.now() - startedAtRef.current) / 1000)));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [result, session]);

  const onPickToken = (token: string, idx: number) => {
    setBankTokens((prev) => prev.filter((_, i) => i !== idx));
    setBuiltTokens((prev) => [...prev, token]);
  };

  const undoLast = () => {
    setBuiltTokens((prev) => {
      if (prev.length === 0) return prev;
      const next = prev.slice(0, -1);
      const last = prev[prev.length - 1];
      setBankTokens((bank) => [last, ...bank]);
      return next;
    });
  };

  const clearBuilt = () => {
    setBankTokens((prev) => [...builtTokens, ...prev]);
    setBuiltTokens([]);
  };

  const useHint = () => {
    if (!currentItem) return;
    const used = hintsUsed[currentItem.item_id] || 0;
    if (used >= 2) {
      setRoundMessage('Limite de 2 dicas por frase.');
      return;
    }
    const expectedNext = expectedTokensForCurrent[builtTokens.length];
    if (!expectedNext) {
      setRoundMessage('Você já completou a frase.');
      return;
    }
    const idx = bankTokens.findIndex((token) => normalizeText(token) === normalizeText(expectedNext));
    if (idx < 0) {
      setRoundMessage('Dica indisponível nesta posição. Tente montar manualmente.');
      return;
    }
    onPickToken(bankTokens[idx], idx);
    setHintsUsed((prev) => ({
      ...prev,
      [currentItem.item_id]: used + 1,
    }));
    setRoundMessage(`Dica usada (${used + 1}/2).`);
  };

  const checkAndNext = async () => {
    if (!session || !currentItem) return;
    if (builtTokens.length === 0) {
      setFeedback('wrong');
      setRoundMessage('Monte pelo menos uma parte da frase antes de continuar.');
      return;
    }

    const itemId = currentItem.item_id;

    // Persist answer
    setAnswers((prev) => ({
      ...prev,
      [itemId]: builtTokens,
    }));

    const isCorrect = normalizeText(builtTokens.join(' ')) === normalizeText(currentItem.sentence_en || '');
    if (isCorrect) {
      setFeedback('correct');
      setStreak((prev) => {
        const next = prev + 1;
        setBestStreak((best) => Math.max(best, next));
        return next;
      });
      const bonus = Math.max(0, 3 - (hintsUsed[itemId] || 0));
      setRoundPoints((prev) => prev + 10 + bonus * 2);
      setRoundMessage(FUN_SUCCESS_LINES[(currentIndex + builtTokens.length) % FUN_SUCCESS_LINES.length]);
    } else {
      setFeedback('wrong');
      setStreak(0);
      setRoundMessage(FUN_RETRY_LINES[(currentIndex + builtTokens.length) % FUN_RETRY_LINES.length]);
    }

    // Move on
    const isLast = currentIndex >= (session.total - 1);
    if (!isLast) {
      setTimeout(() => {
        setCurrentIndex((i) => i + 1);
      }, 700);
      return;
    }

    // Submit all
    try {
      setSubmitting(true);
      const timeSpent = Math.max(0, Math.floor((Date.now() - startedAtRef.current) / 1000));

      const payloadAnswers = session.items.map((it) => ({
        item_id: it.item_id,
        tokens: answers[it.item_id] || (it.item_id === itemId ? builtTokens : []),
      }));

      const res = await gamesApi.submitSentenceBuilder({
        session_id: session.session_id,
        answers: payloadAnswers,
        time_spent: timeSpent,
      });
      setResult(res.data);
    } catch (e) {
      console.error('Erro ao enviar Montar Frases:', e);
    } finally {
      setSubmitting(false);
    }
  };

  const currentBuiltText = builtTokens.join(' ');

  const cleanupCurrentAudioUrl = () => {
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.removeAttribute('src');
        audioRef.current.load();
      } catch {
        // ignore
      }
    }
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current);
      currentAudioUrlRef.current = null;
    }
  };

  const playSentenceAudio = async () => {
    if (!currentItem) return;
    try {
      setIsPlayingAudio(true);
      cleanupCurrentAudioUrl();

      if (currentItem.audio_url && audioRef.current) {
        const resolvedAudio = resolveMediaUrl(currentItem.audio_url);
        if (resolvedAudio) {
          audioRef.current.src = resolvedAudio;
        } else {
          audioRef.current.src = currentItem.audio_url;
        }
        await audioRef.current.play();
        return;
      }

      const response = await conversationApi.textToSpeech({
        text: currentItem.sentence_en || currentItem.tokens.join(' '),
      });
      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      currentAudioUrlRef.current = audioUrl;
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        await audioRef.current.play();
      }
    } catch (e) {
      console.error('Erro ao reproduzir áudio:', e);
    } finally {
      setIsPlayingAudio(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#172554_0%,_#111827_35%,_#020617_100%)]">
      <header className="bg-slate-900/70 backdrop-blur-md border-b border-slate-700/70 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/games" className="text-gray-400 hover:text-white transition">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Sparkles className="w-7 h-7 text-cyan-300" />
              Montar Frases
            </h1>
          </div>
          <button
            onClick={loadSession}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-500/15 text-cyan-300 rounded-xl hover:bg-cyan-500/25 transition"
          >
            <RefreshCw className="w-5 h-5" />
            Reiniciar
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="text-gray-300">Carregando…</div>
        ) : !session || !currentItem ? (
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-gray-200">
            Não foi possível carregar o jogo. Tente novamente.
          </div>
        ) : result ? (
          <div className="bg-slate-900/55 border border-slate-700 rounded-2xl p-6 text-gray-200">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className="text-xl font-bold text-white flex items-center gap-2">
                  <Trophy className="w-6 h-6 text-amber-300" />
                  Resultado Final
                </div>
                <div className="text-gray-300 mt-1">
                  {result.score}/{result.total} ({Math.round(result.percentage)}%)
                </div>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <div className="px-4 py-2 rounded-xl bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  {result.xp_earned} XP
                </div>
                <div className="px-4 py-2 rounded-xl bg-fuchsia-500/15 text-fuchsia-200 border border-fuchsia-500/20 flex items-center gap-2">
                  <Flame className="w-4 h-4" />
                  Melhor streak: {bestStreak}
                </div>
                <div className="px-4 py-2 rounded-xl bg-cyan-500/15 text-cyan-200 border border-cyan-500/20">
                  Pontos de rodada: {roundPoints}
                </div>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              {result.results.map((r) => (
                <div key={r.item_id} className="bg-gray-900/40 border border-gray-700 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    {r.correct ? (
                      <CheckCircle className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400" />
                    )}
                    <div className="text-white font-semibold">{r.correct ? 'Correto' : 'Ajustar'}</div>
                  </div>
                  <div className="mt-2 text-sm text-gray-300">
                    <div className="text-gray-400">Sua frase:</div>
                    <div className="mt-1">{r.your_answer || '(vazio)'}</div>
                    {!r.correct && (
                      <>
                        <div className="text-gray-400 mt-3">Resposta esperada:</div>
                        <div className="mt-1">{r.expected}</div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-3">
              <div className="text-gray-300 flex items-center gap-3 flex-wrap">
                <div className="px-3 py-1 rounded-full bg-slate-900/70 border border-slate-700 text-sm">
                  {progressLabel}
                </div>
                {level && (
                  <div className="px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/20 text-indigo-200 text-sm">
                    Nível {level}
                  </div>
                )}
              </div>
              <div className="text-gray-300 text-sm flex items-center gap-2">
                <Clock className="w-4 h-4" />
                {formatDuration(elapsedSec)}
              </div>
            </div>

            <div className="w-full h-2 rounded-full bg-slate-800 border border-slate-700 overflow-hidden mb-4">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-400 to-indigo-400"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 0.35 }}
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/10 px-3 py-2">
                <div className="text-xs text-cyan-200">Progresso</div>
                <div className="text-lg font-bold text-white">{progressPercent}%</div>
              </div>
              <div className="rounded-xl border border-fuchsia-500/25 bg-fuchsia-500/10 px-3 py-2">
                <div className="text-xs text-fuchsia-100">Streak</div>
                <div className="text-lg font-bold text-white inline-flex items-center gap-1">
                  <Flame className="w-4 h-4 text-orange-300" />
                  {streak}
                </div>
              </div>
              <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2">
                <div className="text-xs text-emerald-100">Melhor sequência</div>
                <div className="text-lg font-bold text-white">{bestStreak}</div>
              </div>
              <div className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2">
                <div className="text-xs text-amber-100">Pontos</div>
                <div className="text-lg font-bold text-white">{roundPoints}</div>
              </div>
            </div>

            <div className="bg-slate-900/55 border border-slate-700 rounded-2xl p-6">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="text-gray-300 text-sm">Dica (PT):</div>
                  <div className="text-white text-lg mt-1">{currentItem.sentence_pt || '—'}</div>
                  <div className="text-gray-400 text-sm mt-3">
                    Palavra foco: <span className="text-yellow-300 font-semibold">{currentItem.focus_word}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={playSentenceAudio}
                    disabled={isPlayingAudio}
                    className="px-3 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 transition flex items-center gap-2 disabled:opacity-60"
                    title="Ouvir a frase"
                  >
                    <Volume2 className="w-4 h-4" />
                    Ouvir
                  </button>
                  <button
                    onClick={useHint}
                    className="px-3 py-2 rounded-lg bg-amber-500/20 text-amber-100 border border-amber-500/30 hover:bg-amber-500/30 transition flex items-center gap-2"
                    disabled={bankTokens.length === 0 || (hintsUsed[currentItem.item_id] || 0) >= 2}
                    title="Adicionar próxima palavra correta"
                  >
                    <Lightbulb className="w-4 h-4" />
                    Dica ({hintsUsed[currentItem.item_id] || 0}/2)
                  </button>
                  <button
                    onClick={undoLast}
                    className="px-3 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 transition flex items-center gap-2"
                    disabled={builtTokens.length === 0}
                  >
                    <Undo2 className="w-4 h-4" />
                    Desfazer
                  </button>
                  <button
                    onClick={clearBuilt}
                    className="px-3 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 transition flex items-center gap-2"
                    disabled={builtTokens.length === 0}
                  >
                    <Trash2 className="w-4 h-4" />
                    Limpar
                  </button>
                </div>
              </div>

              <div className="mt-6">
                <div className="text-gray-300 text-sm mb-2">Sua frase:</div>
                <div className="min-h-[56px] bg-gray-900/40 border border-gray-700 rounded-lg p-3 text-white">
                  {currentBuiltText || <span className="text-gray-500">Clique nas palavras abaixo para montar…</span>}
                </div>
              </div>

              <div className="mt-6">
                <div className="text-gray-300 text-sm mb-3">Banco de palavras:</div>
                <div className="flex flex-wrap gap-2">
                  {bankTokens.map((t, idx) => (
                    <motion.button
                      key={`${t}-${idx}`}
                      onClick={() => onPickToken(t, idx)}
                      whileHover={{ y: -2, scale: 1.02 }}
                      whileTap={{ scale: 0.96 }}
                      className="px-3 py-2 rounded-xl bg-slate-700 text-slate-100 hover:bg-slate-600 transition border border-slate-500/40"
                    >
                      {t}
                    </motion.button>
                  ))}
                  {bankTokens.length === 0 && (
                    <div className="text-gray-500 text-sm">Sem peças restantes</div>
                  )}
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
                <div className="text-sm text-gray-300 inline-flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  Monte a frase e avance para manter o combo.
                </div>

                <button
                  onClick={checkAndNext}
                  disabled={submitting || builtTokens.length === 0}
                  className="px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-cyan-500 text-white font-semibold hover:from-indigo-400 hover:to-cyan-400 transition disabled:opacity-60"
                >
                  {currentIndex >= (session.total - 1) ? (submitting ? 'Enviando…' : 'Finalizar') : 'Próxima'}
                </button>
              </div>

              {roundMessage && (
                <div className="mt-4 text-sm text-cyan-100 bg-cyan-500/10 border border-cyan-500/20 rounded-lg px-4 py-2">
                  {roundMessage}
                </div>
              )}

              <AnimatePresence>
                {feedback && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="mt-4"
                  >
                    <div
                      className={`rounded-lg px-4 py-3 border flex items-center gap-2 ${
                        feedback === 'correct'
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                          : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                      }`}
                    >
                      {feedback === 'correct' ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        <XCircle className="w-5 h-5" />
                      )}
                      <span className="text-sm">
                        {feedback === 'correct'
                          ? 'Resposta excelente! Indo para a próxima...'
                          : 'Resposta registrada. Vamos para o próximo desafio!'}
                      </span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </>
        )}
      </main>

      <audio
        ref={audioRef}
        onEnded={() => {
          cleanupCurrentAudioUrl();
          setIsPlayingAudio(false);
        }}
        onError={() => {
          cleanupCurrentAudioUrl();
          setIsPlayingAudio(false);
        }}
      />
    </div>
  );
}
