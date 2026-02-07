'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
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
  const { user, isLoading: authLoading } = useAuthStore();
  const router = useRouter();

  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [selectedSentence, setSelectedSentence] = useState<Sentence | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [levelFilter, setLevelFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');

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
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      void loadSentences();
    }
  }, [user]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isAskingAI, isAnalyzingSentence]);

  const levels = useMemo(
    () =>
      Array.from(new Set(sentences.map((s) => s.level).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b)
      ),
    [sentences]
  );

  const categories = useMemo(
    () =>
      Array.from(new Set(sentences.map((s) => s.category).filter(Boolean))).sort((a, b) =>
        a.localeCompare(b)
      ),
    [sentences]
  );

  const filteredSentences = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    return sentences.filter((sentence) => {
      const matchesLevel = levelFilter === 'all' || sentence.level === levelFilter;
      const matchesCategory = categoryFilter === 'all' || sentence.category === categoryFilter;
      const haystack = `${sentence.english} ${sentence.portuguese} ${sentence.category} ${sentence.level}`.toLowerCase();
      const matchesSearch = !query || haystack.includes(query);
      return matchesLevel && matchesCategory && matchesSearch;
    });
  }, [sentences, searchTerm, levelFilter, categoryFilter]);

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

  const loadSentences = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/api/sentences/', { params: { limit: 80 } });
      setSentences(response.data);
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao carregar frases');
    } finally {
      setIsLoading(false);
    }
  };

  const playAudio = async (text: string) => {
    try {
      setIsPlayingAudio(true);
      const response = await api.post(
        '/api/sentences/ai/speak',
        { text },
        { responseType: 'blob' }
      );

      const audioBlob = response.data as Blob;
      const objectUrl = URL.createObjectURL(audioBlob);

      const audio = new Audio(objectUrl);
      audio.onended = () => {
        setIsPlayingAudio(false);
        URL.revokeObjectURL(objectUrl);
      };
      audio.onerror = () => {
        setIsPlayingAudio(false);
        URL.revokeObjectURL(objectUrl);
      };
      await audio.play();
    } catch (error) {
      const status = getHttpStatus(error);
      if (status !== 503) {
        console.log('Audio playback not available:', error);
      }
      setIsPlayingAudio(false);
    }
  };

  const analyzeSentence = async (sentence: Sentence) => {
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
      void playAudio(message);
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

      void playAudio(assistantMessage);
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
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#dbeafe_0%,_#f8fafc_42%,_#e0e7ff_100%)]">
      <header className="sticky top-0 z-50 border-b border-white/60 bg-white/90 backdrop-blur-sm">
        <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-3 flex items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-primary-600" />
            <div>
              <p className="font-bold text-gray-900 leading-tight">Estudar Frases com IA</p>
              <p className="text-xs text-gray-500 leading-tight">Treine contexto, gramática e pronúncia</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6">
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(320px,430px)_1fr] gap-4 sm:gap-5">
          <section className="bg-white/90 backdrop-blur-sm rounded-2xl border border-white/70 shadow-sm p-4 sm:p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Frases Disponíveis
              </h2>
              <span className="text-xs px-2 py-1 rounded-lg bg-gray-100 text-gray-700">
                {filteredSentences.length} resultados
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Total</p>
                <p className="text-base font-bold text-gray-900">{sentences.length}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Níveis</p>
                <p className="text-base font-bold text-gray-900">{levels.length}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-2">
                <p className="text-xs text-gray-500">Temas</p>
                <p className="text-base font-bold text-gray-900">{categories.length}</p>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <div className="relative">
                <Search className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Buscar por inglês, português, nível ou categoria..."
                  className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-300"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="relative">
                  <SlidersHorizontal className="h-4 w-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <select
                    value={levelFilter}
                    onChange={(event) => setLevelFilter(event.target.value)}
                    className="w-full appearance-none pl-9 pr-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-300"
                  >
                    <option value="all">Todos os níveis</option>
                    {levels.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                </div>

                <select
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value)}
                  className="w-full appearance-none px-3 py-2.5 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-300"
                >
                  <option value="all">Todas as categorias</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
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
              <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-600">
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
                        ? 'border-primary-500 bg-primary-50 shadow-sm'
                        : 'border-gray-200 bg-white hover:border-primary-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-xs font-semibold px-2 py-1 bg-blue-100 text-blue-700 rounded-md">
                        {sentence.level}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">{sentence.category}</span>
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            void playAudio(sentence.english);
                          }}
                          className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-gray-100 text-gray-600 hover:bg-gray-200"
                          title="Ouvir frase"
                        >
                          <Volume2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="font-semibold text-gray-900 leading-snug">{sentence.english}</p>
                    <p className="text-sm text-gray-600 mt-1 leading-snug">{sentence.portuguese}</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="bg-white/90 backdrop-blur-sm rounded-2xl border border-white/70 shadow-sm p-4 sm:p-5 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg sm:text-xl font-bold text-gray-900 flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Professor de IA
              </h2>
              {selectedSentence ? (
                <span className="text-xs px-2 py-1 rounded-lg bg-emerald-100 text-emerald-700">
                  Frase ativa
                </span>
              ) : (
                <span className="text-xs px-2 py-1 rounded-lg bg-amber-100 text-amber-700">
                  Selecione uma frase
                </span>
              )}
            </div>

            {selectedSentence && (
              <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 mb-1">Frase selecionada</p>
                <p className="font-semibold text-blue-950">{selectedSentence.english}</p>
                <p className="text-sm text-blue-800 mt-1">{selectedSentence.portuguese}</p>
              </div>
            )}

            {selectedSentence && (
              <div className="mb-4 p-3 rounded-xl border border-gray-200 bg-gray-50">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Treinar pronúncia</p>
                    <p className="text-xs text-gray-600">Grave sua voz e receba feedback detalhado.</p>
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
                      className="px-3 py-2 rounded-lg bg-gray-900 text-white hover:bg-gray-800 transition inline-flex items-center gap-2"
                    >
                      <Square className="h-4 w-4" />
                      Parar
                    </button>
                  )}
                </div>

                {isAnalyzingPronunciation ? (
                  <div className="mt-3 text-sm text-gray-600 inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analisando áudio...
                  </div>
                ) : null}

                {isRecording ? (
                  <div className="mt-3">
                    <p className="text-xs text-gray-600 mb-1">Nível do microfone</p>
                    <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden">
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
                      <p className="text-xs font-semibold text-gray-700">Transcrição (STT)</p>
                      <p className="text-sm text-gray-800">{pronunciationResult.transcript || '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-700">Similaridade</p>
                      <p className="text-sm text-gray-800">
                        {pronunciationResult.similarity === null ? '—' : `${pronunciationResult.similarity}%`}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-gray-700">Feedback</p>
                      <div className="whitespace-pre-wrap text-sm text-gray-800">{pronunciationResult.feedback}</div>
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
                  className="shrink-0 text-xs px-3 py-1.5 rounded-full border border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="flex-1 min-h-[360px] max-h-[58vh] overflow-y-auto rounded-xl border border-gray-200 bg-gray-50 p-3 sm:p-4">
              {isAnalyzingSentence ? (
                <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-gray-600">
                  <Loader2 className="h-8 w-8 animate-spin mb-2 text-primary-600" />
                  Sarah está analisando a frase...
                </div>
              ) : chatMessages.length === 0 ? (
                <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-gray-400">
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
                            : 'bg-white border border-gray-200 text-gray-800'
                        }`}
                      >
                        {message.content}
                      </div>
                    </div>
                  ))}
                  {isAskingAI && (
                    <div className="flex justify-start">
                      <div className="inline-flex items-center gap-2 rounded-2xl border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600">
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
                  onClick={() => void playAudio(aiResponse)}
                  disabled={isPlayingAudio}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm bg-primary-100 text-primary-700 hover:bg-primary-200 disabled:opacity-50"
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
                className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-white resize-none focus:outline-none focus:ring-2 focus:ring-primary-300"
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

            <p className="mt-2 text-xs text-gray-500 text-center">
              A Professora Sarah conversa com você e pode responder em áudio. Use Enter para enviar.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
