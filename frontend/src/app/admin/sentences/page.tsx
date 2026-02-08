"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { useAuthStore } from "@/store/authStore";

interface Sentence {
  id: number;
  english: string;
  portuguese: string;
  level: string;
  category: string;
  grammar_points?: string;
  vocabulary_used?: string;
  difficulty_score?: number;
}

export default function AdminSentencesPage() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [editingSentence, setEditingSentence] = useState<Sentence | null>(null);

  useEffect(() => {
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }
    loadSentences();
  }, [user, page]);

  const loadSentences = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/sentences?page=${page}&per_page=50`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSentences(response.data.items || []);
      setTotalPages(response.data.pages || 1);
    } catch (error) {
      console.error("Erro ao carregar sentenças:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Tem certeza que deseja deletar esta sentença?")) return;

    try {
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/sentences/${id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadSentences();
    } catch (error) {
      console.error("Erro ao deletar sentença:", error);
      alert("Erro ao deletar sentença");
    }
  };

  const handleSave = async (sentenceData: Partial<Sentence>) => {
    try {
      if (editingSentence?.id) {
        await axios.patch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/admin/sentences/${editingSentence.id}`,
          sentenceData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        alert("Sentença atualizada com sucesso!");
      } else {
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/admin/sentences`,
          sentenceData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        alert("Sentença criada com sucesso!");
      }
      setShowModal(false);
      setEditingSentence(null);
      loadSentences();
    } catch (error: any) {
      console.error("Erro ao salvar sentença:", error);
      alert(error.response?.data?.detail || "Erro ao salvar sentença");
    }
  };

  const handleExportCsv = async () => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/sentences/export`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: "blob",
        }
      );

      const blob = new Blob([response.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);

      const disposition = response.headers?.["content-disposition"] as string | undefined;
      const match = disposition?.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || "sentences_export.csv";

      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Erro ao exportar CSV:", error);
      alert("Erro ao exportar CSV");
    }
  };

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <Link href="/admin" className="text-purple-600 hover:text-purple-700 mb-2 inline-block">
              ← Voltar ao Painel Admin
            </Link>
            <h1 className="text-4xl font-bold text-gray-800">Gerenciar Sentenças</h1>
            <p className="text-gray-600 mt-2">Adicione, edite ou remova sentenças de exemplo</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleExportCsv}
              className="bg-white border border-purple-200 text-purple-700 px-6 py-3 rounded-lg hover:bg-purple-50 transition-colors font-semibold"
            >
              ⬇️ Exportar CSV
            </button>
            <button
              onClick={() => alert("Funcionalidade de importação CSV em breve!")}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-semibold"
            >
              📤 Importar CSV
            </button>
            <button
              onClick={() => {
                setEditingSentence(null);
                setShowModal(true);
              }}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold"
            >
              ➕ Nova Sentença
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Carregando sentenças...</p>
            </div>
          ) : sentences.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600 text-lg">Nenhuma sentença encontrada</p>
              <p className="text-gray-500 mt-2">Clique em "Nova Sentença" para adicionar a primeira</p>
            </div>
          ) : (
            <>
              <div className="mb-4 text-sm text-gray-600">
                Total: {sentences.length} sentenças (Página {page} de {totalPages})
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">ID</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Inglês</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Português</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Nível</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Categoria</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-700">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sentences.map((sentence) => (
                      <tr key={sentence.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-gray-600">{sentence.id}</td>
                        <td className="py-3 px-4 font-medium text-gray-800">{sentence.english}</td>
                        <td className="py-3 px-4 text-gray-600">{sentence.portuguese}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm font-semibold">
                            {sentence.level}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-600">{sentence.category}</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setEditingSentence(sentence);
                              setShowModal(true);
                            }}
                            className="text-blue-600 hover:text-blue-700 font-semibold mr-3"
                          >
                            Editar
                          </button>
                          <button
                            onClick={() => handleDelete(sentence.id)}
                            className="text-red-600 hover:text-red-700 font-semibold"
                          >
                            Deletar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-6 flex justify-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 bg-gray-200 rounded-lg disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <span className="px-4 py-2">
                    Página {page} de {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-4 py-2 bg-gray-200 rounded-lg disabled:opacity-50"
                  >
                    Próxima
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Modal de Criação/Edição */}
      {showModal && (
        <SentenceModal
          sentence={editingSentence}
          onClose={() => {
            setShowModal(false);
            setEditingSentence(null);
          }}
          onSave={handleSave}
        />
      )}
    </div>
  );
}

// ============== MODAL DE EDIÇÃO ==============
function SentenceModal({
  sentence,
  onClose,
  onSave,
}: {
  sentence: Sentence | null;
  onClose: () => void;
  onSave: (sentence: Partial<Sentence>) => void;
}) {
  const [formData, setFormData] = useState<Partial<Sentence>>(
    sentence || {
      english: "",
      portuguese: "",
      level: "A1",
      category: "",
      grammar_points: "",
      vocabulary_used: "",
      difficulty_score: 0,
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6">
            {sentence ? "Editar Sentença" : "Nova Sentença"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Inglês *
              </label>
              <textarea
                required
                value={formData.english}
                onChange={(e) => setFormData({ ...formData, english: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="The quick brown fox jumps over the lazy dog"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Português *
              </label>
              <textarea
                required
                value={formData.portuguese}
                onChange={(e) => setFormData({ ...formData, portuguese: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="A rápida raposa marrom pula sobre o cachorro preguiçoso"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Nível *
                </label>
                <select
                  required
                  value={formData.level}
                  onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                  title="Nível"
                  aria-label="Nível"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="A1">A1</option>
                  <option value="A2">A2</option>
                  <option value="B1">B1</option>
                  <option value="B2">B2</option>
                  <option value="C1">C1</option>
                  <option value="C2">C2</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Categoria
                </label>
                <input
                  type="text"
                  value={formData.category || ""}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="conversation, business, travel..."
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Pontos Gramaticais
              </label>
              <input
                type="text"
                value={formData.grammar_points || ""}
                onChange={(e) => setFormData({ ...formData, grammar_points: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="present simple, past continuous..."
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Vocabulário Utilizado
              </label>
              <input
                type="text"
                value={formData.vocabulary_used || ""}
                onChange={(e) => setFormData({ ...formData, vocabulary_used: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="quick, brown, fox, jump..."
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Dificuldade (0-10)
              </label>
              <input
                type="number"
                min="0"
                max="10"
                step="0.1"
                value={formData.difficulty_score || 0}
                onChange={(e) => setFormData({ ...formData, difficulty_score: parseFloat(e.target.value) })}
                title="Dificuldade (0-10)"
                aria-label="Dificuldade (0-10)"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="flex justify-end gap-4 pt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold"
              >
                {sentence ? "Atualizar" : "Criar"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
