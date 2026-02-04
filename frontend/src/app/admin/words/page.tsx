"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { useAuthStore } from "@/store/authStore";
import toast from "react-hot-toast";

interface Word {
  id: number;
  english: string;
  ipa?: string;
  portuguese: string;
  level: string;
  word_type?: string;
  definition_en?: string;
  definition_pt?: string;
  example_en?: string;
  example_pt?: string;
  synonyms?: string;
  antonyms?: string;
  collocations?: string;
  usage_notes?: string;
  audio_url?: string;
  tags?: string;
}

export default function AdminWordsPage() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [words, setWords] = useState<Word[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingWord, setEditingWord] = useState<Word | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }
    loadWords();
  }, [user, page, search, levelFilter]);

  const loadWords = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: "50",
        ...(search && { search }),
        ...(levelFilter && { level: levelFilter }),
      });

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setWords(response.data);
    } catch (error) {
      toast.error("Erro ao carregar palavras");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Tem certeza que deseja deletar esta palavra?")) return;

    try {
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words/${id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Palavra deletada com sucesso!");
      loadWords();
    } catch (error) {
      toast.error("Erro ao deletar palavra");
    }
  };

  const handleSave = async (wordData: Partial<Word>) => {
    try {
      if (editingWord?.id) {
        // Update
        await axios.patch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words/${editingWord.id}`,
          wordData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success("Palavra atualizada!");
      } else {
        // Create
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words`,
          wordData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        toast.success("Palavra criada!");
      }
      setShowModal(false);
      setEditingWord(null);
      loadWords();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Erro ao salvar palavra");
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImporting(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words/bulk`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const { created, updated, errors, total_processed } = response.data;

      if (errors.length > 0) {
        toast.error(`Importado com erros: ${created} criadas, ${updated} atualizadas, ${errors.length} erros`);
        console.error("Erros de importação:", errors);
      } else {
        toast.success(`Importação concluída! ${created} criadas, ${updated} atualizadas`);
      }

      loadWords();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Erro ao importar CSV");
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const downloadTemplate = () => {
    const csvContent = `english,ipa,portuguese,level,word_type,definition_en,definition_pt,example_en,example_pt,tags
hello,həˈloʊ,olá,A1,interjection,A greeting,Uma saudação,Hello! How are you?,Olá! Como você está?,greetings;basic
house,haʊs,casa,A1,noun,A building for living,Um edifício para morar,This is my house,Esta é minha casa,places;home`;

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "template_palavras.csv";
    a.click();
  };

  const handleExportCsv = async () => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words/export`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: "blob",
        }
      );

      const blob = new Blob([response.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);

      const disposition = response.headers?.["content-disposition"] as string | undefined;
      const match = disposition?.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || "words_export.csv";

      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Erro ao exportar CSV:", error);
      toast.error("Erro ao exportar CSV")
    }
  };

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-8">
      <div className="container mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <button
              onClick={() => router.push("/admin")}
              className="text-purple-600 hover:text-purple-800 mb-2 flex items-center gap-2"
            >
              ← Voltar ao Painel
            </button>
            <h1 className="text-4xl font-bold text-gray-800">Gerenciar Palavras</h1>
          </div>
          <div className="flex gap-4">
            <button
              onClick={handleExportCsv}
              className="bg-white border border-purple-200 text-purple-700 px-6 py-3 rounded-lg hover:bg-purple-50 transition-colors font-semibold"
            >
              ⬇️ Exportar CSV
            </button>
            <button
              onClick={downloadTemplate}
              className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-semibold"
            >
              📥 Baixar Template CSV
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={importing}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-semibold disabled:opacity-50"
            >
              {importing ? "Importando..." : "📤 Importar CSV"}
            </button>
            <button
              onClick={() => {
                setEditingWord(null);
                setShowModal(true);
              }}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold"
            >
              ➕ Nova Palavra
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleImport}
            title="Importar CSV de palavras"
            aria-label="Importar CSV de palavras"
            className="hidden"
          />
        </div>

        {/* Filtros */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input
              type="text"
              placeholder="Buscar palavra..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              title="Filtrar por nível"
              aria-label="Filtrar por nível"
              className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">Todos os níveis</option>
              <option value="A1">A1</option>
              <option value="A2">A2</option>
              <option value="B1">B1</option>
              <option value="B2">B2</option>
              <option value="C1">C1</option>
              <option value="C2">C2</option>
            </select>
            <button
              onClick={() => {
                setSearch("");
                setLevelFilter("");
              }}
              className="bg-gray-200 px-4 py-2 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Limpar Filtros
            </button>
          </div>
        </div>

        {/* Tabela */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-purple-600 text-white">
                <tr>
                  <th className="px-6 py-4 text-left">Inglês</th>
                  <th className="px-6 py-4 text-left">IPA</th>
                  <th className="px-6 py-4 text-left">Português</th>
                  <th className="px-6 py-4 text-left">Nível</th>
                  <th className="px-6 py-4 text-left">Tipo</th>
                  <th className="px-6 py-4 text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {words.map((word) => (
                  <tr key={word.id} className="border-b hover:bg-gray-50">
                    <td className="px-6 py-4 font-semibold">{word.english}</td>
                    <td className="px-6 py-4 text-gray-600">{word.ipa || "-"}</td>
                    <td className="px-6 py-4">{word.portuguese}</td>
                    <td className="px-6 py-4">
                      <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-semibold">
                        {word.level}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-600">{word.word_type || "-"}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => {
                          setEditingWord(word);
                          setShowModal(true);
                        }}
                        className="bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600 mr-2"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(word.id)}
                        className="bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600"
                      >
                        Deletar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {words.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                Nenhuma palavra encontrada
              </div>
            )}
          </div>
        )}

        {/* Paginação */}
        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="bg-white px-6 py-2 rounded-lg shadow hover:bg-gray-50 disabled:opacity-50"
          >
            ← Anterior
          </button>
          <span className="bg-white px-6 py-2 rounded-lg shadow">Página {page}</span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={words.length < 50}
            className="bg-white px-6 py-2 rounded-lg shadow hover:bg-gray-50 disabled:opacity-50"
          >
            Próxima →
          </button>
        </div>
      </div>

      {/* Modal de Edição/Criação */}
      {showModal && (
        <WordModal
          word={editingWord}
          token={token!}
          onClose={() => {
            setShowModal(false);
            setEditingWord(null);
          }}
          onSave={handleSave}
        />
      )}
    </div>
  );
}

