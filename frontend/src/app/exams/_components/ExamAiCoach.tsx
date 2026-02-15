'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { conversationApi, examsAiApi } from '@/lib/api';

type ExamQuestion = {
  id: string;
  type: string;
  prompt: string;
  options?: string[] | null;
};

type AnalyzeResult = {
  estimated_score?: string | null;
  overall_feedback: string;
  strengths?: string[];
  weaknesses?: string[];
  study_plan?: string[];
  motivation?: string | null;
  per_question?: Array<{ id: string; feedback: string; improved_answer?: string | null }>;
};

type HistoryEntry = {
  at: string; // ISO
  exam: string;
  skill: string;
  estimated_score?: string | null;
  overall_feedback: string;
  strengths?: string[];
  weaknesses?: string[];
  study_plan?: string[];
  motivation?: string | null;
};

type PronunciationApiResponse = {
  transcript?: string;
  similarity?: number | null;
  feedback?: string;
};

type SpeakingAssessment = {
  transcript: string;
  similarity: number | null;
  feedback: string;
};

const isSpeakingType = (value: string) => {
  const normalized = (value || '').toLowerCase();
  return normalized === 'speaking' || normalized.includes('speaking');
};

export default function ExamAiCoach({
  exam,
  defaultSkill = 'mixed',
}: {
  exam: string;
  defaultSkill?: string;
}) {
  const [skill, setSkill] = useState(defaultSkill);
  const [numQuestions, setNumQuestions] = useState(5);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [instructions, setInstructions] = useState<string | null>(null);
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [answersById, setAnswersById] = useState<Record<string, string>>({});
  const [speakingById, setSpeakingById] = useState<Record<string, SpeakingAssessment>>({});
  const [recordingQuestionId, setRecordingQuestionId] = useState<string | null>(null);
  const [processingQuestionId, setProcessingQuestionId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const activeSpeakingQuestionRef = useRef<string | null>(null);

  const canAnalyze = useMemo(() => {
    if (!questions.length) return false;
    // allow analysis even if some answers blank, but require at least one answer
    return Object.values(answersById).some((v) => (v || '').trim().length > 0);
  }, [questions.length, answersById]);

  const getErrorMessage = useCallback((e: unknown, fallback: string) => {
    if (typeof e === 'object' && e !== null) {
      const maybeResponse = (e as { response?: { data?: { detail?: unknown } } }).response;
      const detail = maybeResponse?.data?.detail;
      if (typeof detail === 'string' && detail.trim()) return detail;
    }
    return fallback;
  }, []);

  const stopMediaTracks = useCallback(() => {
    try {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    } catch {
      // ignore
    }
    mediaStreamRef.current = null;
  }, []);

  const cleanupRecorderState = useCallback(() => {
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    activeSpeakingQuestionRef.current = null;
  }, []);

  const historyKey = useMemo(() => `exam_ai_history:${exam}:${skill}`, [exam, skill]);

  useEffect(() => {
    setSkill(defaultSkill);
  }, [defaultSkill, exam]);

  useEffect(() => {
    return () => {
      try {
        const recorder = mediaRecorderRef.current;
        if (recorder && recorder.state !== 'inactive') {
          recorder.stop();
        }
      } catch {
        // ignore
      }
      stopMediaTracks();
      cleanupRecorderState();
    };
  }, [cleanupRecorderState, stopMediaTracks]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(historyKey);
      if (!raw) {
        setHistory([]);
        return;
      }
      const parsed = JSON.parse(raw) as unknown;
      if (!Array.isArray(parsed)) {
        setHistory([]);
        return;
      }
      const cleaned: HistoryEntry[] = parsed
        .filter((x) => typeof x === 'object' && x !== null)
        .map((x) => x as HistoryEntry)
        .filter((x) => typeof x.at === 'string' && typeof x.overall_feedback === 'string')
        .slice(0, 20);
      setHistory(cleaned);
    } catch {
      setHistory([]);
    }
  }, [historyKey]);

  const persistHistory = (entry: HistoryEntry) => {
    if (typeof window === 'undefined') return;
    try {
      const next = [entry, ...history].slice(0, 20);
      window.localStorage.setItem(historyKey, JSON.stringify(next));
      setHistory(next);
    } catch {
      // ignore quota/serialization errors
    }
  };

  const stopSpeakingRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    try {
      if (recorder.state !== 'inactive') {
        recorder.stop();
      }
    } catch {
      setRecordingQuestionId(null);
      stopMediaTracks();
      cleanupRecorderState();
    }
  }, [cleanupRecorderState, stopMediaTracks]);

  const startSpeakingRecording = useCallback(
    async (questionId: string) => {
      if (recordingQuestionId || processingQuestionId || isGenerating || isAnalyzing) return;
      if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        setError('Seu navegador não suporta gravação de áudio.');
        return;
      }

      setError(null);

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        mediaStreamRef.current = stream;
        chunksRef.current = [];
        activeSpeakingQuestionRef.current = questionId;

        const preferredTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'];
        const mimeType = preferredTypes.find(
          (type) => typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)
        );
        const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            chunksRef.current.push(event.data);
          }
        };

        recorder.onstop = async () => {
          const targetQuestionId = activeSpeakingQuestionRef.current || questionId;
          const localChunks = [...chunksRef.current];
          setRecordingQuestionId((current) => (current === targetQuestionId ? null : current));

          stopMediaTracks();
          cleanupRecorderState();

          const audioBlob = new Blob(localChunks, { type: recorder.mimeType || 'audio/webm' });
          if (!audioBlob || audioBlob.size < 800) {
            setError('Áudio muito curto ou sem som. Grave novamente.');
            return;
          }

          setProcessingQuestionId(targetQuestionId);
          try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'exam-speaking.webm');
            formData.append('native_language', 'pt-BR');

            const response = await conversationApi.analyzePronunciation(formData);
            const data = response.data as PronunciationApiResponse;

            const transcript = typeof data.transcript === 'string' ? data.transcript.trim() : '';
            const feedback = typeof data.feedback === 'string' ? data.feedback.trim() : '';
            const similarity = typeof data.similarity === 'number' ? data.similarity : null;

            setSpeakingById((prev) => ({
              ...prev,
              [targetQuestionId]: {
                transcript,
                feedback,
                similarity,
              },
            }));

            if (transcript) {
              setAnswersById((prev) => ({
                ...prev,
                [targetQuestionId]: transcript,
              }));
            }
          } catch (e: unknown) {
            setError(getErrorMessage(e, 'Não foi possível analisar o áudio da resposta.'));
          } finally {
            setProcessingQuestionId((current) => (current === targetQuestionId ? null : current));
          }
        };

        recorder.start(250);
        setRecordingQuestionId(questionId);
      } catch {
        setError('Não foi possível acessar o microfone. Verifique a permissão do navegador.');
        setRecordingQuestionId(null);
        stopMediaTracks();
        cleanupRecorderState();
      }
    },
    [cleanupRecorderState, getErrorMessage, isAnalyzing, isGenerating, processingQuestionId, recordingQuestionId, stopMediaTracks]
  );

  const handleGenerate = async () => {
    setError(null);
    setAnalysis(null);
    setIsGenerating(true);
    try {
      const { data } = await examsAiApi.generate({
        exam,
        skill,
        num_questions: numQuestions,
      });

      setInstructions(data.instructions || null);
      setQuestions(Array.isArray(data.questions) ? data.questions : []);
      setAnswersById({});
      setSpeakingById({});
    } catch (e: unknown) {
      setError(getErrorMessage(e, 'Não foi possível gerar o mini-simulado.'));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAnalyze = async () => {
    setError(null);
    setIsAnalyzing(true);
    try {
      const answers = questions.map((q) => {
        const baseAnswer = (answersById[q.id] || '').trim();
        if (!isSpeakingType(q.type)) {
          return { id: q.id, answer: baseAnswer };
        }

        const speaking = speakingById[q.id];
        if (!speaking) {
          return { id: q.id, answer: baseAnswer };
        }

        const enrichments: string[] = [];
        if (speaking.feedback) {
          enrichments.push(`Pronunciation feedback: ${speaking.feedback}`);
        }
        if (speaking.similarity !== null) {
          enrichments.push(`Similarity score: ${speaking.similarity}%`);
        }

        return {
          id: q.id,
          answer: [baseAnswer, ...enrichments].filter(Boolean).join('\n\n'),
        };
      });

      const { data } = await examsAiApi.analyze({
        exam,
        skill,
        questions,
        answers,
      });
      setAnalysis(data);

      persistHistory({
        at: new Date().toISOString(),
        exam,
        skill,
        estimated_score: data.estimated_score ?? null,
        overall_feedback: data.overall_feedback,
        strengths: data.strengths,
        weaknesses: data.weaknesses,
        study_plan: data.study_plan,
        motivation: data.motivation ?? null,
      });
    } catch (e: unknown) {
      setError(getErrorMessage(e, 'Não foi possível analisar suas respostas.'));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleClear = () => {
    if (recordingQuestionId) {
      stopSpeakingRecording();
    }
    setQuestions([]);
    setAnswersById({});
    setSpeakingById({});
    setAnalysis(null);
    setInstructions(null);
    setError(null);
  };

  return (
    <section id="coach-ia" className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
      <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Coach IA (mini-simulado)</h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Gere um mini-simulado e receba feedback prático + plano de estudo.
      </p>

      <div className="mb-4 rounded-lg border border-blue-200 dark:border-blue-900/50 bg-blue-50 dark:bg-blue-900/20 px-3 py-2 text-xs text-blue-700 dark:text-blue-200">
        Questões do tipo <span className="font-semibold">speaking</span> já aceitam resposta por voz, com transcrição e
        feedback de pronúncia.
      </div>

      <div className="grid md:grid-cols-3 gap-3 mb-4">
        <div>
          <label htmlFor="exam-skill" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            Habilidade
          </label>
          <select
            id="exam-skill"
            value={skill}
            onChange={(e) => setSkill(e.target.value)}
            className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
            <option value="mixed">Misto</option>
            <option value="reading">Reading</option>
            <option value="listening">Listening</option>
            <option value="writing">Writing</option>
            <option value="speaking">Speaking</option>
            <option value="vocab">Vocabulary</option>
            <option value="grammar">Grammar</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="exam-num-questions"
            className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
          >
            Nº de questões
          </label>
          <select
            id="exam-num-questions"
            value={numQuestions}
            onChange={(e) => setNumQuestions(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
            {[3, 5, 7, 10, 12].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !!recordingQuestionId || !!processingQuestionId}
            className="w-full rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white px-4 py-2 text-sm font-semibold transition"
          >
            {isGenerating ? 'Gerando…' : 'Gerar mini-simulado'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 px-3 py-2 text-sm text-red-700 dark:text-red-300">
          {error}
        </div>
      )}

      {instructions && (
        <div className="mb-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/40 px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="font-semibold text-xs text-gray-600 dark:text-gray-400 mb-1">Instruções</div>
          <div>{instructions}</div>
        </div>
      )}

      {questions.length > 0 && (
        <div className="space-y-4">
          {questions.map((q, idx) => {
            const isSpeakingQuestion = isSpeakingType(q.type);
            const speakingResult = speakingById[q.id];
            const isRecordingThis = recordingQuestionId === q.id;
            const isProcessingThis = processingQuestionId === q.id;
            const isBusyWithAnotherQuestion =
              (!!recordingQuestionId && !isRecordingThis) || (!!processingQuestionId && !isProcessingThis);

            return (
              <div key={q.id} className="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="text-sm font-semibold text-gray-900 dark:text-white">Questão {idx + 1}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">{q.type}</div>
                </div>

                <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap mb-3">{q.prompt}</div>

                {q.type === 'multiple_choice' && Array.isArray(q.options) && q.options.length > 0 ? (
                  <div className="space-y-2">
                    {q.options.map((opt, i) => {
                      const value = String.fromCharCode(65 + i);
                      const checked = (answersById[q.id] || '') === value;
                      return (
                        <label
                          key={value}
                          className="flex items-start gap-2 rounded-md px-2 py-1 hover:bg-gray-50 dark:hover:bg-gray-900/40 cursor-pointer"
                        >
                          <input
                            type="radio"
                            name={q.id}
                            checked={checked}
                            onChange={() =>
                              setAnswersById((prev) => ({
                                ...prev,
                                [q.id]: value,
                              }))
                            }
                          />
                          <div className="text-sm text-gray-700 dark:text-gray-300">
                            <span className="font-semibold mr-2">{value}.</span>
                            {opt}
                          </div>
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  <>
                    <textarea
                      value={answersById[q.id] || ''}
                      onChange={(e) => setAnswersById((prev) => ({ ...prev, [q.id]: e.target.value }))}
                      rows={q.type === 'essay' ? 6 : 4}
                      placeholder={
                        isSpeakingQuestion
                          ? 'Grave sua resposta abaixo ou digite manualmente...'
                          : 'Digite sua resposta aqui…'
                      }
                      className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white"
                    />

                    {isSpeakingQuestion && (
                      <div className="mt-3 rounded-lg border border-blue-200 dark:border-blue-900/40 bg-blue-50 dark:bg-blue-900/20 p-3">
                        <div className="flex flex-wrap items-center gap-2">
                          {isRecordingThis ? (
                            <button
                              onClick={stopSpeakingRecording}
                              className="rounded-lg bg-red-600 hover:bg-red-700 text-white px-3 py-2 text-xs font-semibold transition"
                            >
                              Parar gravação
                            </button>
                          ) : (
                            <button
                              onClick={() => void startSpeakingRecording(q.id)}
                              disabled={isBusyWithAnotherQuestion || isGenerating || isAnalyzing}
                              className="rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-3 py-2 text-xs font-semibold transition"
                            >
                              Gravar resposta por voz
                            </button>
                          )}

                          {isRecordingThis && (
                            <span className="inline-flex items-center gap-2 text-xs text-red-700 dark:text-red-300 font-semibold">
                              <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
                              Gravando...
                            </span>
                          )}

                          {isProcessingThis && (
                            <span className="inline-flex items-center gap-2 text-xs text-blue-700 dark:text-blue-300 font-semibold">
                              <span className="w-3 h-3 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
                              Processando áudio...
                            </span>
                          )}
                        </div>

                        {speakingResult && (
                          <div className="mt-3 space-y-2">
                            <div>
                              <div className="text-[11px] font-semibold text-blue-900 dark:text-blue-100 mb-1">
                                Transcrição
                              </div>
                              <div className="text-xs text-blue-900 dark:text-blue-100 whitespace-pre-wrap">
                                {speakingResult.transcript || 'Sem transcrição.'}
                              </div>
                            </div>

                            {speakingResult.similarity !== null && (
                              <div className="text-xs text-blue-900 dark:text-blue-100">
                                Similaridade: <span className="font-semibold">{speakingResult.similarity}%</span>
                              </div>
                            )}

                            {speakingResult.feedback && (
                              <div>
                                <div className="text-[11px] font-semibold text-blue-900 dark:text-blue-100 mb-1">
                                  Feedback de pronúncia
                                </div>
                                <div className="text-xs text-blue-900 dark:text-blue-100 whitespace-pre-wrap">
                                  {speakingResult.feedback}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}

          <div className="flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={!canAnalyze || isAnalyzing || !!recordingQuestionId || !!processingQuestionId}
              className="rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 disabled:opacity-60 px-4 py-2 text-sm font-semibold transition"
            >
              {isAnalyzing ? 'Analisando…' : 'Analisar respostas'}
            </button>

            <button
              onClick={handleClear}
              disabled={!!recordingQuestionId || !!processingQuestionId}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-2 text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900/40 disabled:opacity-60 transition"
            >
              Limpar
            </button>
          </div>
        </div>
      )}

      {analysis && (
        <div className="mt-6 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-start justify-between gap-4 mb-3">
            <div>
              <div className="text-sm font-bold text-gray-900 dark:text-white">Feedback do Coach</div>
              {analysis.estimated_score ? (
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  Score estimado: {analysis.estimated_score}
                </div>
              ) : null}
            </div>
          </div>

          <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap mb-4">
            {analysis.overall_feedback}
          </div>

          {(analysis.strengths?.length || 0) > 0 && (
            <div className="mb-4">
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">Pontos fortes</div>
              <ul className="text-sm text-gray-700 dark:text-gray-300 list-disc pl-5 space-y-1">
                {analysis.strengths!.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {(analysis.weaknesses?.length || 0) > 0 && (
            <div className="mb-4">
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">Onde melhorar</div>
              <ul className="text-sm text-gray-700 dark:text-gray-300 list-disc pl-5 space-y-1">
                {analysis.weaknesses!.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {(analysis.study_plan?.length || 0) > 0 && (
            <div className="mb-4">
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">
                Plano de estudo (próximos passos)
              </div>
              <ul className="text-sm text-gray-700 dark:text-gray-300 list-disc pl-5 space-y-1">
                {analysis.study_plan!.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}

          {analysis.motivation && (
            <div className="rounded-lg bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
              {analysis.motivation}
            </div>
          )}

          {(analysis.per_question?.length || 0) > 0 && (
            <div className="mt-4">
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2">Por questão</div>
              <div className="space-y-3">
                {analysis.per_question!.map((pq) => (
                  <div key={pq.id} className="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{pq.id}</div>
                    <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{pq.feedback}</div>
                    {pq.improved_answer ? (
                      <div className="mt-2 text-sm text-gray-700 dark:text-gray-300">
                        <div className="text-xs font-bold text-gray-600 dark:text-gray-400">Resposta sugerida</div>
                        <div className="whitespace-pre-wrap">{pq.improved_answer}</div>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div className="mt-6 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div>
              <div className="text-sm font-bold text-gray-900 dark:text-white">Histórico (local)</div>
              <div className="text-xs text-gray-600 dark:text-gray-400">Salvo apenas neste navegador (por habilidade).</div>
            </div>
            <button
              onClick={() => {
                if (typeof window !== 'undefined') {
                  try {
                    window.localStorage.removeItem(historyKey);
                  } catch {
                    // ignore
                  }
                }
                setHistory([]);
              }}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-2 text-xs font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900/40 transition"
            >
              Limpar histórico
            </button>
          </div>

          <div className="space-y-2">
            {history.slice(0, 5).map((h) => {
              const dateLabel = (() => {
                try {
                  return new Date(h.at).toLocaleString();
                } catch {
                  return h.at;
                }
              })();

              return (
                <div
                  key={h.at}
                  className="flex items-start justify-between gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3"
                >
                  <div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{dateLabel}</div>
                    <div className="text-sm text-gray-900 dark:text-white">
                      {h.estimated_score ? (
                        <span className="font-semibold">Score: {h.estimated_score}</span>
                      ) : (
                        <span className="font-semibold">Análise salva</span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setAnalysis({
                        estimated_score: h.estimated_score ?? null,
                        overall_feedback: h.overall_feedback,
                        strengths: h.strengths,
                        weaknesses: h.weaknesses,
                        study_plan: h.study_plan,
                        motivation: h.motivation ?? null,
                      });
                    }}
                    className="rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 px-3 py-2 text-xs font-semibold transition"
                  >
                    Reabrir
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
