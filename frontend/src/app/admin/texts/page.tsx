"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";

type AxiosLikeError = {
  response?: {
    data?: {
      detail?: string;
    };
  };
};

function getErrorDetail(error: unknown): string | undefined {
  if (typeof error === "object" && error !== null && "response" in error) {
    const detail = (error as AxiosLikeError).response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return undefined;
}

interface StudyTextAdminListItem {
  id: number;
  title: string;
  level: string;
  audio_url?: string | null;
  created_at: string;
  updated_at: string;
}

interface StudyTextAdminDetail {
  id: number;
  title: string;
  level: string;
  content_en: string;
  content_pt?: string | null;
  audio_url?: string | null;
  tags?: unknown;
  created_at: string;
  updated_at: string;
}

type FormState = {
  title: string;
  level: string;
  audio_url: string;
  content_en: string;
  content_pt: string;
};

const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"] as const;

export default function AdminTextsPage() {
  const router = useRouter();
  const { user, token } = useAuthStore();

  const [items, setItems] = useState<StudyTextAdminListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [generatingAudio, setGeneratingAudio] = useState(false);

  const [form, setForm] = useState<FormState>({
    title: "",
    level: "A1",
    audio_url: "",
    content_en: "",
    content_pt: "",
  });

  const firstFieldRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (showModal) {
      setTimeout(() => firstFieldRef.current?.focus(), 0);
    }
  }, [showModal]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: "50",
        ...(search && { search }),
        ...(levelFilter && { level: levelFilter }),
      });

      const res = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/texts?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setItems(res.data);
    } catch (e) {
      console.error(e);
      toast.error("Erro ao carregar textos");
    } finally {
      setLoading(false);
    }
  }, [levelFilter, page, search, token]);

  useEffect(() => {
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }
    void load();
  }, [user, router, load]);

  // Debounced search avoids one request per keystroke.
  useEffect(() => {
    const timer = setTimeout(() => {
      const normalizedSearch = searchInput.trim();
      setPage(1);
      setSearch((prev) => (prev === normalizedSearch ? prev : normalizedSearch));
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ title: "", level: "A1", audio_url: "", content_en: "", content_pt: "" });
    setShowModal(true);
  };

  const openEdit = async (id: number) => {
    setEditingId(id);
    setSaving(true);
    setShowModal(true);
    try {
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/texts/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const t: StudyTextAdminDetail = res.data;
      setForm({
        title: t.title || "",
        level: t.level || "A1",
        audio_url: t.audio_url || "",
        content_en: t.content_en || "",
        content_pt: t.content_pt || "",
      });
    } catch (e) {
      console.error(e);
      toast.error("Erro ao carregar texto");
      setShowModal(false);
      setEditingId(null);
    } finally {
      setSaving(false);
    }
  };

  const closeModal = () => {
    if (saving) return;
    setShowModal(false);
    setEditingId(null);
  };

  const save = async () => {
    if (!form.title.trim() || !form.content_en.trim()) {
      toast.error("Preencha título e texto (EN)");
      return;
    }

    setSaving(true);

    const payload = {
      title: form.title.trim(),
      level: form.level,
      audio_url: form.audio_url.trim() || null,
      content_en: form.content_en,
      content_pt: form.content_pt.trim() ? form.content_pt : null,
    };

    try {
      if (editingId) {
        await axios.patch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/texts/${editingId}`, payload, {
          headers: { Authorization: `Bearer ${token}` },
        });
        toast.success("Texto atualizado!");
      } else {
        await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/texts`, payload, {
          headers: { Authorization: `Bearer ${token}` },
        });
        toast.success("Texto criado!");
      }
      setShowModal(false);
      setEditingId(null);
      load();
    } catch (e) {
      console.error(e);
      toast.error("Erro ao salvar texto");
    } finally {
      setSaving(false);
    }
  };

  const generateAudio = async () => {
    if (!editingId) {
      toast.error("Salve o texto antes de gerar o áudio");
      return;
    }
    if (!form.content_en.trim()) {
      toast.error("Preencha o texto (EN) antes de gerar o áudio");
      return;
    }

    setGeneratingAudio(true);
    try {
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/texts/${editingId}/generate-audio?voice=nova`,
        null,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const updated: StudyTextAdminDetail = res.data;
      setForm((s) => ({ ...s, audio_url: updated.audio_url || "" }));
      toast.success("Áudio gerado!");
      load();
    } catch (e: unknown) {
      const msg = getErrorDetail(e);
      toast.error(typeof msg === "string" ? msg : "Erro ao gerar áudio");
      console.error(e);
    } finally {
      setGeneratingAudio(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Tem certeza que deseja deletar este texto?")) return;

    try {
      await axios.delete(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/texts/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("Texto deletado!");
      load();
    } catch (e) {
      console.error(e);
      toast.error("Erro ao deletar texto");
    }
  };

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <Link
              href="/admin"
              className="inline-flex items-center px-4 py-2 rounded-lg border border-purple-200 bg-white text-purple-700 hover:bg-purple-50 transition-colors font-semibold mb-3"
            >
              ← Voltar ao Painel Administrativo
            </Link>
            <h1 className="text-3xl font-bold text-gray-800">Textos (Slow Listening & Speaking Practice)</h1>
            <p className="text-gray-600">Gerencie textos, tradução e áudio (URL)</p>
          </div>

          <button
            onClick={openCreate}
            className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold"
          >
            ➕ Novo Texto
          </button>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between mb-4">
            <input
              aria-label="Buscar textos"
              value={searchInput}
              onChange={(e) => {
                setSearchInput(e.target.value);
              }}
              placeholder="Buscar por título ou conteúdo (EN)"
              className="w-full md:max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />

            <select
              aria-label="Filtrar por nível"
              title="Filtrar por nível"
              value={levelFilter}
              onChange={(e) => {
                setPage(1);
                setLevelFilter(e.target.value);
              }}
              className="w-full md:w-48 px-4 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">Todos os níveis</option>
              {LEVELS.map((lvl) => (
                <option key={lvl} value={lvl}>
                  {lvl}
                </option>
              ))}
            </select>
          </div>

          {loading ? (
            <p className="text-gray-600">Carregando...</p>
          ) : items.length === 0 ? (
            <p className="text-gray-600">Nenhum texto encontrado.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 text-gray-600 font-semibold">Título</th>
                    <th className="text-left p-3 text-gray-600 font-semibold">Nível</th>
                    <th className="text-left p-3 text-gray-600 font-semibold">Áudio</th>
                    <th className="text-right p-3 text-gray-600 font-semibold">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((t) => (
                    <tr key={t.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">
                        <div className="font-semibold text-gray-900">{t.title}</div>
                        <div className="text-xs text-gray-500">ID: {t.id}</div>
                      </td>
                      <td className="p-3">
                        <span className="text-xs font-semibold px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          {t.level}
                        </span>
                      </td>
                      <td className="p-3">
                        {t.audio_url ? (
                          <span className="text-xs font-semibold px-2 py-1 bg-green-100 text-green-700 rounded">
                            Sim
                          </span>
                        ) : (
                          <span className="text-xs font-semibold px-2 py-1 bg-gray-100 text-gray-600 rounded">
                            Não
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <div className="inline-flex gap-2">
                          <button
                            onClick={() => openEdit(t.id)}
                            className="px-3 py-1 rounded-lg border border-gray-300 hover:bg-gray-100 text-gray-700"
                          >
                            Editar
                          </button>
                          <button
                            onClick={() => remove(t.id)}
                            className="px-3 py-1 rounded-lg border border-red-200 hover:bg-red-50 text-red-700"
                          >
                            Deletar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex justify-between items-center mt-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
            >
              ← Anterior
            </button>
            <span className="text-sm text-gray-600">Página {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!loading && items.length < 50}
              className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
            >
              Próxima →
            </button>
          </div>
        </div>
      </div>

      {showModal ? (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-lg w-full max-w-3xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">
                {editingId ? "Editar Texto" : "Novo Texto"}
              </h2>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-800"
                disabled={saving}
              >
                ✕
              </button>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="text-title" className="text-sm font-semibold text-gray-700">Título</label>
                <input
                  ref={firstFieldRef}
                  id="text-title"
                  value={form.title}
                  onChange={(e) => setForm((s) => ({ ...s, title: e.target.value }))}
                  placeholder="Ex: My first story"
                  className="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={saving}
                />
              </div>

              <div>
                <label htmlFor="text-level" className="text-sm font-semibold text-gray-700">Nível</label>
                <select
                  id="text-level"
                  title="Selecionar nível"
                  value={form.level}
                  onChange={(e) => setForm((s) => ({ ...s, level: e.target.value }))}
                  className="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg"
                  disabled={saving}
                >
                  {LEVELS.map((lvl) => (
                    <option key={lvl} value={lvl}>
                      {lvl}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label htmlFor="text-audio-url" className="text-sm font-semibold text-gray-700">Audio URL (opcional)</label>
                <div className="mt-1 flex flex-col md:flex-row gap-2">
                  <input
                    id="text-audio-url"
                    value={form.audio_url}
                    onChange={(e) => setForm((s) => ({ ...s, audio_url: e.target.value }))}
                    placeholder="https://.../audio.mp3"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    disabled={saving || generatingAudio}
                  />
                  <button
                    type="button"
                    onClick={generateAudio}
                    disabled={saving || generatingAudio || !editingId}
                    className="px-4 py-2 rounded-lg border border-purple-200 bg-white text-purple-700 hover:bg-purple-50 disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                    title={!editingId ? "Salve o texto primeiro" : "Gerar áudio com IA"}
                  >
                    {generatingAudio ? "Gerando..." : "Gerar áudio (IA)"}
                  </button>
                </div>
              </div>

              <div className="md:col-span-2">
                <label htmlFor="text-content-en" className="text-sm font-semibold text-gray-700">Texto (EN)</label>
                <textarea
                  id="text-content-en"
                  value={form.content_en}
                  onChange={(e) => setForm((s) => ({ ...s, content_en: e.target.value }))}
                  placeholder="Cole aqui o texto em inglês..."
                  className="mt-1 w-full min-h-[160px] px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={saving}
                />
              </div>

              <div className="md:col-span-2">
                <label htmlFor="text-content-pt" className="text-sm font-semibold text-gray-700">Tradução (PT) (opcional)</label>
                <textarea
                  id="text-content-pt"
                  value={form.content_pt}
                  onChange={(e) => setForm((s) => ({ ...s, content_pt: e.target.value }))}
                  placeholder="Cole aqui a tradução em português (opcional)..."
                  className="mt-1 w-full min-h-[140px] px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  disabled={saving}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={closeModal}
                className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50"
                disabled={saving}
              >
                Cancelar
              </button>
              <button
                onClick={save}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                disabled={saving}
              >
                {saving ? "Salvando..." : "Salvar"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
