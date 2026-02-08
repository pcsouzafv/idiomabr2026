"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

export default function AdminReadingWritingPage() {
  const router = useRouter();
  const { user } = useAuthStore();

  useEffect(() => {
    if (!user?.is_admin) {
      router.push("/dashboard");
    }
  }, [user, router]);

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <Link
              href="/admin"
              className="inline-flex items-center px-4 py-2 rounded-lg border border-purple-200 bg-white text-purple-700 hover:bg-purple-50 transition-colors font-semibold mb-3"
            >
              ← Voltar ao Painel Administrativo
            </Link>
            <h1 className="text-4xl font-bold text-gray-800 mb-2">Leitura e Escrita</h1>
            <p className="text-gray-600">Configuração do módulo (placeholder)</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <p className="text-gray-600">
              Use este módulo para cadastrar textos com tradução e áudio. A prática do aluno acontece em
              <span className="font-semibold text-gray-900"> /texts</span>.
            </p>
            <Link
              href="/admin/texts"
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold inline-block"
            >
              📚 Gerenciar Textos
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
