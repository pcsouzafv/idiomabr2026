'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { resolveMediaUrl } from '@/lib/media';
import { ArrowLeft, FileText, Loader2, Send } from 'lucide-react';
import toast from 'react-hot-toast';

type Task = 'writing' | 'summary' | 'translation';

interface StudyTextDetail {
  id: number;
  title: string;
  level: string;
  content_en: string;
  content_pt?: string | null;
  audio_url?: string | null;
  tags?: unknown;
}

interface AttemptResponse {
  id: number;
  text_id: number;
  task: string;
  user_text: string;
  ai_feedback?: string | null;
  model_used?: string | null;
}

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

  const [task, setTask] = useState<Task>('writing');
  const [userText, setUserText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<AttemptResponse | null>(null);

  const [shadowingSeconds, setShadowingSeconds] = useState(0);
  const [shadowingRunning, setShadowingRunning] = useState(false);
  const [shadowingChecks, setShadowingChecks] = useState({
    listenFollow: false,
    shadowSoft: false,
    shadowFaithful: false,
    readAloudSolo: false,
    repeatHardParts: false,
  });

  useEffect(() => {
    void fetchUser();
  }, [fetchUser]);

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

  const submit = async () => {
    if (!userText.trim()) return;

    setIsSubmitting(true);
    setFeedback(null);

    try {
      const res = await api.post(`/api/texts/${textId}/attempt`, {
        task,
        user_text: userText,
      });
      setFeedback(res.data);
      toast.success('Avaliação gerada!');
    } catch (e) {
      console.error(e);
      toast.error('Erro ao enviar resposta');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authLoading || isLoading || !text) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/texts" className="text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div className="flex items-center gap-2">
            <FileText className="h-6 w-6 text-primary-600" />
            <div>
              <p className="font-bold text-gray-900">{text.title}</p>
              <p className="text-xs text-gray-500">Nível {text.level}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-3">Texto (EN)</h2>

          {text.audio_url ? (
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Áudio</h3>
              <audio controls preload="none" className="w-full">
                <source src={resolveMediaUrl(text.audio_url) || undefined} />
              </audio>
              <p className="text-xs text-gray-500 mt-2">Dica: escute e acompanhe a leitura no texto.</p>
            </div>
          ) : null}

          <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-semibold text-gray-900">Modo Shadowing</p>
                <p className="text-sm text-gray-600">
                  Treine ritmo e fluência repetindo junto com o áudio (ou lendo em voz alta).
                </p>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">{shadowingTimeLabel}</span>
                <button
                  type="button"
                  onClick={() => setShadowingRunning((r) => !r)}
                  className="px-3 py-2 rounded-lg border border-gray-300 hover:bg-white transition text-gray-800"
                >
                  {shadowingRunning ? 'Pausar' : 'Iniciar'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShadowingRunning(false);
                    setShadowingSeconds(0);
                  }}
                  className="px-3 py-2 rounded-lg border border-gray-300 hover:bg-white transition text-gray-800"
                >
                  Zerar
                </button>
              </div>
            </div>

            {!text.audio_url ? (
              <p className="text-sm text-gray-600 mt-3">
                Este texto não tem áudio cadastrado. Você ainda pode praticar lendo em voz alta.
              </p>
            ) : null}

            <div className="mt-4 grid gap-2">
              <label className="flex items-start gap-2 text-gray-800">
                <input
                  type="checkbox"
                  checked={shadowingChecks.listenFollow}
                  onChange={(e) => setShadowingChecks((s) => ({ ...s, listenFollow: e.target.checked }))}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold">1)</span> Ouvir + acompanhar com os olhos (sem falar)
                </span>
              </label>
              <label className="flex items-start gap-2 text-gray-800">
                <input
                  type="checkbox"
                  checked={shadowingChecks.shadowSoft}
                  onChange={(e) => setShadowingChecks((s) => ({ ...s, shadowSoft: e.target.checked }))}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold">2)</span> Shadowing suave (1–2 palavras atrás, sem pausar)
                </span>
              </label>
              <label className="flex items-start gap-2 text-gray-800">
                <input
                  type="checkbox"
                  checked={shadowingChecks.shadowFaithful}
                  onChange={(e) => setShadowingChecks((s) => ({ ...s, shadowFaithful: e.target.checked }))}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold">3)</span> Shadowing fiel (copiar pausas e entonação)
                </span>
              </label>
              <label className="flex items-start gap-2 text-gray-800">
                <input
                  type="checkbox"
                  checked={shadowingChecks.readAloudSolo}
                  onChange={(e) => setShadowingChecks((s) => ({ ...s, readAloudSolo: e.target.checked }))}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold">4)</span> Ler em voz alta sem áudio (mesmo ritmo)
                </span>
              </label>
              <label className="flex items-start gap-2 text-gray-800">
                <input
                  type="checkbox"
                  checked={shadowingChecks.repeatHardParts}
                  onChange={(e) => setShadowingChecks((s) => ({ ...s, repeatHardParts: e.target.checked }))}
                  className="mt-1"
                />
                <span>
                  <span className="font-semibold">5)</span> Repetir 2–3 trechos que travaram (30–60s)
                </span>
              </label>
            </div>
          </div>

          <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">{text.content_en}</div>

          {text.content_pt ? (
            <>
              <h3 className="text-lg font-bold text-gray-900 mt-6 mb-3">Tradução (PT)</h3>
              <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">{text.content_pt}</div>
            </>
          ) : null}
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Sua prática</h2>

          <div className="grid md:grid-cols-3 gap-3 mb-4">
            <button
              onClick={() => setTask('writing')}
              className={`px-4 py-2 rounded-lg border transition ${
                task === 'writing'
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 hover:bg-gray-50 text-gray-700'
              }`}
            >
              Escrita
            </button>
            <button
              onClick={() => setTask('summary')}
              className={`px-4 py-2 rounded-lg border transition ${
                task === 'summary'
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 hover:bg-gray-50 text-gray-700'
              }`}
            >
              Resumo
            </button>
            <button
              onClick={() => setTask('translation')}
              className={`px-4 py-2 rounded-lg border transition ${
                task === 'translation'
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 hover:bg-gray-50 text-gray-700'
              }`}
            >
              Tradução
            </button>
          </div>

          <textarea
            value={userText}
            onChange={(e) => setUserText(e.target.value)}
            placeholder="Escreva sua resposta aqui..."
            className="w-full min-h-[160px] p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            disabled={isSubmitting}
          />

          <div className="flex justify-end mt-3">
            <button
              onClick={submit}
              disabled={isSubmitting || !userText.trim()}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
            >
              {isSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              Enviar
            </button>
          </div>

          {feedback?.ai_feedback ? (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between mb-2">
                <p className="font-semibold text-gray-800">Feedback da IA</p>
                {feedback.model_used ? (
                  <p className="text-xs text-gray-500">Modelo: {feedback.model_used}</p>
                ) : null}
              </div>
              <div className="whitespace-pre-wrap text-gray-700">{feedback.ai_feedback}</div>
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
