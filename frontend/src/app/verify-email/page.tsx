'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { authApi } from '@/lib/api';
import toast from 'react-hot-toast';

type VerificationStatus = 'loading' | 'success' | 'error';

export default function VerifyEmailPage() {
  const searchParams = useSearchParams();
  const token = useMemo(() => searchParams.get('token') || '', [searchParams]);
  const [status, setStatus] = useState<VerificationStatus>('loading');
  const [message, setMessage] = useState('Validando seu e-mail...');

  useEffect(() => {
    const run = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Link de confirmacao invalido.');
        return;
      }

      try {
        const response = await authApi.verifyEmail(token);
        const detail = response.data?.message || 'Email confirmado com sucesso.';
        setStatus('success');
        setMessage(detail);
        toast.success('Email confirmado!');
      } catch (error: unknown) {
        const err = error as { response?: { data?: { detail?: string } } };
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Nao foi possivel confirmar seu e-mail.');
      }
    };

    void run();
  }, [token]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Confirmacao de e-mail</h1>
        <p
          className={`mb-6 ${
            status === 'error' ? 'text-red-600' : status === 'success' ? 'text-green-700' : 'text-gray-600'
          }`}
        >
          {message}
        </p>

        {status === 'loading' && (
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-primary-600 border-b-transparent" />
        )}

        {status !== 'loading' && (
          <Link
            href="/login"
            className="inline-flex items-center justify-center rounded-lg bg-primary-600 px-5 py-3 text-white font-semibold hover:bg-primary-700 transition"
          >
            Ir para login
          </Link>
        )}
      </div>
    </div>
  );
}
