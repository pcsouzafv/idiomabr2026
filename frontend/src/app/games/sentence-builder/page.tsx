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
} from 'lucide-react';
import { gamesApi } from '@/lib/api';

interface SentenceBuilderItem {
  item_id: string;
  word_id: number;
  focus_word: string;
  sentence_pt: string;
  tokens: string[];
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

  const startedAtRef = useRef<number>(Date.now());

  const currentItem = useMemo(() => {
    if (!session) return null;
    return session.items[currentIndex] || null;
  }, [session, currentIndex]);

  const progressLabel = useMemo(() => {
    if (!session) return '';
    return `${Math.min(currentIndex + 1, session.total)}/${session.total}`;
  }, [session, currentIndex]);

  const loadSession = async () => {
    try {
      setLoading(true);
      setResult(null);
      setFeedback(null);
      setAnswers({});
      setCurrentIndex(0);
      setBuiltTokens([]);
      setBankTokens([]);
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
    setBuiltTokens([]);
    setBankTokens(item.tokens || []);
  }, [currentIndex, session]);

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

  const checkAndNext = async () => {
    if (!session || !currentItem) return;

    const itemId = currentItem.item_id;

    // Persist answer
    setAnswers((prev) => ({
      ...prev,
      [itemId]: builtTokens,
    }));

    // Local quick-check (length only) to give immediate feedback.
    // Final correctness comes from backend on submit.
    if (builtTokens.length === currentItem.tokens.length) {
      setFeedback('correct');
    } else {
      setFeedback('wrong');
    }

    // Move on
    const isLast = currentIndex >= (session.total - 1);
    if (!isLast) {
      setTimeout(() => {
        setCurrentIndex((i) => i + 1);
      }, 500);
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/games" className="text-gray-400 hover:text-white transition">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Sparkles className="w-7 h-7 text-yellow-400" />
              Montar Frases
            </h1>
          </div>
          <button
            onClick={loadSession}
            className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition"
          >
            <RefreshCw className="w-5 h-5" />
            Reiniciar
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {loading ? (
          <div className="text-gray-300">Carregando…</div>
        ) : !session || !currentItem ? (
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-gray-200">
            Não foi possível carregar o jogo. Tente novamente.
          </div>
        ) : result ? (
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-gray-200">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className="text-xl font-bold text-white">Resultado</div>
                <div className="text-gray-300 mt-1">
                  {result.score}/{result.total} ({Math.round(result.percentage)}%)
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="px-4 py-2 rounded-lg bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  {result.xp_earned} XP
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
            <div className="flex items-center justify-between mb-4">
              <div className="text-gray-300 flex items-center gap-3">
                <div className="px-3 py-1 rounded-full bg-gray-800/70 border border-gray-700 text-sm">
                  {progressLabel}
                </div>
                {level && (
                  <div className="px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/20 text-indigo-300 text-sm">
                    Nível {level}
                  </div>
                )}
              </div>
              <div className="text-gray-400 text-sm flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Monte a frase usando as peças
              </div>
            </div>

            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
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
                    onClick={undoLast}
                    className="px-3 py-2 rounded-lg bg-gray-700 text-gray-200 hover:bg-gray-600 transition flex items-center gap-2"
                    disabled={builtTokens.length === 0}
                  >
                    <Undo2 className="w-4 h-4" />
                    Desfazer
                  </button>
                  <button
                    onClick={clearBuilt}
                    className="px-3 py-2 rounded-lg bg-gray-700 text-gray-200 hover:bg-gray-600 transition flex items-center gap-2"
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
                    <button
                      key={`${t}-${idx}`}
                      onClick={() => onPickToken(t, idx)}
                      className="px-3 py-2 rounded-lg bg-gray-700 text-gray-100 hover:bg-gray-600 transition"
                    >
                      {t}
                    </button>
                  ))}
                  {bankTokens.length === 0 && (
                    <div className="text-gray-500 text-sm">Sem peças restantes</div>
                  )}
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
                <div className="text-sm text-gray-400">Monte a frase e avance.</div>

                <button
                  onClick={checkAndNext}
                  disabled={submitting}
                  className="px-5 py-3 rounded-lg bg-indigo-600 text-white font-semibold hover:bg-indigo-500 transition disabled:opacity-60"
                >
                  {currentIndex >= (session.total - 1) ? (submitting ? 'Enviando…' : 'Finalizar') : 'Próxima'}
                </button>
              </div>

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
                          ? 'Ok! Próxima frase…'
                          : 'Continue ajustando (você pode mostrar a resposta).'}
                      </span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
