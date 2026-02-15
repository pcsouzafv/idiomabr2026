'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import ThemeToggle from '@/components/ThemeToggle';
import { PIX_BENEFICIARY, PIX_CITY, PIX_PAYLOAD } from '@/lib/donation';
import {
  ArrowRight,
  BookOpen,
  Brain,
  Gamepad2,
  GraduationCap,
  MessageCircle,
  Sparkles,
  Target,
  Trophy,
  Zap,
} from 'lucide-react';
import toast from 'react-hot-toast';

const PLATFORM_STATS = [
  { value: '10.000+', label: 'palavras disponíveis' },
  { value: '2.500+', label: 'frases para praticar' },
  { value: '5-10 min', label: 'de estudo por dia' },
];

export default function Home() {
  const { user, isLoading, fetchUser } = useAuthStore();
  const [copyingPix, setCopyingPix] = useState(false);
  const router = useRouter();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/dashboard');
    }
  }, [user, isLoading, router]);

  const copyPixCode = async () => {
    try {
      setCopyingPix(true);
      await navigator.clipboard.writeText(PIX_PAYLOAD);
      toast.success('Código PIX copiado');
    } catch {
      toast.error('Não foi possível copiar o código PIX');
    } finally {
      setCopyingPix(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 transition-colors">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_10%_20%,_#dbeafe_0%,_#eef2ff_35%,_#f8fafc_100%)] dark:bg-[radial-gradient(circle_at_10%_15%,_#1e293b_0%,_#0f172a_45%,_#020617_100%)] transition-colors">
      <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-cyan-300/30 blur-3xl dark:bg-cyan-500/20" />
      <div className="pointer-events-none absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-indigo-400/30 blur-3xl dark:bg-indigo-500/20" />

      <div className="relative container mx-auto px-4 py-8 md:py-12">
        <nav className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="inline-flex items-center">
            <div className="relative h-16 w-56 overflow-hidden rounded-2xl border border-white/80 bg-white shadow-md dark:border-slate-700 dark:bg-slate-900">
              <Image
                src="/brand/idiomasbr-logo.png"
                alt="IdiomasBR - Conectando Culturas"
                fill
                priority
                className="object-cover object-center"
                sizes="224px"
              />
            </div>
          </Link>

          <div className="flex items-center gap-3 self-end sm:self-auto">
            <ThemeToggle />
            <Link
              href="/login"
              className="px-5 py-2.5 rounded-xl text-primary-700 dark:text-primary-300 font-semibold hover:bg-white/70 dark:hover:bg-slate-800 transition"
            >
              Entrar
            </Link>
            <Link
              href="/register"
              className="px-5 py-2.5 rounded-xl bg-primary-600 text-white font-semibold hover:bg-primary-700 transition"
            >
              Criar Conta
            </Link>
          </div>
        </nav>

        <section className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div className="animate-slide-up">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary-200 bg-white/85 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-primary-700 dark:border-primary-500/30 dark:bg-slate-900/80 dark:text-primary-300">
              <Sparkles className="h-4 w-4" />
              Plataforma Brasileira de Inglês com IA
            </p>
            <h1 className="text-4xl md:text-6xl font-black tracking-tight text-slate-900 dark:text-white leading-tight">
              Prática inteligente para você falar inglês com confiança
            </h1>
            <p className="mt-5 max-w-2xl text-lg md:text-xl text-slate-600 dark:text-slate-300 leading-relaxed">
              Estude com trilhas modernas de vocabulário, frases, conversação com IA, jogos e simulados.
              Hoje o IdiomasBR já oferece mais de <span className="font-bold text-slate-900 dark:text-slate-100">10.000 palavras</span>{' '}
              e mais de <span className="font-bold text-slate-900 dark:text-slate-100">2.500 frases</span>.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link
                href="/register"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-7 py-4 text-base font-bold text-white hover:bg-slate-800 dark:bg-primary-600 dark:hover:bg-primary-700 transition"
              >
                Começar Agora
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-xl border border-slate-300 dark:border-slate-700 bg-white/80 dark:bg-slate-900 px-7 py-4 text-base font-semibold text-slate-800 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 transition"
              >
                Já tenho conta
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200/70 dark:border-slate-700 bg-white/85 dark:bg-slate-900/80 backdrop-blur p-6 md:p-7 shadow-xl animate-slide-up">
            <h2 className="text-sm uppercase tracking-wide font-bold text-slate-500 dark:text-slate-400 mb-5">
              Recursos em destaque
            </h2>
            <div className="grid gap-3">
              <div className="rounded-2xl border border-blue-200 dark:border-blue-900/40 bg-blue-50/80 dark:bg-blue-950/30 p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                    <BookOpen className="h-5 w-5 text-blue-600 dark:text-blue-300" />
                  </div>
                  <div>
                    <p className="font-bold text-slate-900 dark:text-slate-100">Vocabulário e flashcards</p>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Estudo diário com revisão inteligente.</p>
                  </div>
                </div>
              </div>
              <div className="rounded-2xl border border-cyan-200 dark:border-cyan-900/40 bg-cyan-50/80 dark:bg-cyan-950/30 p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-cyan-100 dark:bg-cyan-900/40 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-cyan-600 dark:text-cyan-300" />
                  </div>
                  <div>
                    <p className="font-bold text-slate-900 dark:text-slate-100">Frases com IA</p>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Análise, contexto e pronúncia guiada.</p>
                  </div>
                </div>
              </div>
              <div className="rounded-2xl border border-violet-200 dark:border-violet-900/40 bg-violet-50/80 dark:bg-violet-950/30 p-4">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-xl bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center">
                    <MessageCircle className="h-5 w-5 text-violet-600 dark:text-violet-300" />
                  </div>
                  <div>
                    <p className="font-bold text-slate-900 dark:text-slate-100">Conversação por voz</p>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Pratique speaking em cenários reais.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-14 grid gap-4 sm:grid-cols-3">
          {PLATFORM_STATS.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/85 dark:bg-slate-900/80 p-5 text-center shadow-sm"
            >
              <div className="text-3xl font-black text-primary-600 dark:text-primary-300">{item.value}</div>
              <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{item.label}</div>
            </div>
          ))}
        </section>

        <section className="mt-14 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/85 dark:bg-slate-900/80 p-5 shadow-sm">
            <Zap className="h-6 w-6 text-primary-600 dark:text-primary-300 mb-3" />
            <h3 className="font-bold text-slate-900 dark:text-slate-100">Repetição espaçada</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Sistema prioriza o que você precisa revisar para aprender com consistência.</p>
          </article>
          <article className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/85 dark:bg-slate-900/80 p-5 shadow-sm">
            <Target className="h-6 w-6 text-emerald-600 dark:text-emerald-300 mb-3" />
            <h3 className="font-bold text-slate-900 dark:text-slate-100">Desafios diários</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Metas e missões para manter ritmo de estudo e evolução semanal.</p>
          </article>
          <article className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/85 dark:bg-slate-900/80 p-5 shadow-sm">
            <Gamepad2 className="h-6 w-6 text-amber-600 dark:text-amber-300 mb-3" />
            <h3 className="font-bold text-slate-900 dark:text-slate-100">Jogos educativos</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Quiz, ditado, forca e mais para treinar ouvindo, lendo e escrevendo.</p>
          </article>
          <article className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-white/85 dark:bg-slate-900/80 p-5 shadow-sm">
            <GraduationCap className="h-6 w-6 text-rose-600 dark:text-rose-300 mb-3" />
            <h3 className="font-bold text-slate-900 dark:text-slate-100">Preparação para exames</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Trilhas de IELTS, TOEFL, TOEIC e Cambridge com acompanhamento por IA.</p>
          </article>
        </section>

        <section className="mt-14 rounded-3xl border border-emerald-200 dark:border-emerald-900/40 bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50 dark:from-emerald-950/20 dark:via-teal-950/20 dark:to-cyan-950/20 p-6 md:p-8 shadow-lg">
          <div className="grid gap-6 lg:grid-cols-[1fr_220px] lg:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300 mb-2">Apoio ao projeto</p>
              <h3 className="text-2xl md:text-3xl font-black text-slate-900 dark:text-slate-100 mb-3">
                Apoie o IdiomasBR no Apoia.se
              </h3>
              <p className="text-slate-700 dark:text-slate-300 max-w-2xl">
                Estamos organizando a página oficial de apoio para sustentar infraestrutura, IA e expansão de conteúdos.
                O espaço do QR code já está pronto e será ativado assim que você enviar.
              </p>
              <p className="mt-3 text-sm text-slate-700 dark:text-slate-300">
                Favorecido: <span className="font-semibold">{PIX_BENEFICIARY}</span> ({PIX_CITY})
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-300 dark:border-emerald-700 bg-white/90 dark:bg-slate-900 p-4 text-center">
              <div className="mx-auto relative h-44 w-44 rounded-xl overflow-hidden border border-emerald-200 dark:border-emerald-800 bg-white">
                <Image
                  src="/donations/pix-rickpcsouza.png"
                  alt="QR Code PIX para apoiar o projeto"
                  fill
                  className="object-contain"
                  sizes="176px"
                />
              </div>
              <button
                type="button"
                onClick={() => void copyPixCode()}
                disabled={copyingPix}
                className="mt-3 w-full rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60 transition"
              >
                {copyingPix ? 'Copiando...' : 'Copiar código PIX'}
              </button>
              <p className="mt-2 text-[11px] leading-snug text-emerald-800 dark:text-emerald-200 break-all">
                {PIX_PAYLOAD}
              </p>
            </div>
          </div>
        </section>
      </div>

      <footer className="mt-14 border-t border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/70 backdrop-blur">
        <div className="container mx-auto px-4 py-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-primary-700 dark:text-primary-300" />
            </div>
            <div>
              <p className="font-bold text-slate-900 dark:text-slate-100">IdiomasBR</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">Conectando culturas com tecnologia e educação.</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
            <Trophy className="h-4 w-4" />
            <span>Mais de 10.000 palavras e 2.500 frases para você praticar.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
