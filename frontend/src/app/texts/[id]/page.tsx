'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import api from '@/lib/api';
import { resolveMediaUrl } from '@/lib/media';
import { ArrowLeft, FileText, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

type TextToken = {
  raw: string;
  isWord: boolean;
  wordPosition: number | null;
};

type AlignmentSource = 'transcription_words' | 'transcription_segments' | 'none';

type AudioWordTiming = {
  index: number;
  word: string;
  start: number;
  end: number;
};

type EstimatedWordTiming = {
  index: number;
  startRatio: number;
  endRatio: number;
};

interface StudyTextDetail {
  id: number;
  title: string;
  level: string;
  content_en: string;
  content_pt?: string | null;
  audio_url?: string | null;
  tags?: unknown;
}

interface AudioAlignmentResponse {
  source: AlignmentSource;
  word_timings: AudioWordTiming[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const normalizeWord = (value: string): string => {
  return value
    .toLowerCase()
    .replace(/’/g, "'")
    .replace(/[^a-z0-9']/g, '');
};

const findWordIndexByTime = (timeInSeconds: number, rows: AudioWordTiming[]): number | null => {
  if (!Number.isFinite(timeInSeconds) || rows.length === 0) return null;

  let left = 0;
  let right = rows.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const row = rows[mid];
    if (timeInSeconds < row.start) {
      right = mid - 1;
      continue;
    }
    if (timeInSeconds > row.end) {
      left = mid + 1;
      continue;
    }
    return row.index;
  }

  if (left >= rows.length) {
    return rows[rows.length - 1].index;
  }
  if (right < 0) {
    return rows[0].index;
  }

  const before = rows[right];
  const after = rows[left];
  const distanceToBefore = Math.abs(timeInSeconds - before.end);
  const distanceToAfter = Math.abs(after.start - timeInSeconds);
  return distanceToBefore <= distanceToAfter ? before.index : after.index;
};

const findWordIndexByProgress = (progress: number, rows: EstimatedWordTiming[]): number | null => {
  if (!Number.isFinite(progress) || rows.length === 0) return null;

  let left = 0;
  let right = rows.length - 1;

  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    const row = rows[mid];
    if (progress < row.startRatio) {
      right = mid - 1;
      continue;
    }
    if (progress > row.endRatio) {
      left = mid + 1;
      continue;
    }
    return row.index;
  }

  if (left >= rows.length) {
    return rows[rows.length - 1].index;
  }
  if (right < 0) {
    return rows[0].index;
  }
  return rows[left].index;
};

export default function TextDetailPage() {
  const { user, isLoading: authLoading, fetchUser } = useAuthStore();
  const router = useRouter();
  const params = useParams();

  const textId = useMemo(() => {
    const raw = params?.id;
    const asString = Array.isArray(raw) ? raw[0] : raw;
    return Number(asString);
  }, [params]);

  const [text, setText] = useState<StudyTextDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [shadowingSeconds, setShadowingSeconds] = useState(0);
  const [shadowingRunning, setShadowingRunning] = useState(false);

  const [followAudioWords, setFollowAudioWords] = useState(true);
  const [playbackRate, setPlaybackRate] = useState<number>(0.9);
  const [activeWordPosition, setActiveWordPosition] = useState<number | null>(null);
  const [audioWordTimings, setAudioWordTimings] = useState<AudioWordTiming[]>([]);
  const [audioAlignmentSource, setAudioAlignmentSource] = useState<AlignmentSource>('none');
  const [isLoadingAudioAlignment, setIsLoadingAudioAlignment] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const textReaderRef = useRef<HTMLDivElement | null>(null);

  const textTokens = useMemo<TextToken[]>(() => {
    const source = text?.content_en ?? '';
    const chunks = source.match(/\s+|[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*|[^\sA-Za-z0-9]/g) ?? [];
    let wordPosition = 0;

    return chunks.map((raw) => {
      const isWord = /^[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*$/.test(raw);
      const token: TextToken = {
        raw,
        isWord,
        wordPosition: isWord ? wordPosition : null,
      };
      if (isWord) {
        wordPosition += 1;
      }
      return token;
    });
  }, [text?.content_en]);

  const textWords = useMemo(() => textTokens.filter((token) => token.isWord).map((token) => token.raw), [textTokens]);
  const totalWordTokens = textWords.length;

  const estimatedWordTimings = useMemo<EstimatedWordTiming[]>(() => {
    let accumulatedWeight = 0;
    const weighted: Array<{
      index: number;
      startWeight: number;
      endWeight: number;
    }> = [];

    for (let tokenIndex = 0; tokenIndex < textTokens.length; tokenIndex += 1) {
      const token = textTokens[tokenIndex];
      if (!token.isWord || token.wordPosition === null) continue;

      const normalized = normalizeWord(token.raw);
      const lengthWeight = 1 + Math.min(12, normalized.length || 1) * 0.06;

      let punctuationPause = 0;
      for (let probe = tokenIndex + 1; probe < textTokens.length; probe += 1) {
        const nextToken = textTokens[probe];
        if (/^\s+$/.test(nextToken.raw)) continue;
        if (/^[,.!?]$/.test(nextToken.raw)) punctuationPause = 0.55;
        else if (/^[;:]$/.test(nextToken.raw)) punctuationPause = 0.3;
        break;
      }

      const weight = lengthWeight + punctuationPause;
      weighted.push({
        index: token.wordPosition,
        startWeight: accumulatedWeight,
        endWeight: accumulatedWeight + weight,
      });
      accumulatedWeight += weight;
    }

    if (weighted.length === 0 || accumulatedWeight <= 0) return [];
    return weighted.map((row) => ({
      index: row.index,
      startRatio: row.startWeight / accumulatedWeight,
      endRatio: row.endWeight / accumulatedWeight,
    }));
  }, [textTokens]);

  const activeWordLabel = useMemo(() => {
    if (activeWordPosition === null || totalWordTokens === 0) return '—';
    return `${Math.min(totalWordTokens, activeWordPosition + 1)}/${totalWordTokens}`;
  }, [activeWordPosition, totalWordTokens]);

  const textAudioSource = useMemo(() => {
    if (!text?.audio_url) return null;
    if (Number.isFinite(text?.id) && Number(text.id) > 0) {
      return `${API_URL}/api/texts/${text.id}/audio`;
    }
    return resolveMediaUrl(text.audio_url);
  }, [text?.audio_url, text?.id]);

  const alignmentStatusLabel = useMemo(() => {
    if (isLoadingAudioAlignment) return 'Sincronia: analisando áudio...';
    if (audioWordTimings.length > 0 && audioAlignmentSource === 'transcription_words') {
      return 'Sincronia: precisa (timestamps por palavra)';
    }
    if (audioWordTimings.length > 0 && audioAlignmentSource === 'transcription_segments') {
      return 'Sincronia: boa (derivada por segmentos)';
    }
    return 'Sincronia: estimada pelo progresso do áudio';
  }, [audioAlignmentSource, audioWordTimings.length, isLoadingAudioAlignment]);

  const syncHighlightWithAudio = useCallback(() => {
    if (!followAudioWords) return;
    if (totalWordTokens === 0) return;

    const audio = audioRef.current;
    if (!audio) return;

    if (audioWordTimings.length > 0) {
      const exactWordPosition = findWordIndexByTime(audio.currentTime, audioWordTimings);
      if (exactWordPosition !== null) {
        setActiveWordPosition(Math.max(0, Math.min(totalWordTokens - 1, exactWordPosition)));
        return;
      }
    }

    if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;

    const progress = Math.min(1, Math.max(0, audio.currentTime / audio.duration));
    const estimatedWordPosition = findWordIndexByProgress(progress, estimatedWordTimings);
    const nextWordPosition =
      estimatedWordPosition !== null
        ? estimatedWordPosition
        : Math.min(totalWordTokens - 1, Math.floor(progress * totalWordTokens));
    setActiveWordPosition(Math.max(0, Math.min(totalWordTokens - 1, nextWordPosition)));
  }, [audioWordTimings, estimatedWordTimings, followAudioWords, totalWordTokens]);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!followAudioWords) {
      setActiveWordPosition(null);
    }
  }, [followAudioWords]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = playbackRate;
  }, [playbackRate]);

  useEffect(() => {
    if (!followAudioWords || activeWordPosition === null) return;
    const container = textReaderRef.current;
    if (!container) return;

    const activeWord = container.querySelector<HTMLElement>(`[data-word-position="${activeWordPosition}"]`);
    if (!activeWord) return;

    activeWord.scrollIntoView({
      behavior: 'smooth',
      block: 'nearest',
      inline: 'nearest',
    });
  }, [activeWordPosition, followAudioWords]);

  useEffect(() => {
    setActiveWordPosition(null);
    setAudioWordTimings([]);
    setAudioAlignmentSource('none');
  }, [text?.id]);

  useEffect(() => {
    if (!user || !text?.id || !text.audio_url) {
      setIsLoadingAudioAlignment(false);
      return;
    }

    let cancelled = false;

    const loadAudioAlignment = async () => {
      setIsLoadingAudioAlignment(true);
      try {
        const res = await api.get<AudioAlignmentResponse>(`/api/texts/${text.id}/audio-alignment`);
        if (cancelled) return;

        const payload = res.data;
        const source: AlignmentSource =
          payload?.source === 'transcription_words' || payload?.source === 'transcription_segments'
            ? payload.source
            : 'none';

        const alignedWords = Array.isArray(payload?.word_timings)
          ? payload.word_timings
              .filter(
                (item) =>
                  Number.isFinite(item?.index) &&
                  Number.isFinite(item?.start) &&
                  Number.isFinite(item?.end) &&
                  item.end > item.start
              )
              .map((item) => ({
                index: Number(item.index),
                word: String(item.word ?? ''),
                start: Number(item.start),
                end: Number(item.end),
              }))
          : [];

        setAudioAlignmentSource(source);
        setAudioWordTimings(alignedWords);
      } catch (e) {
        console.warn('Falha ao carregar alinhamento de áudio do texto', e);
        if (!cancelled) {
          setAudioAlignmentSource('none');
          setAudioWordTimings([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingAudioAlignment(false);
        }
      }
    };

    void loadAudioAlignment();

    return () => {
      cancelled = true;
    };
  }, [text?.audio_url, text?.id, user]);

  useEffect(() => {
    if (!shadowingRunning) return;
    const id = window.setInterval(() => {
      setShadowingSeconds((s) => s + 1);
    }, 1000);
    return () => window.clearInterval(id);
  }, [shadowingRunning]);

  const shadowingTimeLabel = useMemo(() => {
    const mm = String(Math.floor(shadowingSeconds / 60)).padStart(2, '0');
    const ss = String(shadowingSeconds % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  }, [shadowingSeconds]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/api/texts/${textId}`);
      setText(res.data);
    } catch (e) {
      console.error(e);
      toast.error('Erro ao carregar texto');
      router.push('/texts');
    } finally {
      setIsLoading(false);
    }
  }, [router, textId]);

  useEffect(() => {
    if (user && Number.isFinite(textId) && textId > 0) {
      void load();
    }
  }, [user, textId, load]);

  if (authLoading || isLoading || !text) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-50 transition-colors">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <div className="min-w-0 flex items-center gap-3">
            <Link
              href="/texts"
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition"
              aria-label="Voltar para textos"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="h-6 w-6 text-primary-600 dark:text-primary-400 shrink-0" />
              <div className="min-w-0">
                <p className="font-bold text-gray-900 dark:text-white truncate">{text.title}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Nível {text.level}</p>
              </div>
            </div>
          </div>

          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-4 py-6 sm:py-8">
        <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 sm:p-6 transition-colors">
          <div className="mb-5">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Leitura guiada com áudio</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
              Foque no áudio e acompanhe o texto com destaque automático em cada palavra.
            </p>
          </div>

          {text.audio_url ? (
            <div className="sticky top-[74px] z-20 mb-5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50/95 dark:bg-gray-900/85 backdrop-blur p-4 shadow-sm">
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2">Áudio da IA</p>
              <audio
                ref={audioRef}
                controls
                preload="none"
                className="w-full"
                onPlay={syncHighlightWithAudio}
                onLoadedMetadata={() => {
                  const audio = audioRef.current;
                  if (audio) {
                    audio.playbackRate = playbackRate;
                  }
                  syncHighlightWithAudio();
                }}
                onTimeUpdate={syncHighlightWithAudio}
                onSeeked={syncHighlightWithAudio}
                onEnded={() => {
                  setActiveWordPosition(null);
                  setShadowingRunning(false);
                }}
              >
                <source src={textAudioSource || undefined} />
              </audio>

              <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={followAudioWords}
                    onChange={(e) => setFollowAudioWords(e.target.checked)}
                  />
                  Acompanhar palavras com destaque automático
                </label>
                <div className="text-sm text-gray-700 dark:text-gray-300">
                  Palavra atual: <span className="font-semibold text-gray-900 dark:text-white">{activeWordLabel}</span>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-300">Velocidade</span>
                {[0.8, 0.9, 1.0].map((rate) => {
                  const selected = playbackRate === rate;
                  return (
                    <button
                      key={rate}
                      type="button"
                      onClick={() => setPlaybackRate(rate)}
                      className={`px-2.5 py-1 rounded-md text-sm border transition ${
                        selected
                          ? 'bg-primary-600 text-white border-primary-600'
                          : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-white dark:hover:bg-gray-800'
                      }`}
                    >
                      {rate.toFixed(1)}x
                    </button>
                  );
                })}

                <span className="text-sm text-gray-600 dark:text-gray-300">Timer de shadowing</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white rounded-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-2 py-1">
                  {shadowingTimeLabel}
                </span>
                <button
                  type="button"
                  onClick={() => setShadowingRunning((running) => !running)}
                  className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-white dark:hover:bg-gray-800 transition text-sm text-gray-800 dark:text-gray-100"
                >
                  {shadowingRunning ? 'Pausar' : 'Iniciar'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShadowingRunning(false);
                    setShadowingSeconds(0);
                  }}
                  className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-white dark:hover:bg-gray-800 transition text-sm text-gray-800 dark:text-gray-100"
                >
                  Zerar
                </button>
              </div>

              <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {alignmentStatusLabel}
                {audioWordTimings.length > 0 ? (
                  <span className="ml-2">({audioWordTimings.length} palavras sincronizadas)</span>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="mb-5 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/20 p-4">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                Este texto ainda não tem áudio cadastrado. O modo de destaque automático ficará disponível quando o
                áudio for gerado.
              </p>
            </div>
          )}

          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/35 p-4 sm:p-5">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Texto (EN)</h3>
            <div
              ref={textReaderRef}
              className="max-h-[62vh] overflow-y-auto pr-1 whitespace-pre-wrap leading-9 text-[1.08rem] sm:text-[1.2rem] text-gray-800 dark:text-gray-100"
            >
              {textTokens.map((token, idx) => {
                if (!token.isWord || token.wordPosition === null) {
                  return <span key={idx}>{token.raw}</span>;
                }

                const isActive = followAudioWords && activeWordPosition === token.wordPosition;
                const isPast =
                  followAudioWords && activeWordPosition !== null && token.wordPosition < activeWordPosition;

                return (
                  <span
                    key={idx}
                    data-word-position={token.wordPosition}
                    className={`rounded-sm transition-all duration-150 ${
                      isActive
                        ? 'bg-primary-200 dark:bg-primary-500/35 text-gray-900 dark:text-white shadow-[0_0_0_5px_rgba(59,130,246,0.28)] dark:shadow-[0_0_0_5px_rgba(59,130,246,0.35)]'
                        : isPast
                          ? 'text-gray-900 dark:text-gray-100'
                          : ''
                    }`}
                  >
                    {token.raw}
                  </span>
                );
              })}
            </div>
          </div>

          {text.content_pt ? (
            <details className="mt-5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/35 p-4 sm:p-5">
              <summary className="cursor-pointer list-none text-base font-semibold text-gray-900 dark:text-white">
                Tradução (PT)
              </summary>
              <div className="mt-3 whitespace-pre-wrap text-gray-700 dark:text-gray-300 leading-relaxed text-[15px] sm:text-base">
                {text.content_pt}
              </div>
            </details>
          ) : null}
        </section>
      </main>
    </div>
  );
}
