'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Circle, Target, TrendingUp, Flame } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { EXAM_TRACKS, type ExamId } from '../_data/tracks';

type CheckMap = Record<string, boolean>;

const clamp = (value: number) => Math.max(0, Math.min(100, value));

function getWeekStartKey(date = new Date()): string {
  const current = new Date(date);
  const day = (current.getDay() + 6) % 7; // monday=0
  current.setDate(current.getDate() - day);
  current.setHours(0, 0, 0, 0);
  return current.toISOString().slice(0, 10);
}

export default function ExamGuidedTrack({ exam }: { exam: ExamId }) {
  const track = EXAM_TRACKS[exam];
  const { stats, fetchStats } = useAuthStore();
  const [checked, setChecked] = useState<CheckMap>({});

  useEffect(() => {
    if (!stats) {
      fetchStats();
    }
  }, [fetchStats, stats]);

  const weekKey = useMemo(() => getWeekStartKey(), []);
  const storageKey = useMemo(() => `exam_track:${exam}:${weekKey}`, [exam, weekKey]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) {
        setChecked({});
        return;
      }
      const parsed = JSON.parse(raw) as unknown;
      if (!parsed || typeof parsed !== 'object') {
        setChecked({});
        return;
      }
      setChecked(parsed as CheckMap);
    } catch {
      setChecked({});
    }
  }, [storageKey]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(checked));
    } catch {
      // ignore storage errors
    }
  }, [checked, storageKey]);

  const wordsProgress = clamp(
    ((stats?.total_words_learned ?? 0) / track.targets.wordsLearned) * 100
  );
  const streakProgress = clamp(
    ((stats?.current_streak ?? 0) / track.targets.streakDays) * 100
  );
  const dailyProgress = clamp(stats?.daily_goal_progress ?? 0);

  const readinessScore = Math.round(
    wordsProgress * 0.45 + streakProgress * 0.25 + dailyProgress * 0.3
  );

  const weakestPillar = useMemo(() => {
    const candidates = [
      { key: 'vocabulary', value: wordsProgress, label: 'vocabulário-base' },
      { key: 'consistency', value: streakProgress, label: 'consistência diária' },
      { key: 'daily-goal', value: dailyProgress, label: 'meta de estudo' },
    ];
    return candidates.sort((a, b) => a.value - b.value)[0];
  }, [dailyProgress, streakProgress, wordsProgress]);

  const completedCount = track.weeklySteps.filter((step) => checked[step.id]).length;
  const completionProgress = clamp((completedCount / track.weeklySteps.length) * 100);

  const toggleStep = (stepId: string) => {
    setChecked((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  };

  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm transition-colors">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">Trilha Guiada da Semana</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{track.goal}</p>
          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">Escala de referência: {track.scoreHint}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 dark:text-gray-500">Etapas concluídas</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {completedCount}/{track.weeklySteps.length}
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-3 mb-5">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-3">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 mb-1">
            <Target className="w-4 h-4" />
            Prontidão estimada
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{readinessScore}%</div>
        </div>

        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-3">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 mb-1">
            <TrendingUp className="w-4 h-4" />
            Vocabulário para prova
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{Math.round(wordsProgress)}%</div>
        </div>

        <div className="rounded-xl border border-gray-200 dark:border-gray-700 p-3">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 mb-1">
            <Flame className="w-4 h-4" />
            Consistência
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{Math.round(streakProgress)}%</div>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-300 mb-1">
          <span>Progresso da trilha</span>
          <span>{Math.round(completionProgress)}%</span>
        </div>
        <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-cyan-500 transition-all duration-300"
            style={{ width: `${completionProgress}%` }}
          />
        </div>
      </div>

      <div className="mb-4 rounded-lg border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-sm text-amber-800 dark:text-amber-200">
        Foco recomendado desta semana: reforçar <span className="font-semibold">{weakestPillar.label}</span>.
      </div>

      <div className="space-y-3">
        {track.weeklySteps.map((step, index) => {
          const done = !!checked[step.id];
          const isAnchor = step.href.startsWith('#');

          return (
            <div
              key={step.id}
              className={`rounded-xl border p-4 transition-colors ${
                done
                  ? 'border-emerald-300 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-900/20'
                  : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/20'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Etapa {index + 1}</div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{step.title}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{step.description}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    Ritmo: {step.cadence} • {step.minutes} min
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {isAnchor ? (
                    <a
                      href={step.href}
                      className="rounded-lg bg-primary-600 hover:bg-primary-700 text-white px-3 py-2 text-xs font-semibold transition"
                    >
                      Abrir
                    </a>
                  ) : (
                    <Link
                      href={step.href}
                      className="rounded-lg bg-primary-600 hover:bg-primary-700 text-white px-3 py-2 text-xs font-semibold transition"
                    >
                      Praticar
                    </Link>
                  )}

                  <button
                    onClick={() => toggleStep(step.id)}
                    className={`inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold border transition ${
                      done
                        ? 'border-emerald-300 dark:border-emerald-800 bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-200'
                        : 'border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    {done ? <CheckCircle2 className="w-4 h-4" /> : <Circle className="w-4 h-4" />}
                    {done ? 'Concluída' : 'Marcar'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

