"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { useAuthStore } from "@/store/authStore";

interface AdminStats {
  total_users: number;
  active_users: number;
  total_words: number;
  total_sentences: number;
  total_videos: number;
  total_reviews: number;
  words_by_level: Record<string, number>;
}

export default function AdminDashboard() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "words" | "sentences" | "videos" | "users" | "reading_writing">("overview");

  useEffect(() => {
    // Verificar se é admin
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }

    loadStats();
  }, [user, router]);

  const loadStats = async () => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/stats`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setStats(response.data);
    } catch (error) {
      console.error("Erro ao carregar estatísticas:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-orange-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-2xl shadow-lg">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Acesso Negado</h1>
          <p className="text-gray-600">Você não tem permissão para acessar esta área.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Carregando painel administrativo...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <Link
              href="/dashboard"
              className="inline-flex items-center px-4 py-2 rounded-lg border border-purple-200 bg-white text-purple-700 hover:bg-purple-50 transition-colors font-semibold mb-3"
            >
              ← Voltar ao Dashboard
            </Link>
            <h1 className="text-4xl font-bold text-gray-800 mb-2">Painel Administrativo</h1>
            <p className="text-gray-600">Gerencie todo o sistema IdiomasBR</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-lg mb-8">
          <div className="flex flex-wrap border-b">
            <button
              onClick={() => setActiveTab("overview")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "overview"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              📊 Visão Geral
            </button>
            <button
              onClick={() => setActiveTab("words")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "words"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              📖 Palavras
            </button>
            <button
              onClick={() => setActiveTab("sentences")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "sentences"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              💬 Sentenças
            </button>
            <button
              onClick={() => setActiveTab("videos")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "videos"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              🎥 Vídeos
            </button>
            <button
              onClick={() => setActiveTab("users")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "users"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              👥 Usuários
            </button>
            <button
              onClick={() => setActiveTab("reading_writing")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "reading_writing"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              ✍️ Leitura e Escrita
            </button>
          </div>

          <div className="p-6">
            {activeTab === "overview" && stats && (
              <OverviewTab stats={stats} />
            )}
            {activeTab === "words" && <WordsTab token={token!} />}
            {activeTab === "sentences" && <SentencesTab token={token!} />}
            {activeTab === "videos" && <VideosTab token={token!} />}
            {activeTab === "users" && <UsersTab token={token!} />}
            {activeTab === "reading_writing" && <ReadingWritingTab />}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============== TAB: VISÃO GERAL ==============
function OverviewTab({ stats }: { stats: AdminStats }) {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Estatísticas do Sistema</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Total de Usuários"
          value={stats.total_users}
          subtitle={`${stats.active_users} ativos (7 dias)`}
          icon="👥"
          color="bg-blue-500"
        />
        <StatCard
          title="Palavras"
          value={stats.total_words}
          subtitle="Vocabulário disponível"
          icon="📖"
          color="bg-green-500"
        />
        <StatCard
          title="Sentenças"
          value={stats.total_sentences}
          subtitle="Exemplos práticos"
          icon="💬"
          color="bg-purple-500"
        />
        <StatCard
          title="Vídeos"
          value={stats.total_videos}
          subtitle="Conteúdo educacional"
          icon="🎥"
          color="bg-red-500"
        />
        <StatCard
          title="Total de Reviews"
          value={stats.total_reviews}
          subtitle="Interações de estudo"
          icon="✅"
          color="bg-yellow-500"
        />
        <StatCard
          title="Taxa de Engajamento"
          value={`${Math.round((stats.active_users / stats.total_users) * 100)}%`}
          subtitle="Usuários ativos"
          icon="📈"
          color="bg-indigo-500"
        />
      </div>

      <div className="bg-gray-50 rounded-xl p-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4">Palavras por Nível</h3>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          {Object.entries(stats.words_by_level).map(([level, count]) => (
            <div key={level} className="bg-white rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-purple-600">{count}</div>
              <div className="text-sm text-gray-600 font-semibold">{level}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, subtitle, icon, color }: any) {
  const borderClass =
    color === "bg-blue-500"
      ? "border-blue-500"
      : color === "bg-green-500"
        ? "border-green-500"
        : color === "bg-purple-500"
          ? "border-purple-500"
          : color === "bg-red-500"
            ? "border-red-500"
            : color === "bg-yellow-500"
              ? "border-yellow-500"
              : color === "bg-indigo-500"
                ? "border-indigo-500"
                : "border-gray-300";

  return (
    <div className={`bg-white rounded-xl p-6 shadow-md border-l-4 ${borderClass}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-4xl">{icon}</div>
        <div className={`${color} text-white text-2xl font-bold px-3 py-1 rounded-lg`}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
      </div>
      <h3 className="text-gray-600 font-semibold">{title}</h3>
      <p className="text-sm text-gray-500">{subtitle}</p>
    </div>
  );
}

// ============== TAB: PALAVRAS ==============
function WordsTab({ token }: { token: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Gerenciar Palavras</h2>
        <Link
          href="/admin/words"
          className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold inline-block"
        >
          ➕ Gerenciar Palavras
        </Link>
      </div>
      <p className="text-gray-600">
        Adicione, edite ou remova palavras do vocabulário. Suporta importação em massa via CSV.
      </p>
    </div>
  );
}

// ============== TAB: SENTENÇAS ==============
function SentencesTab({ token }: { token: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Gerenciar Sentenças</h2>
        <Link
          href="/admin/sentences"
          className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold inline-block"
        >
          ➕ Gerenciar Sentenças
        </Link>
      </div>
      <p className="text-gray-600">
        Gerencie frases de exemplo e contextos práticos para o aprendizado.
      </p>
    </div>
  );
}

// ============== TAB: VÍDEOS ==============
function VideosTab({ token }: { token: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Gerenciar Vídeos</h2>
        <Link
          href="/admin/videos"
          className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold inline-block"
        >
          ➕ Adicionar Vídeo
        </Link>
      </div>
      <p className="text-gray-600">
        Adicione vídeos educacionais do YouTube para complementar o aprendizado.
      </p>
    </div>
  );
}

// ============== TAB: USUÁRIOS ==============
function UsersTab({ token }: { token: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Gerenciar Usuários</h2>
        <Link
          href="/admin/users"
          className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold inline-block"
        >
          👥 Ver Todos os Usuários
        </Link>
      </div>
      <p className="text-gray-600">
        Visualize, edite ou remova usuários do sistema. Gerencie permissões de administrador.
      </p>
    </div>
  );
}

// ============== TAB: LEITURA E ESCRITA ==============
function ReadingWritingTab() {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Leitura e Escrita</h2>
        <Link
          href="/admin/texts"
          className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold inline-block"
        >
          📚 Gerenciar Textos
        </Link>
      </div>
      <p className="text-gray-600">
        Cadastre textos com tradução e áudio para o aluno estudar em /texts.
      </p>
    </div>
  );
}