// ============== MODAL DE EDIÇÃO ==============
function WordModal({
  word,
  token,
  onClose,
  onSave,
}: {
  word: Word | null;
  token: string;
  onClose: () => void;
  onSave: (word: Partial<Word>) => void;
}) {
  const [formData, setFormData] = useState<Partial<Word>>(
    word || {
      english: "",
      portuguese: "",
      level: "A1",
    }
  );
  const [isFillingAi, setIsFillingAi] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleAiFill = async () => {
    if (!word?.id) return;
    try {
      setIsFillingAi(true);
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/words/${word.id}/ai-fill`,
        {
          fields: [
            "word_type",
            "definition_en",
            "definition_pt",
            "example_en",
            "example_pt",
            "ipa",
            "synonyms",
            "antonyms",
          ],
          overwrite: false,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setFormData(response.data);
      toast.success("IA preencheu os campos faltantes!");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Erro ao preencher com IA");
    } finally {
      setIsFillingAi(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6">
            {word ? "Editar Palavra" : "Nova Palavra"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-sm text-gray-500">
                Use a IA para completar campos vazios desta palavra.
              </div>
              <button
                type="button"
                onClick={handleAiFill}
                disabled={!word?.id || isFillingAi}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                title={word?.id ? "Preencher com IA" : "Salve a palavra antes de usar a IA"}
              >
                {isFillingAi ? "Preenchendo..." : "✨ Preencher com IA"}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Inglês *
                </label>
                <input
                  type="text"
                  required
                  value={formData.english}
                  onChange={(e) => setFormData({ ...formData, english: e.target.value })}
                  title="Inglês"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  IPA (Pronúncia)
                </label>
                <input
                  type="text"
                  value={formData.ipa || ""}
                  onChange={(e) => setFormData({ ...formData, ipa: e.target.value })}
                  title="IPA (Pronúncia)"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Português *
                </label>
                <input
                  type="text"
                  required
                  value={formData.portuguese}
                  onChange={(e) => setFormData({ ...formData, portuguese: e.target.value })}
                  title="Português"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

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
                  Tipo de Palavra
                </label>
                <input
                  type="text"
                  placeholder="noun, verb, adjective..."
                  value={formData.word_type || ""}
                  onChange={(e) => setFormData({ ...formData, word_type: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Tags (separadas por vírgula)
                </label>
                <input
                  type="text"
                  placeholder="food, travel, business"
                  value={formData.tags || ""}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Definição (Inglês)
              </label>
              <textarea
                value={formData.definition_en || ""}
                onChange={(e) => setFormData({ ...formData, definition_en: e.target.value })}
                rows={2}
                title="Definição (Inglês)"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Definição (Português)
              </label>
              <textarea
                value={formData.definition_pt || ""}
                onChange={(e) => setFormData({ ...formData, definition_pt: e.target.value })}
                rows={2}
                title="Definição (Português)"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Exemplo (Inglês)
              </label>
              <textarea
                value={formData.example_en || ""}
                onChange={(e) => setFormData({ ...formData, example_en: e.target.value })}
                rows={2}
                title="Exemplo (Inglês)"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Exemplo (Português)
              </label>
              <textarea
                value={formData.example_pt || ""}
                onChange={(e) => setFormData({ ...formData, example_pt: e.target.value })}
                rows={2}
                title="Exemplo (Português)"
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
                {word ? "Atualizar" : "Criar"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
