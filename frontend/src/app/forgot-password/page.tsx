'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Mail, BookOpen } from 'lucide-react';
import toast from 'react-hot-toast';
import { authApi } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resetUrl, setResetUrl] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setResetUrl(null);

    try {
      const response = await authApi.forgotPassword({ email });
      const message = response.data?.message || 'Se o email estiver cadastrado, enviaremos um link.';
      toast.success(message);
      if (response.data?.reset_url) {
        setResetUrl(response.data.reset_url);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast.error(err.response?.data?.detail || 'Erro ao solicitar recuperacao de senha');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Link href="/" className="flex items-center justify-center gap-2 mb-8">
          <BookOpen className="h-10 w-10 text-primary-600" />
          <span className="text-3xl font-bold text-gray-900">IdiomasBR</span>
        </Link>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-2xl font-bold text-gray-900 text-center mb-2">
            Recuperar senha
          </h1>
          <p className="text-gray-600 text-center mb-8">
            Informe seu email para receber o link de redefinicao
          </p>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
                  placeholder="seu@email.com"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-primary-600 text-white rounded-lg font-semibold hover:bg-primary-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Enviando...' : 'Enviar link'}
            </button>
          </form>

          {resetUrl && (
            <div className="mt-6 text-sm text-gray-700 bg-gray-50 rounded-lg p-3">
              <p className="font-semibold mb-2">Link de reset (ambiente de desenvolvimento):</p>
              <a className="text-primary-600 break-all" href={resetUrl}>
                {resetUrl}
              </a>
            </div>
          )}

          <div className="mt-6 text-center">
            <Link href="/login" className="text-primary-600 font-semibold hover:text-primary-700">
              Voltar ao login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
