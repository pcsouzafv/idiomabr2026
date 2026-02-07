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
  Sparkles,
  Trash2,
  Undo2,
  PenTool,
  Volume2,
  Clock,
  Flame,
  Trophy,
  Lightbulb,
} from 'lucide-react';
import { conversationApi, gamesApi } from '@/lib/api';
import { resolveMediaUrl } from '@/lib/media';

interface GrammarBuilderItem {
  item_id: string;
  sentence_pt: string;
  tokens: string[];
  verb: string;
  tip: string;
  explanation: string;
  level: number;
  tense: string;
  expected: string;
  audio_url?: string | null;
}

interface GrammarBuilderSession {
  session_id: string;
  items: GrammarBuilderItem[];
  total: number;
}

interface GrammarBuilderResult {
  score: number;
  total: number;
  percentage: number;
  xp_earned: number;
  results: Array<{
    item_id: string;
    correct: boolean;
    expected: string;
    your_answer: string;
    expected_tokens: string[];
    tip: string;
    explanation: string;
    verb: string;
    level?: number;
    tense?: string;
  }>;
}

const tenseLabels: Record<string, string> = {
  present: 'Presente',
  past: 'Passado',
  future: 'Futuro',
};

function parseGrammarLevelParam(value: string | null): number | null {
  if (!value) return null;
  const normalized = value.trim().toUpperCase();
  if (normalized === '1' || normalized === '2' || normalized === '3') {
    return Number(normalized);
  }
  if (normalized === 'A1') return 1;
  if (normalized === 'A2') return 2;
  if (['B1', 'B2', 'C1', 'C2'].includes(normalized)) return 3;
  return null;
}

const FUN_SUCCESS_LINES = [
  'Gramática impecável! Continue.',
  'Excelente construção. Combo subindo!',
  'Muito bom! Você está internalizando o padrão.',
  'Boa! Essa estrutura ficou perfeita.',
];

