"use client";

import { useCallback, useEffect, useState } from "react";
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

interface AdminPerformanceOverview {
  total_users: number;
  active_users: number;
  total_reviews: number;
  total_unique_words: number;
  accuracy_percent: number;
  reviews_per_active_user: number;
}

interface AdminUserPerformance {
  user_id: number;
  name: string;
  email: string;
  last_study_date?: string | null;
  current_streak: number;
  total_reviews: number;
  unique_words: number;
  accuracy_percent: number;
}

interface AdminPerformanceReport {
  period_days: number;
  overview: AdminPerformanceOverview;
  users: AdminUserPerformance[];
}

type BudgetStatus = "ok" | "warning" | "critical" | "unconfigured";

interface AdminAIUsageOverview {
  period_days: number;
  total_requests: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  budget_tokens: number;
  budget_used_percent: number;
  remaining_tokens?: number | null;
  budget_status: BudgetStatus;
}

interface AdminAIUsageUser {
  user_id: number;
  name: string;
  email: string;
  total_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  last_usage_at?: string | null;
}

interface AdminAIUsageProvider {
  provider: string;
  model?: string | null;
  total_requests: number;
  total_tokens: number;
}

interface AdminAIUsageReport {
  generated_at: string;
  overview: AdminAIUsageOverview;
  users: AdminAIUsageUser[];
  providers: AdminAIUsageProvider[];
  system_usage_requests: number;
  system_usage_tokens: number;
}

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle: string;
  icon: string;
  color: string;
}

