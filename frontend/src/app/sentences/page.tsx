'use client';

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import ThemeToggle from '@/components/ThemeToggle';
import {
  ArrowLeft,
  Brain,
  MessageSquare,
  BookOpen,
  Loader2,
  Send,
  Sparkles,
  Volume2,
  Mic,
  Square,
  Search,
  SlidersHorizontal,
} from 'lucide-react';
import toast from 'react-hot-toast';

type AxiosLikeError = {
  response?: {
    status?: number;
  };
};

function getHttpStatus(error: unknown): number | undefined {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    return (error as AxiosLikeError).response?.status;
  }
  return undefined;
}

interface Sentence {
  id: number;
  english: string;
  portuguese: string;
  level: string;
  category: string;
}

interface FilterOption {
  value: string;
  count: number;
}

interface FiltersData {
  total: number;
  levels: FilterOption[];
  categories: FilterOption[];
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const QUICK_PROMPTS = [
  'Explain this sentence in simple English.',
  'Give me 3 similar examples I can use today.',
  'What grammar pattern is used here?',
  'Create a mini dialogue using this sentence.',
];

export default function SentencesPage() {
  const { user, isLoading: authLoading, fetchUser } = useAuthStore();
  const router = useRouter();

  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [filtersData, setFiltersData] = useState<FiltersData | null>(null);
  const [selectedSentence, setSelectedSentence] = useState<Sentence | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const [userMessage, setUserMessage] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [aiResponse, setAiResponse] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzingSentence, setIsAnalyzingSentence] = useState(false);
  const [isAskingAI, setIsAskingAI] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const browserUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const ttsAudioUrlRef = useRef<string | null>(null);
  const rafRef = useRef<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzingPronunciation, setIsAnalyzingPronunciation] = useState(false);
  const [pronunciationResult, setPronunciationResult] = useState<null | {
    transcript: string;
    similarity: number | null;
    feedback: string;
  }>(null);

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAskingAI, isAnalyzingSentence]);

  const stopBrowserSpeech = useCallback(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    browserUtteranceRef.current = null;
  }, []);

  const speakWithBrowser = useCallback(
    (text: string, language: 'en-US' | 'pt-BR' = 'en-US') => {
      const normalizedText = text.trim();
      if (!normalizedText) return;

      if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        toast.error('Seu navegador não suporta leitura de áudio');
        return;
      }

      stopBrowserSpeech();

      const utterance = new SpeechSynthesisUtterance(normalizedText);
      utterance.lang = language;
      utterance.rate = language === 'en-US' ? 0.9 : 1;

      const voices = window.speechSynthesis.getVoices();
      const preferredVoice =
        voices.find((voice) => voice.lang.toLowerCase().startsWith(language.toLowerCase())) ||
        voices.find((voice) => voice.lang.toLowerCase().startsWith(language.slice(0, 2).toLowerCase()));
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.onend = () => {
        if (browserUtteranceRef.current === utterance) {
          browserUtteranceRef.current = null;
        }
      };

      utterance.onerror = () => {
        if (browserUtteranceRef.current === utterance) {
          browserUtteranceRef.current = null;
        }
      };

      browserUtteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [stopBrowserSpeech]
  );

  const cleanupTtsAudio = useCallback(() => {
    const audio = ttsAudioRef.current;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      try {
        audio.pause();
        audio.removeAttribute('src');
        audio.load();
      } catch {
        // ignore
      }
    }
    ttsAudioRef.current = null;

    if (ttsAudioUrlRef.current) {
      URL.revokeObjectURL(ttsAudioUrlRef.current);
      ttsAudioUrlRef.current = null;
    }
  }, []);

  const stopAudioPlayback = useCallback(() => {
    cleanupTtsAudio();
    setIsPlayingAudio(false);
  }, [cleanupTtsAudio]);

  const speakWithAI = useCallback(async (text: string) => {
    const normalizedText = text.trim();
    if (!normalizedText) return;

    stopBrowserSpeech();
    stopAudioPlayback();
    setIsPlayingAudio(true);

    try {
      const response = await api.post('/api/sentences/ai/speak', { text: normalizedText }, { responseType: 'blob' });
      const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
      const audioUrl = URL.createObjectURL(audioBlob);
      ttsAudioUrlRef.current = audioUrl;

      const audio = new Audio(audioUrl);
      ttsAudioRef.current = audio;

      audio.onended = () => {
        cleanupTtsAudio();
        setIsPlayingAudio(false);
      };
      audio.onerror = () => {
        cleanupTtsAudio();
        setIsPlayingAudio(false);
        toast.error('Não foi possível reproduzir o áudio da IA');
      };

      await audio.play();
    } catch (error) {
      console.error('Erro ao gerar áudio da IA:', error);
      const status = getHttpStatus(error);
      stopAudioPlayback();
      if (status === 503 || status === 400) {
        toast.error('TTS da IA indisponível. Verifique OPENAI_API_KEY ou LEMONFOX_API_KEY.');
      } else if (status === 429) {
        toast.error('TTS da IA no limite de uso agora. Tente novamente em instantes.');
      } else {
        toast.error('Erro ao gerar áudio da IA');
      }
    }
  }, [cleanupTtsAudio, stopAudioPlayback, stopBrowserSpeech]);

  useEffect(() => {
    return () => {
      stopBrowserSpeech();
      stopAudioPlayback();
    };
  }, [stopAudioPlayback, stopBrowserSpeech]);

  const levels = useMemo(
    () => filtersData?.levels ?? [],
    [filtersData]
  );

  const categories = useMemo(
    () => filtersData?.categories ?? [],
    [filtersData]
  );

  const filteredSentences = sentences;

  const cleanupMedia = () => {
    try {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    } catch {
      // ignore
    }
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    analyserRef.current = null;
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {
        // ignore
      }
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  };

  const PAGE_SIZE = 50;

  const loadFilters = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (levelFilter !== 'all') params.level = levelFilter;
      if (categoryFilter !== 'all') params.category = categoryFilter;
      const response = await api.get('/api/sentences/filters', { params });
      setFiltersData(response.data);
    } catch (error) {
      console.error('Erro ao carregar filtros:', error);
    }
  }, [levelFilter, categoryFilter]);

  const loadSentences = useCallback(async (
    options?: { append?: boolean; offset?: number }
  ) => {
    const append = options?.append ?? false;
    const offset = options?.offset ?? 0;
    if (!append) {
      setIsLoading(true);
    } else {
      setLoadingMore(true);
    }
    try {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        skip: append ? offset : 0,
        mode: 'all',
      };
      if (levelFilter !== 'all') params.level = levelFilter;
      if (categoryFilter !== 'all') params.category = categoryFilter;
      if (searchTerm) params.search = searchTerm;

      const response = await api.get('/api/sentences/', { params });
      const data: Sentence[] = response.data;

      if (append) {
        setSentences((prev) => [...prev, ...data]);
      } else {
        setSentences(data);
      }
      setHasMore(data.length >= PAGE_SIZE);
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao carregar frases');
    } finally {
      setIsLoading(false);
      setLoadingMore(false);
    }
  }, [categoryFilter, levelFilter, searchTerm]);

  // Debounced search keeps typing responsive and avoids excessive requests.
  useEffect(() => {
    const timer = setTimeout(() => {
      const normalizedSearch = searchInput.trim();
      setSearchTerm((prev) => (prev === normalizedSearch ? prev : normalizedSearch));
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!user) return;
    void loadFilters();
  }, [user, loadFilters]);

  useEffect(() => {
    if (!user) return;
    void loadSentences();
  }, [user, loadSentences]);

  const loadMore = () => {
    if (!loadingMore && hasMore) {
      void loadSentences({ append: true, offset: sentences.length });
    }
  };

  const analyzeSentence = async (sentence: Sentence) => {
    stopBrowserSpeech();
    stopAudioPlayback();
    setSelectedSentence(sentence);
    setAiResponse('');
    setChatMessages([]);
    setPronunciationResult(null);
    setIsAnalyzingSentence(true);

    try {
      const response = await api.post(`/api/sentences/ai/analyze/${sentence.id}`);
      const message = String(response.data.response || '');
      setAiResponse(message);
      setChatMessages([
        {
          id: `${Date.now()}-intro`,
          role: 'assistant',
          content: message,
        },
      ]);
      toast.success('Professora Sarah está pronta!');
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao analisar frase');
    } finally {
      setIsAnalyzingSentence(false);
    }
  };

  const stopRecorder = () => {
    try {
      mediaRecorderRef.current?.stop();
    } catch {
      // ignore
    }
  };

  const startRecording = async () => {
    if (!selectedSentence) {
      toast.error('Selecione uma frase primeiro');
      return;
    }

    setPronunciationResult(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const preferredTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
      const mimeType = preferredTypes.find(
        (type) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)
      );

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateMeter = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteTimeDomainData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i += 1) {
          const normalized = (dataArray[i] - 128) / 128;
          sum += normalized * normalized;
        }
        const rms = Math.sqrt(sum / dataArray.length);
        setAudioLevel(Math.min(100, Math.round(rms * 200)));
        rafRef.current = requestAnimationFrame(updateMeter);
      };
      updateMeter();

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        setIsRecording(false);
        setIsAnalyzingPronunciation(true);
        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
          if (!blob || blob.size < 800) {
            toast.error('Áudio muito curto ou sem som. Tente novamente.');
            return;
          }
          const formData = new FormData();
          formData.append('audio', blob, 'pronunciation.webm');
          formData.append('expected_text', selectedSentence.english);

          const response = await api.post(
            `/api/sentences/ai/pronunciation/${selectedSentence.id}`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );

          setPronunciationResult({
            transcript: response.data.transcript,
            similarity: response.data.similarity ?? null,
            feedback: response.data.feedback,
          });
          toast.success('Análise de pronúncia pronta!');
        } catch (error) {
          console.error(error);
          const status = getHttpStatus(error);
          if (status === 400) {
            toast.error('Áudio inválido/sem conteúdo. Grave novamente.');
          } else {
            toast.error('Erro ao analisar pronúncia');
          }
        } finally {
          setIsAnalyzingPronunciation(false);
          cleanupMedia();
        }
      };

      recorder.start(250);
      setIsRecording(true);
      toast.success('Gravando...');
    } catch (error) {
      console.error(error);
      toast.error('Não foi possível acessar o microfone');
      cleanupMedia();
    }
  };

  const askAI = async () => {
    const message = userMessage.trim();
    if (!message) return;

    const userChatMessage: ChatMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: message,
    };

    setUserMessage('');
    setIsAskingAI(true);
    setChatMessages((prev) => [...prev, userChatMessage]);

    try {
      const response = await api.post('/api/sentences/ai/ask', {
        sentence_id: selectedSentence?.id,
        user_message: message,
        include_context: !!selectedSentence,
      });

      const assistantMessage = String(response.data.response || '');
      setAiResponse(assistantMessage);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-assistant`,
          role: 'assistant',
          content: assistantMessage,
        },
      ]);
      toast.success('Sarah respondeu!');
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao perguntar à IA');
    } finally {
      setIsAskingAI(false);
    }
  };

  const handleMessageKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void askAI();
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 transition-colors">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#dbeafe_0%,_#f8fafc_42%,_#e0e7ff_100%)] dark:bg-[radial-gradient(circle_at_top,_#0f172a_0%,_#020617_45%,_#111827_100%)] transition-colors">
      <header className="sticky top-0 z-50 border-b border-white/60 bg-white/90 dark:border-slate-800/70 dark:bg-slate-950/85 backdrop-blur-sm transition-colors">
        <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white transition"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary-600 dark:text-primary-400" />
              <div>
                <p className="font-bold text-gray-900 dark:text-white leading-tight">Estudar Frases com IA</p>
                <p className="text-xs text-gray-500 dark:text-gray-300 leading-tight">Treine contexto, gramática e pronúncia</p>
              </div>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6">
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(320px,430px)_1fr] gap-4 sm:gap-5">
          <section className="bg-white/90 dark:bg-slate-900/85 backdrop-blur-sm rounded-2xl border border-white/70 dark:border-slate-700/70 shadow-sm p-4 sm:p-5 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Frases Disponíveis
              </h2>
              <span className="text-xs px-2 py-1 rounded-lg bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-200">
                {filteredSentences.length} resultados
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/70 px-3 py-2 transition-colors">
                <p className="text-xs text-gray-500 dark:text-gray-400">Total</p>
                <p className="text-base font-bold text-gray-900 dark:text-gray-100">{filtersData?.total ?? sentences.length}</p>
              </div>
              <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/70 px-3 py-2 transition-colors">
                <p className="text-xs text-gray-500 dark:text-gray-400">Níveis</p>
                <p className="text-base font-bold text-gray-900 dark:text-gray-100">{levels.length}</p>
              </div>
              <div className="rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/70 px-3 py-2 transition-colors">
                <p className="text-xs text-gray-500 dark:text-gray-400">Temas</p>
                <p className="text-base font-bold text-gray-900 dark:text-gray-100">{categories.length}</p>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <div className="relative">
                <Search className="h-4 w-4 text-gray-400 dark:text-gray-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Buscar por inglês, português, nível ou categoria..."
                  className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-300"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="relative">
                  <SlidersHorizontal className="h-4 w-4 text-gray-400 dark:text-gray-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <select
                    title="Filtrar por nível"
                    value={levelFilter}
                    onChange={(event) => setLevelFilter(event.target.value)}
                    className="w-full appearance-none pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-300"
                  >
                    <option value="all">Todos os níveis</option>
                    {levels.map((lv) => (
                      <option key={lv.value} value={lv.value}>
                        {lv.value} ({lv.count})
                      </option>
                    ))}
                  </select>
                </div>

                <select
                  title="Filtrar por categoria"
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value)}
                  className="w-full appearance-none px-3 py-2.5 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-300"
                >
                  <option value="all">Todas as categorias</option>
                  {categories.map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.value} ({cat.count})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {isLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
              </div>
            ) : filteredSentences.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/70 p-6 text-center text-sm text-gray-600 dark:text-gray-300 transition-colors">
                Nenhuma frase encontrada para o filtro atual.
              </div>
            ) : (
              <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
                {filteredSentences.map((sentence) => (
                  <div
                    key={sentence.id}
                    onClick={() => void analyzeSentence(sentence)}
                    className={`rounded-xl border p-3 cursor-pointer transition ${
                      selectedSentence?.id === sentence.id
                        ? 'border-primary-500 dark:border-primary-400 bg-primary-50 dark:bg-primary-500/20 shadow-sm'
                        : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:border-primary-300 dark:hover:border-primary-500 hover:bg-gray-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-xs font-semibold px-2 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-200 rounded-md">
                        {sentence.level}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 dark:text-gray-400">{sentence.category}</span>
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            speakWithBrowser(sentence.english, 'en-US');
                          }}
                          className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-slate-700"
                          title="Ouvir frase"
                        >
                          <Volume2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="font-semibold text-gray-900 dark:text-white leading-snug">{sentence.english}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 leading-snug">{sentence.portuguese}</p>
                  </div>
                ))}

                {hasMore && (
                  <button
                    onClick={loadMore}
                    disabled={loadingMore}
                    className="w-full py-2.5 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-800 transition disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {loadingMore ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Carregando...
                      </>
                    ) : (
                      `Carregar mais frases (${sentences.length} de ${filtersData?.total ?? '...'})`
                    )}
                  </button>
                )}
              </div>
            )}
          </section>

          <section className="bg-white/90 dark:bg-slate-900/85 backdrop-blur-sm rounded-2xl border border-white/70 dark:border-slate-700/70 shadow-sm p-4 sm:p-5 flex flex-col transition-colors">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Professor de IA
              </h2>
              {selectedSentence ? (
                <span className="text-xs px-2 py-1 rounded-lg bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
                  Frase ativa
                </span>
              ) : (
                <span className="text-xs px-2 py-1 rounded-lg bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                  Selecione uma frase
                </span>
              )}
            </div>

            {selectedSentence && (
              <div className="mb-4 rounded-xl border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 p-3 transition-colors">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-200 mb-1">Frase selecionada</p>
                <p className="font-semibold text-blue-950 dark:text-blue-100">{selectedSentence.english}</p>
                <p className="text-sm text-blue-800 dark:text-blue-200 mt-1">{selectedSentence.portuguese}</p>
              </div>
            )}

            {selectedSentence && (
              <div className="mb-4 p-3 rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/70 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">Treinar pronúncia</p>
                    <p className="text-xs text-gray-600 dark:text-gray-300">Grave sua voz e receba feedback detalhado.</p>
                  </div>
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      disabled={isAnalyzingPronunciation}
                      className="px-3 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 transition inline-flex items-center gap-2"
                    >
                      <Mic className="h-4 w-4" />
                      Gravar
                    </button>
                  ) : (
                    <button
                      onClick={stopRecorder}
                      className="px-3 py-2 rounded-lg bg-gray-900 text-white hover:bg-gray-800 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-gray-200 transition inline-flex items-center gap-2"
                    >
                      <Square className="h-4 w-4" />
                      Parar
                    </button>
                  )}
                </div>

                {isAnalyzingPronunciation ? (
                  <div className="mt-3 text-sm text-gray-600 dark:text-gray-300 inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analisando áudio...
                  </div>
                ) : null}

                {isRecording ? (
                  <div className="mt-3">
                    <p className="text-xs text-gray-600 dark:text-gray-300 mb-1">Nível do microfone</p>
                    <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-slate-700 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-500 transition-[width] duration-100"
                        style={{ width: `${Math.max(6, audioLevel)}%` }}
                      />
                    </div>
                  </div>
                ) : null}

                {pronunciationResult ? (
                  <div className="mt-4 space-y-3">
                    <div>
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">Transcrição (STT)</p>
                      <p className="text-sm text-gray-800 dark:text-gray-100">{pronunciationResult.transcript || '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">Similaridade</p>
                      <p className="text-sm text-gray-800 dark:text-gray-100">
                        {pronunciationResult.similarity === null ? '—' : `${pronunciationResult.similarity}%`}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">Feedback</p>
                      <div className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-100">{pronunciationResult.feedback}</div>
                    </div>
                  </div>
                ) : null}
              </div>
            )}

            <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setUserMessage(prompt)}
                  className="shrink-0 text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-slate-800"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="flex-1 min-h-[360px] max-h-[58vh] overflow-y-auto rounded-xl border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/70 p-3 sm:p-4 transition-colors">
              {isAnalyzingSentence ? (
                <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-gray-600 dark:text-gray-300">
                  <Loader2 className="h-8 w-8 animate-spin mb-2 text-primary-600" />
                  Sarah está analisando a frase...
                </div>
              ) : chatMessages.length === 0 ? (
                <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-gray-400 dark:text-gray-500">
                  <Sparkles className="h-12 w-12 mb-2" />
                  <p className="text-center max-w-md">
                    Selecione uma frase e comece a conversar com a Professora Sarah.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[92%] sm:max-w-[82%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed ${
                          message.role === 'user'
                            ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
                            : 'bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 text-gray-800 dark:text-gray-100'
                        }`}
                      >
                        {message.content}
                      </div>
                    </div>
                  ))}
                  {isAskingAI && (
                    <div className="flex justify-start">
                      <div className="inline-flex items-center gap-2 rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-2 text-sm text-gray-600 dark:text-gray-200">
                        <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                        Sarah está respondendo...
                      </div>
                    </div>
                  )}
                  <div ref={chatEndRef} />
                </div>
              )}
            </div>

            {aiResponse && (
              <div className="mt-3 flex justify-end">
                <button
                  onClick={() => void speakWithAI(aiResponse)}
                  disabled={isPlayingAudio}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm bg-primary-100 dark:bg-primary-500/20 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-500/30 disabled:opacity-50 transition-colors"
                >
                  {isPlayingAudio ? (
                    <>
                      <Volume2 className="h-4 w-4 animate-pulse" />
                      Falando...
                    </>
                  ) : (
                    <>
                      <Volume2 className="h-4 w-4" />
                      Ouvir resposta
                    </>
                  )}
                </button>
              </div>
            )}

            <div className="mt-3 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2">
              <textarea
                value={userMessage}
                onChange={(event) => setUserMessage(event.target.value)}
                onKeyDown={handleMessageKeyDown}
                placeholder={
                  selectedSentence
                    ? 'Pergunte sobre a frase, gramática, pronúncia ou contexto...'
                    : 'Você também pode conversar sem frase selecionada...'
                }
                className="w-full px-4 py-3 rounded-xl border border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 resize-none focus:outline-none focus:ring-2 focus:ring-primary-300"
                rows={2}
                disabled={isAskingAI || isAnalyzingSentence}
              />
              <button
                onClick={() => void askAI()}
                disabled={isAskingAI || isAnalyzingSentence || !userMessage.trim()}
                className="px-4 py-3 rounded-xl bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition inline-flex items-center justify-center gap-2"
              >
                {isAskingAI ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                <span className="sm:hidden">Enviar</span>
              </button>
            </div>

            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
              A Professora Sarah conversa com você e pode responder em áudio. Use Enter para enviar.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
