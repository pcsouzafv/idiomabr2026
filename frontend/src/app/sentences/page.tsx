'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { ArrowLeft, Brain, MessageSquare, BookOpen, Loader2, Send, Sparkles, Volume2, Mic, Square } from 'lucide-react';
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

export default function SentencesPage() {
  const { user, isLoading: authLoading } = useAuthStore();
  const router = useRouter();

  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [selectedSentence, setSelectedSentence] = useState<Sentence | null>(null);
  const [userMessage, setUserMessage] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

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
      loadSentences();
    }
  }, [user]);

  const loadSentences = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/api/sentences/', { params: { limit: 20 } });
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
      audio.play();
    } catch (error) {
      // Se for erro 503, significa que TTS não está configurado
      const status = getHttpStatus(error);
      if (status === 503) {
        console.log('TTS não disponível - OpenAI API Key não configurada');
      } else {
        console.log('Audio playback not available:', error);
      }
      setIsPlayingAudio(false);
    }
  };

  const analyzeSentence = async (sentence: Sentence) => {
    setSelectedSentence(sentence);
    setAiResponse('');
    setPronunciationResult(null);
    setIsSendingMessage(true);

    try {
      const response = await api.post(`/api/sentences/ai/analyze/${sentence.id}`);
      setAiResponse(response.data.response);

      // Reproduzir áudio automaticamente
      playAudio(response.data.response);

      toast.success('Professora Sarah está aqui!');
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao analisar frase');
    } finally {
      setIsSendingMessage(false);
    }
  };

  const stopRecorder = () => {
    try {
      mediaRecorderRef.current?.stop();
    } catch {
      // ignore
    }
  };

  const cleanupMedia = () => {
    try {
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    } catch {
      // ignore
    }
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
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
      const mimeType = preferredTypes.find((t) => (window as any).MediaRecorder?.isTypeSupported?.(t));

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        setIsRecording(false);
        setIsAnalyzingPronunciation(true);
        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
          const formData = new FormData();
          formData.append('audio', blob, 'pronunciation.webm');
          formData.append('expected_text', selectedSentence.english);

          const res = await api.post(`/api/sentences/ai/pronunciation/${selectedSentence.id}`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });

          setPronunciationResult({
            transcript: res.data.transcript,
            similarity: res.data.similarity ?? null,
            feedback: res.data.feedback,
          });
          toast.success('Análise de pronúncia pronta!');
        } catch (e) {
          console.error(e);
          toast.error('Erro ao analisar pronúncia');
        } finally {
          setIsAnalyzingPronunciation(false);
          cleanupMedia();
        }
      };

      recorder.start();
      setIsRecording(true);
      toast.success('Gravando...');
    } catch (e) {
      console.error(e);
      toast.error('Não foi possível acessar o microfone');
      cleanupMedia();
    }
  };

  const askAI = async () => {
    if (!userMessage.trim()) return;

    setIsSendingMessage(true);
    setAiResponse('');

    try {
      const response = await api.post('/api/sentences/ai/ask', {
        sentence_id: selectedSentence?.id,
        user_message: userMessage,
        include_context: !!selectedSentence,
      });

      setAiResponse(response.data.response);
      setUserMessage('');

      // Reproduzir áudio da resposta
      playAudio(response.data.response);

      toast.success('Sarah respondeu!');
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao perguntar à IA');
    } finally {
      setIsSendingMessage(false);
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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/dashboard" className="text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="flex items-center gap-2">
            <Brain className="h-6 w-6 text-primary-600" />
            <span className="font-bold text-gray-900">Estudar Frases com IA</span>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Lista de Frases */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Frases Disponíveis
            </h2>

            {isLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto">
                {sentences.map((sentence) => (
                  <div
                    key={sentence.id}
                    onClick={() => analyzeSentence(sentence)}
                    className={`p-4 border rounded-lg cursor-pointer transition ${
                      selectedSentence?.id === sentence.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-xs font-semibold px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        {sentence.level}
                      </span>
                      <span className="text-xs text-gray-500">{sentence.category}</span>
                    </div>
                    <p className="font-medium text-gray-900 mb-1">{sentence.english}</p>
                    <p className="text-sm text-gray-600">{sentence.portuguese}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Professor IA */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Professor de IA
            </h2>

            {selectedSentence && (
              <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm font-semibold text-blue-900 mb-1">Frase selecionada:</p>
                <p className="text-sm text-blue-800">{selectedSentence.english}</p>
              </div>
            )}

            {/* Pronúncia */}
            {selectedSentence && (
              <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">Treinar pronúncia</p>
                    <p className="text-xs text-gray-600">Grave sua voz e receba feedback (fica salvo no banco).</p>
                  </div>
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      disabled={isAnalyzingPronunciation}
                      className="px-3 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2"
                    >
                      <Mic className="h-4 w-4" />
                      Gravar
                    </button>
                  ) : (
                    <button
                      onClick={stopRecorder}
                      className="px-3 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition flex items-center gap-2"
                    >
                      <Square className="h-4 w-4" />
                      Parar
                    </button>
                  )}
                </div>

                {isAnalyzingPronunciation ? (
                  <div className="mt-3 flex items-center gap-2 text-sm text-gray-600">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analisando áudio...
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

            {/* Resposta da IA */}
            <div className="mb-4">
              {aiResponse && (
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                    <Brain className="h-4 w-4 text-primary-600" />
                    Professora Sarah
                  </span>
                  <button
                    onClick={() => playAudio(aiResponse)}
                    disabled={isPlayingAudio}
                    className="flex items-center gap-2 px-3 py-1 text-sm bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200 disabled:opacity-50 transition"
                  >
                    {isPlayingAudio ? (
                      <>
                        <Volume2 className="h-4 w-4 animate-pulse" />
                        Falando...
                      </>
                    ) : (
                      <>
                        <Volume2 className="h-4 w-4" />
                        Ouvir novamente
                      </>
                    )}
                  </button>
                </div>
              )}
              <div className="min-h-[300px] max-h-[400px] overflow-y-auto p-4 bg-gray-50 rounded-lg border border-gray-200">
                {isSendingMessage ? (
                  <div className="flex flex-col items-center justify-center h-[250px]">
                    <Loader2 className="h-8 w-8 animate-spin text-primary-600 mb-2" />
                    <p className="text-gray-600">Sarah está pensando...</p>
                  </div>
                ) : aiResponse ? (
                  <div className="prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap text-gray-700">{aiResponse}</div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-[250px] text-gray-400">
                    <Sparkles className="h-12 w-12 mb-2" />
                    <p className="text-center">
                      Selecione uma frase e comece a conversar com a Professora Sarah!
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Input de Mensagem */}
            <div className="flex gap-2">
              <input
                type="text"
                value={userMessage}
                onChange={(e) => setUserMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && askAI()}
                placeholder="Faça uma pergunta sobre a frase..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                disabled={isSendingMessage}
              />
              <button
                onClick={askAI}
                disabled={isSendingMessage || !userMessage.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
              >
                {isSendingMessage ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </button>
            </div>

            <p className="mt-2 text-xs text-gray-500 text-center">
              A Professora Sarah vai conversar com você e até falar em voz alta! 🎙️
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