export default function AdminDashboard() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "words" | "sentences" | "videos" | "users" | "reading_writing" | "performance" | "ai_usage">("overview");

  const loadStats = useCallback(async () => {
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
  }, [token]);

  useEffect(() => {
    // Verificar se é admin
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }

    void loadStats();
  }, [user, router, loadStats]);

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
              ✍️ Slow Listening & Speaking Practice
            </button>
            <button
              onClick={() => setActiveTab("performance")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "performance"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              📈 Desempenho
            </button>
            <button
              onClick={() => setActiveTab("ai_usage")}
              className={`flex-1 px-6 py-4 font-semibold transition-colors ${
                activeTab === "ai_usage"
                  ? "bg-purple-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              🤖 Uso de IA
            </button>
          </div>

          <div className="p-6">
            {activeTab === "overview" && stats && (
              <OverviewTab stats={stats} />
            )}
            {activeTab === "words" && <WordsTab />}
            {activeTab === "sentences" && <SentencesTab />}
            {activeTab === "videos" && <VideosTab />}
            {activeTab === "users" && <UsersTab />}
            {activeTab === "reading_writing" && <ReadingWritingTab />}
            {activeTab === "performance" && <PerformanceTab token={token!} />}
            {activeTab === "ai_usage" && <AIUsageTab token={token!} />}
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

function StatCard({ title, value, subtitle, icon, color }: StatCardProps) {
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

// ============== TAB: DESEMPENHO ==============
function PerformanceTab({ token }: { token: string }) {
  const [report, setReport] = useState<AdminPerformanceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const loadReport = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/performance`,
        {
          params: { days },
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setReport(response.data);
    } catch (error) {
      console.error("Erro ao carregar relatório de desempenho:", error);
    } finally {
      setLoading(false);
    }
  }, [days, token]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="text-center text-gray-600 py-12">
        Não foi possível carregar o relatório.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Desempenho dos Alunos</h2>
          <p className="text-sm text-gray-600">Visão geral e individual do período selecionado.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-semibold text-gray-600">Período:</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            aria-label="Período do relatório"
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
            <option value={180}>Últimos 180 dias</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Usuários ativos"
          value={report.overview.active_users}
          subtitle={`${report.overview.total_users} usuários totais`}
          icon="🟢"
          color="bg-green-500"
        />
        <StatCard
          title="Reviews no período"
          value={report.overview.total_reviews}
          subtitle={`${report.overview.total_unique_words} palavras únicas`}
          icon="✅"
          color="bg-blue-500"
        />
        <StatCard
          title="Precisão média"
          value={`${report.overview.accuracy_percent.toFixed(1)}%`}
          subtitle={`Média ${report.overview.reviews_per_active_user.toFixed(1)} reviews/aluno ativo`}
          icon="🎯"
          color="bg-purple-500"
        />
      </div>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Desempenho individual</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Aluno</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Reviews</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Palavras únicas</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Precisão</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Streak</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Último estudo</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {report.users.map((user) => (
                <tr key={user.user_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-semibold text-gray-800">{user.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{user.email}</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-700">{user.total_reviews}</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-700">{user.unique_words}</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-700">{user.accuracy_percent.toFixed(1)}%</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-700">{user.current_streak}</td>
                  <td className="px-6 py-4 text-sm text-right text-gray-600">
                    {user.last_study_date ? new Date(user.last_study_date).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function AIUsageTab({ token }: { token: string }) {
  const [report, setReport] = useState<AdminAIUsageReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const loadReport = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/ai-usage`,
        {
          params: { days, limit: 100 },
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      setReport(response.data);
    } catch (error) {
      console.error("Erro ao carregar relatório de uso de IA:", error);
    } finally {
      setLoading(false);
    }
  }, [days, token]);

  useEffect(() => {
    void loadReport();
  }, [loadReport]);

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
      </div>
    );
  }

  if (!report) {
    return <div className="text-center text-gray-600 py-12">Não foi possível carregar o relatório de IA.</div>;
  }

  const statusStyles: Record<BudgetStatus, string> = {
    ok: "bg-emerald-100 text-emerald-800",
    warning: "bg-amber-100 text-amber-800",
    critical: "bg-red-100 text-red-800",
    unconfigured: "bg-gray-100 text-gray-700",
  };

  const statusLabel: Record<BudgetStatus, string> = {
    ok: "Dentro do orçamento",
    warning: "Próximo do limite",
    critical: "Acima do limite",
    unconfigured: "Sem orçamento configurado",
  };

  const topUser = report.users[0];
  const budgetConfigured = report.overview.budget_tokens > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Uso de IA por usuário</h2>
          <p className="text-sm text-gray-600">Consumo de tokens para monitorar custos e planejar limites.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm font-semibold text-gray-600">Período:</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            aria-label="Período do relatório de IA"
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
            <option value={180}>Últimos 180 dias</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Tokens totais"
          value={report.overview.total_tokens}
          subtitle={`${report.overview.total_prompt_tokens} prompt + ${report.overview.total_completion_tokens} resposta`}
          icon="🧮"
          color="bg-indigo-500"
        />
        <StatCard
          title="Requisições IA"
          value={report.overview.total_requests}
          subtitle={`Período de ${report.overview.period_days} dias`}
          icon="🤖"
          color="bg-blue-500"
        />
        <StatCard
          title="Maior consumo"
          value={topUser ? topUser.total_tokens : 0}
          subtitle={topUser ? topUser.name : "Sem dados"}
          icon="🏅"
          color="bg-purple-500"
        />
      </div>

      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h3 className="text-lg font-semibold text-gray-800">Saúde do orçamento</h3>
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusStyles[report.overview.budget_status]}`}>
            {statusLabel[report.overview.budget_status]}
          </span>
        </div>

        {budgetConfigured ? (
          <div className="space-y-3">
            <div className="text-sm text-gray-700">
              Orçamento configurado: <strong>{report.overview.budget_tokens.toLocaleString()}</strong> tokens
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full ${
                  report.overview.budget_status === "critical"
                    ? "bg-red-500"
                    : report.overview.budget_status === "warning"
                      ? "bg-amber-500"
                      : "bg-emerald-500"
                }`}
                style={{ width: `${Math.min(100, report.overview.budget_used_percent)}%` }}
              />
            </div>
            <div className="text-sm text-gray-700">
              Uso atual: <strong>{report.overview.budget_used_percent.toFixed(2)}%</strong> | Restante:{" "}
              <strong>{(report.overview.remaining_tokens ?? 0).toLocaleString()}</strong> tokens
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-600">
            Configure `AI_USAGE_BUDGET_TOKENS` no backend para receber alerta de “token acabando”.
          </p>
        )}

        {report.system_usage_tokens > 0 ? (
          <p className="text-xs text-gray-500 mt-3">
            Uso não vinculado a usuário: {report.system_usage_tokens.toLocaleString()} tokens em{" "}
            {report.system_usage_requests.toLocaleString()} requisições.
          </p>
        ) : null}
      </div>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Consumo por usuário</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuário</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Req.</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Prompt</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Resposta</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Último uso</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {report.users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-6 text-center text-sm text-gray-500">
                    Nenhum consumo no período selecionado.
                  </td>
                </tr>
              ) : (
                report.users.map((usage) => (
                  <tr key={usage.user_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-semibold text-gray-800">{usage.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{usage.email}</td>
                    <td className="px-6 py-4 text-sm text-right text-gray-700">
                      {usage.total_requests.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-gray-700">
                      {usage.prompt_tokens.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-gray-700">
                      {usage.completion_tokens.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-right font-semibold text-gray-800">
                      {usage.total_tokens.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-right text-gray-600">
                      {usage.last_usage_at ? new Date(usage.last_usage_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Consumo por provedor/modelo</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provedor</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Modelo</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Requisições</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Tokens</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {report.providers.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-6 text-center text-sm text-gray-500">
                    Sem dados de provedor/modelo no período.
                  </td>
                </tr>
              ) : (
                report.providers.map((provider, idx) => (
                  <tr key={`${provider.provider}-${provider.model ?? "none"}-${idx}`} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-semibold text-gray-800">{provider.provider}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{provider.model || "—"}</td>
                    <td className="px-6 py-4 text-sm text-right text-gray-700">
                      {provider.total_requests.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-right font-semibold text-gray-800">
                      {provider.total_tokens.toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ============== TAB: PALAVRAS ==============
function WordsTab() {
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
function SentencesTab() {
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
function VideosTab() {
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
function UsersTab() {
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

// ============== TAB: SLOW LISTENING & SPEAKING PRACTICE ==============
function ReadingWritingTab() {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Slow Listening & Speaking Practice</h2>
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
