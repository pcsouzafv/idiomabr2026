'use client';

import { useEffect, useMemo, useState } from 'react';
import { examsAiApi } from '@/lib/api';

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

export default function ExamAiCoach({ exam }: { exam: string }) {
  const [skill, setSkill] = useState('mixed');
  const [numQuestions, setNumQuestions] = useState(5);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [instructions, setInstructions] = useState<string | null>(null);
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [answersById, setAnswersById] = useState<Record<string, string>>({});
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const canAnalyze = useMemo(() => {
    if (!questions.length) return false;
    // allow analysis even if some answers blank, but require at least one answer
    return Object.values(answersById).some((v) => (v || '').trim().length > 0);
  }, [questions.length, answersById]);

  const getErrorMessage = (e: unknown, fallback: string) => {
    if (typeof e === 'object' && e !== null) {
      const maybeResponse = (e as { response?: { data?: { detail?: unknown } } }).response;
      const detail = maybeResponse?.data?.detail;
      if (typeof detail === 'string' && detail.trim()) return detail;
    }
    return fallback;
  };

  const historyKey = useMemo(() => `exam_ai_history:${exam}:${skill}`, [exam, skill]);

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
      const answers = questions.map((q) => ({ id: q.id, answer: answersById[q.id] || '' }));
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

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
      <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Coach IA (mini-simulado)</h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Gere um mini-simulado e receba feedback prático + plano de estudo.
      </p>

      <div className="grid md:grid-cols-3 gap-3 mb-4">
        <div>
          <label htmlFor="exam-skill" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Habilidade</label>
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
          <label htmlFor="exam-num-questions" className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Nº de questões</label>
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
            disabled={isGenerating}
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
          {questions.map((q, idx) => (
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
                <textarea
                  value={answersById[q.id] || ''}
                  onChange={(e) => setAnswersById((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  rows={q.type === 'essay' ? 6 : 3}
                  placeholder="Digite sua resposta aqui…"
                  className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white"
                />
              )}
            </div>
          ))}

          <div className="flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={!canAnalyze || isAnalyzing}
              className="rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:opacity-90 disabled:opacity-60 px-4 py-2 text-sm font-semibold transition"
            >
              {isAnalyzing ? 'Analisando…' : 'Analisar respostas'}
            </button>

            <button
              onClick={() => {
                setQuestions([]);
                setAnswersById({});
                setAnalysis(null);
                setInstructions(null);
                setError(null);
              }}
              className="rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-2 text-sm font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900/40 transition"
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
                <div className="text-xs text-gray-600 dark:text-gray-400">Score estimado: {analysis.estimated_score}</div>
              ) : null}
            </div>
          </div>

          <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap mb-4">{analysis.overall_feedback}</div>

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
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">Plano de estudo (próximos passos)</div>
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
                <div key={h.at} className="flex items-start justify-between gap-3 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
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