const FUN_RETRY_LINES = [
  'Quase. Vamos refinar a ordem.',
  'Boa tentativa! A próxima sai melhor.',
  'Sem estresse: errar também ensina.',
  'Tente de novo mantendo o tempo verbal.',
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

export default function GrammarBuilderPage() {
  const searchParams = useSearchParams();
  const initialTense = (searchParams.get('tense') || '').toLowerCase();
  const initialLevel = searchParams.get('level');
  const initialLevelNumber = parseGrammarLevelParam(initialLevel);

  const [selectedTense, setSelectedTense] = useState<string>(initialTense);
  const [selectedLevel, setSelectedLevel] = useState<number | null>(
    initialLevelNumber
  );

  const [session, setSession] = useState<GrammarBuilderSession | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [bankTokens, setBankTokens] = useState<string[]>([]);
  const [builtTokens, setBuiltTokens] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<GrammarBuilderResult | null>(null);

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
    if (!currentItem?.expected) return [];
    return currentItem.expected.split(/\s+/).filter(Boolean);
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

      const res = await gamesApi.startGrammarBuilder({
        num_sentences: 6,
        tense: selectedTense || undefined,
        level: selectedLevel ?? undefined,
      });
      const data: GrammarBuilderSession = res.data;
      setSession(data);

      const first = data.items[0];
      setBankTokens(first?.tokens || []);
      setBuiltTokens([]);
    } catch (e) {
      console.error('Erro ao iniciar Gramática:', e);
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTense, selectedLevel]);

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
      setRoundMessage('Dica indisponível nesta posição. Continue tentando.');
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
      setRoundMessage('Monte ao menos parte da frase antes de continuar.');
      return;
    }

    const itemId = currentItem.item_id;

    setAnswers((prev) => ({
      ...prev,
      [itemId]: builtTokens,
    }));

    const isCorrect = normalizeText(builtTokens.join(' ')) === normalizeText(currentItem.expected || '');
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

    const isLast = currentIndex >= session.total - 1;
    if (!isLast) {
      setTimeout(() => {
        setCurrentIndex((i) => i + 1);
      }, 700);
      return;
    }

    try {
      setSubmitting(true);
      const timeSpent = Math.max(0, Math.floor((Date.now() - startedAtRef.current) / 1000));

      const payloadAnswers = session.items.map((it) => ({
        item_id: it.item_id,
        tokens: answers[it.item_id] || (it.item_id === itemId ? builtTokens : []),
      }));

      const res = await gamesApi.submitGrammarBuilder({
        session_id: session.session_id,
        answers: payloadAnswers,
        time_spent: timeSpent,
      });
      setResult(res.data);
    } catch (e) {
      console.error('Erro ao enviar Gramática:', e);
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

  const playSentenceAudio = async (item: GrammarBuilderItem) => {
    if (!item) return;
    try {
      setIsPlayingAudio(true);
      cleanupCurrentAudioUrl();

      if (item.audio_url && audioRef.current) {
        const resolvedAudio = resolveMediaUrl(item.audio_url);
        if (resolvedAudio) {
          audioRef.current.src = resolvedAudio;
        } else {
          audioRef.current.src = item.audio_url;
        }
        await audioRef.current.play();
        return;
      }

      const response = await conversationApi.textToSpeech({
        text: item.expected,
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#3b0764_0%,_#1f2937_38%,_#030712_100%)]">
      <header className="bg-slate-900/70 backdrop-blur-md border-b border-slate-700/70 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/games" className="text-gray-400 hover:text-white transition">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <PenTool className="w-7 h-7 text-fuchsia-300" />
              Gramática
            </h1>
          </div>
          <button
            onClick={loadSession}
            className="flex items-center gap-2 px-4 py-2 bg-fuchsia-500/20 text-fuchsia-200 rounded-xl hover:bg-fuchsia-500/30 transition"
          >
            <RefreshCw className="w-5 h-5" />
            Reiniciar
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="bg-slate-900/55 border border-slate-700 rounded-2xl p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2 text-gray-300">
              <Sparkles className="w-4 h-4 text-yellow-400" />
              Filtros
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="grammar-tense" className="text-sm text-gray-400">Tempo verbal</label>
              <select
                id="grammar-tense"
                value={selectedTense}
                onChange={(e) => setSelectedTense(e.target.value)}
                className="bg-gray-900 border border-gray-700 text-gray-200 rounded-lg px-3 py-2"
              >
                <option value="">Todos</option>
                <option value="present">Presente</option>
                <option value="past">Passado</option>
                <option value="future">Futuro</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="grammar-level" className="text-sm text-gray-400">Nível</label>
              <select
                id="grammar-level"
                value={selectedLevel ?? ''}
                onChange={(e) => {
                  const v = e.target.value;
                  setSelectedLevel(v ? Number(v) : null);
                }}
                className="bg-gray-900 border border-gray-700 text-gray-200 rounded-lg px-3 py-2"
              >
                <option value="">Todos</option>
                <option value="1">Nível 1</option>
                <option value="2">Nível 2</option>
                <option value="3">Nível 3</option>
              </select>
            </div>
          </div>
        </div>

        {!loading && session && !result && (
          <>
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <div className="text-gray-300 flex items-center gap-3">
                <div className="px-3 py-1 rounded-full bg-slate-900/70 border border-slate-700 text-sm">
                  {progressLabel}
                </div>
                <div className="text-sm text-gray-300 inline-flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  {formatDuration(elapsedSec)}
                </div>
              </div>
              <div className="text-sm text-gray-300">Complete as frases para manter o combo.</div>
            </div>
            <div className="w-full h-2 rounded-full bg-slate-800 border border-slate-700 overflow-hidden mb-4">
              <motion.div
                className="h-full bg-gradient-to-r from-fuchsia-400 to-violet-400"
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 0.35 }}
              />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              <div className="rounded-xl border border-fuchsia-500/25 bg-fuchsia-500/10 px-3 py-2">
                <div className="text-xs text-fuchsia-100">Progresso</div>
                <div className="text-lg font-bold text-white">{progressPercent}%</div>
              </div>
              <div className="rounded-xl border border-orange-500/25 bg-orange-500/10 px-3 py-2">
                <div className="text-xs text-orange-100">Streak</div>
                <div className="text-lg font-bold text-white inline-flex items-center gap-1">
                  <Flame className="w-4 h-4 text-orange-300" />
                  {streak}
                </div>
              </div>
              <div className="rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-3 py-2">
                <div className="text-xs text-emerald-100">Melhor sequência</div>
                <div className="text-lg font-bold text-white">{bestStreak}</div>
              </div>
              <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/10 px-3 py-2">
                <div className="text-xs text-cyan-100">Pontos</div>
                <div className="text-lg font-bold text-white">{roundPoints}</div>
              </div>
            </div>
          </>
        )}

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
                    <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-gray-400">
                      <div>Verbo: <span className="text-gray-200">{r.verb || '-'}</span></div>
                      <div>Tempo: <span className="text-gray-200">{tenseLabels[r.tense || ''] || '-'}</span></div>
                      <div>Nível: <span className="text-gray-200">{r.level ?? '-'}</span></div>
                      <div>Dica: <span className="text-gray-200">{r.tip || '-'}</span></div>
                    </div>
                    {r.explanation && (
                      <div className="mt-2 text-xs text-gray-300">
                        <span className="text-gray-400">Explicação:</span> {r.explanation}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-slate-900/55 border border-slate-700 rounded-2xl p-6 text-gray-200">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <div className="text-sm text-gray-400">Frase em português</div>
                  <div className="text-xl font-semibold text-white mt-1">{currentItem.sentence_pt}</div>
                  <div className="mt-2 text-sm text-gray-400">
                    Verbo: <span className="text-gray-200 font-medium">{currentItem.verb}</span>
                  </div>
                  <div className="mt-1 text-sm text-gray-400">
                    Tempo: <span className="text-gray-200 font-medium">{tenseLabels[currentItem.tense] || currentItem.tense}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-sm text-gray-400">Progresso: {progressLabel}</div>
                  <button
                    onClick={() => playSentenceAudio(currentItem)}
                    disabled={isPlayingAudio}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 disabled:opacity-60"
                    title="Ouvir a frase"
                  >
                    <Volume2 className="w-4 h-4" />
                    Ouvir
                  </button>
                </div>
              </div>

              <div className="mt-4 text-sm text-gray-300 bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                <div className="text-gray-400 mb-1">Dica</div>
                {currentItem.tip}
              </div>
              {currentItem.explanation && (
                <div className="mt-3 text-sm text-gray-300 bg-gray-900/50 border border-gray-700 rounded-lg p-3">
                  <div className="text-gray-400 mb-1">Explicação</div>
                  {currentItem.explanation}
                </div>
              )}
            </div>

            <div className="bg-slate-900/55 border border-slate-700 rounded-2xl p-6 text-gray-200">
              <div className="text-sm text-gray-400">Construa a frase em inglês</div>
              <div className="mt-3 min-h-[52px] rounded-lg border border-gray-700 bg-gray-900/50 px-3 py-2 text-white">
                {currentBuiltText || <span className="text-gray-500">Clique nas peças abaixo</span>}
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {bankTokens.map((token, idx) => (
                  <motion.button
                    key={`${token}-${idx}`}
                    onClick={() => onPickToken(token, idx)}
                    whileHover={{ y: -2, scale: 1.02 }}
                    whileTap={{ scale: 0.96 }}
                    className="px-3 py-1.5 rounded-full bg-slate-700 hover:bg-slate-600 text-white text-sm border border-slate-500/40"
                  >
                    {token}
                  </motion.button>
                ))}
              </div>

              <div className="mt-4 flex items-center gap-2">
                <button
                  onClick={useHint}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/20 text-amber-100 border border-amber-500/30 hover:bg-amber-500/30"
                  disabled={bankTokens.length === 0 || (hintsUsed[currentItem.item_id] || 0) >= 2}
                >
                  <Lightbulb className="w-4 h-4" />
                  Dica ({hintsUsed[currentItem.item_id] || 0}/2)
                </button>
                <button
                  onClick={undoLast}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600"
                  disabled={builtTokens.length === 0}
                >
                  <Undo2 className="w-4 h-4" />
                  Desfazer
                </button>
                <button
                  onClick={clearBuilt}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600"
                  disabled={builtTokens.length === 0}
                >
                  <Trash2 className="w-4 h-4" />
                  Limpar
                </button>

                <div className="flex-1" />

                <button
                  onClick={checkAndNext}
                  disabled={submitting || builtTokens.length === 0}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-fuchsia-600 to-violet-500 text-white hover:from-fuchsia-500 hover:to-violet-400 disabled:opacity-60"
                >
                  {currentIndex >= (session.total - 1) ? 'Finalizar' : 'Continuar'}
                </button>
              </div>

              {roundMessage && (
                <div className="mt-4 text-sm text-fuchsia-100 bg-fuchsia-500/10 border border-fuchsia-500/20 rounded-lg px-4 py-2">
                  {roundMessage}
                </div>
              )}

              <AnimatePresence>
                {feedback && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="mt-3 text-sm"
                  >
                    {feedback === 'correct' ? (
                      <span className="text-emerald-300 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" />
                        Resposta excelente! Mantendo o combo.
                      </span>
                    ) : (
                      <span className="text-rose-300 flex items-center gap-2">
                        <XCircle className="w-4 h-4" />
                        Resposta registrada. Próximo desafio!
                      </span>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
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
