'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/lib/api';
import ThemeToggle from '@/components/ThemeToggle';
import { PIX_BENEFICIARY, PIX_CITY, PIX_PAYLOAD } from '@/lib/donation';
import {
  ArrowRight,
  BookOpenCheck,
  Eye,
  EyeOff,
  Lock,
  Mail,
  MessageSquareText,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pendingVerificationEmail, setPendingVerificationEmail] = useState('');
  const searchParams = useSearchParams();
  const [isResendingVerification, setIsResendingVerification] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [copyingPix, setCopyingPix] = useState(false);

  const { login } = useAuthStore();
  const router = useRouter();

  const verificationSentEmail = useMemo(() => {
    if (searchParams.get('verification') !== 'sent') return '';
    return (searchParams.get('email') || '').trim().toLowerCase();
  }, [searchParams]);

  useEffect(() => {
    if (!verificationSentEmail) return;
    setPendingVerificationEmail(verificationSentEmail);
    setEmail(verificationSentEmail);
  }, [verificationSentEmail]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      setPendingVerificationEmail('');
      toast.success('Login realizado com sucesso!');
      router.push('/dashboard');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      const detail = err.response?.data?.detail || 'Erro ao fazer login';
      toast.error(detail);

      if (detail.includes('Email nao verificado')) {
        setPendingVerificationEmail(email.trim());
      } else {
        setPendingVerificationEmail('');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendVerification = async (emailOverride?: string) => {
    const targetEmail = (emailOverride || pendingVerificationEmail).trim();
    if (!targetEmail) return;
    setIsResendingVerification(true);
    try {
      await authApi.resendVerification({ email: targetEmail });
      toast.success('Se o email estiver pendente, reenviamos um novo link.');
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast.error(err.response?.data?.detail || 'Erro ao reenviar confirmação');
    } finally {
      setIsResendingVerification(false);
    }
  };

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

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_15%_10%,_#dbeafe_0%,_#eef2ff_40%,_#f8fafc_100%)] dark:bg-[radial-gradient(circle_at_15%_10%,_#1e293b_0%,_#0f172a_45%,_#020617_100%)] transition-colors">
      <div className="pointer-events-none absolute -top-20 -left-20 h-64 w-64 rounded-full bg-sky-300/30 blur-3xl dark:bg-sky-500/20" />
      <div className="pointer-events-none absolute -bottom-28 -right-20 h-72 w-72 rounded-full bg-indigo-400/30 blur-3xl dark:bg-indigo-500/20" />

      <main className="relative container mx-auto px-4 py-8 md:py-12">
        <header className="mb-8 flex items-center justify-between">
          <Link href="/" className="inline-flex items-center">
            <div className="relative h-14 w-52 overflow-hidden rounded-2xl border border-white/80 bg-white shadow-md dark:border-slate-700 dark:bg-slate-900">
              <Image
                src="/brand/idiomasbr-logo.png"
                alt="IdiomasBR - Conectando Culturas"
                fill
                priority
                className="object-cover object-center"
                sizes="208px"
              />
            </div>
          </Link>
          <ThemeToggle />
        </header>

        <section className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
          <aside className="hidden lg:flex flex-col justify-between rounded-3xl border border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 backdrop-blur p-8 shadow-xl">
            <div>
              <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary-200 dark:border-primary-500/30 bg-primary-50 dark:bg-primary-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary-700 dark:text-primary-300">
                <Sparkles className="h-3.5 w-3.5" />
                Plataforma com IA
              </p>
              <h1 className="text-4xl font-black leading-tight text-slate-900 dark:text-slate-100">
                Continue sua evolução no inglês
              </h1>
              <p className="mt-4 text-slate-600 dark:text-slate-300 leading-relaxed">
                Retome seus estudos com trilhas de vocabulário, frases com IA,
                conversação por voz e simulados.
              </p>
            </div>

            <div className="space-y-3">
              <div className="rounded-2xl border border-sky-200 dark:border-sky-900/40 bg-sky-50/80 dark:bg-sky-950/30 p-4">
                <div className="flex items-center gap-3">
                  <BookOpenCheck className="h-5 w-5 text-sky-600 dark:text-sky-300" />
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    Mais de 10.000 palavras disponíveis
                  </p>
                </div>
              </div>
              <div className="rounded-2xl border border-violet-200 dark:border-violet-900/40 bg-violet-50/80 dark:bg-violet-950/30 p-4">
                <div className="flex items-center gap-3">
                  <MessageSquareText className="h-5 w-5 text-violet-600 dark:text-violet-300" />
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    Mais de 2.500 frases para prática real
                  </p>
                </div>
              </div>
            </div>
          </aside>

          <div className="rounded-3xl border border-slate-200 dark:border-slate-700 bg-white/90 dark:bg-slate-900/85 backdrop-blur p-6 sm:p-8 shadow-xl">
            <h2 className="text-3xl font-black text-slate-900 dark:text-slate-100">
              Entrar
            </h2>
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              Acesse sua conta para continuar estudando.
            </p>

            {verificationSentEmail && (
              <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                <p className="text-sm text-emerald-900">
                  Enviamos um e-mail de confirmação para <span className="font-semibold">{verificationSentEmail}</span>.
                  Verifique sua caixa de entrada e spam e clique no link para liberar o acesso.
                </p>
                <button
                  type="button"
                  onClick={() => void handleResendVerification(verificationSentEmail)}
                  disabled={isResendingVerification}
                  className="mt-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
                >
                  {isResendingVerification ? 'Reenviando...' : 'Reenviar e-mail de confirmação'}
                </button>
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-7 space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Email
                </label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 pl-10 pr-4 py-3 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
                    placeholder="seu@email.com"
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Senha
                </label>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 pl-10 pr-12 py-3 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
                    placeholder="••••••••"
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition"
                    aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
                <div className="mt-2 text-right">
                  <Link href="/forgot-password" className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                    Esqueci minha senha
                  </Link>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full rounded-xl bg-primary-600 py-3.5 text-white font-bold hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                {isLoading ? (
                  <span className="inline-flex items-center justify-center gap-2">
                    <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-b-transparent" />
                    Entrando...
                  </span>
                ) : (
                  <span className="inline-flex items-center justify-center gap-2">
                    Entrar
                    <ArrowRight className="h-4 w-4" />
                  </span>
                )}
              </button>
            </form>

            {pendingVerificationEmail && (
              <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3">
                <p className="text-sm text-amber-900">
                  Seu e-mail ainda não foi confirmado.
                </p>
                <button
                  type="button"
                  onClick={() => void handleResendVerification()}
                  disabled={isResendingVerification}
                  className="mt-2 rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-60"
                >
                  {isResendingVerification ? 'Reenviando...' : 'Reenviar e-mail de confirmação'}
                </button>
              </div>
            )}

            <div className="mt-6 rounded-xl border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/80 dark:bg-emerald-950/20 p-3">
              <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">
                Apoie o projeto via PIX
              </p>
              <p className="mt-1 text-xs text-emerald-800 dark:text-emerald-300">
                Favorecido: {PIX_BENEFICIARY} ({PIX_CITY})
              </p>
              <div className="mt-3 flex items-center gap-3">
                <div className="relative h-20 w-20 shrink-0 rounded-lg overflow-hidden border border-emerald-300 dark:border-emerald-800 bg-white">
                  <Image
                    src="/donations/pix-rickpcsouza.png"
                    alt="QR Code PIX para apoiar o projeto"
                    fill
                    className="object-contain"
                    sizes="80px"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => void copyPixCode()}
                  disabled={copyingPix}
                  className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-60 transition"
                >
                  {copyingPix ? 'Copiando...' : 'Copiar código PIX'}
                </button>
              </div>
            </div>

            <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-300">
              Não tem uma conta?{' '}
              <Link href="/register" className="font-semibold text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                Criar conta
              </Link>
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
