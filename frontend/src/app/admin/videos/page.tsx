"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { useAuthStore } from "@/store/authStore";

interface Video {
  id: number;
  title: string;
  description?: string;
  youtube_id: string;
  youtube_url: string;
  thumbnail_url: string;
  level: string;
  category: string;
  tags?: string;
  duration?: number;
  is_active: boolean;
  is_featured: boolean;
}

export default function AdminVideosPage() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [editingVideo, setEditingVideo] = useState<Video | null>(null);

  useEffect(() => {
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }
    loadVideos();
  }, [user, page]);

  const loadVideos = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/videos?page=${page}&per_page=50`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setVideos(response.data.items || []);
      setTotalPages(response.data.pages || 1);
    } catch (error) {
      console.error("Erro ao carregar vídeos:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Tem certeza que deseja deletar este vídeo?")) return;

    try {
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/videos/${id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadVideos();
    } catch (error) {
      console.error("Erro ao deletar vídeo:", error);
      alert("Erro ao deletar vídeo");
    }
  };

  const handleSave = async (videoData: Partial<Video>) => {
    try {
      if (editingVideo?.id) {
        await axios.patch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/admin/videos/${editingVideo.id}`,
          videoData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        alert("Vídeo atualizado com sucesso!");
      } else {
        await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/admin/videos`,
          videoData,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        alert("Vídeo criado com sucesso!");
      }
      setShowModal(false);
      setEditingVideo(null);
      loadVideos();
    } catch (error: any) {
      console.error("Erro ao salvar vídeo:", error);
      alert(error.response?.data?.detail || "Erro ao salvar vídeo");
    }
  };

  const handleExportCsv = async () => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/videos/export`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: "blob",
        }
      );

      const blob = new Blob([response.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);

      const disposition = response.headers?.["content-disposition"] as string | undefined;
      const match = disposition?.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || "videos_export.csv";

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

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex justify-between items-center">
          <div>
            <Link href="/admin" className="text-purple-600 hover:text-purple-700 mb-2 inline-block">
              ← Voltar ao Painel Admin
            </Link>
            <h1 className="text-4xl font-bold text-gray-800">Gerenciar Vídeos</h1>
            <p className="text-gray-600 mt-2">Adicione, edite ou remova vídeos educacionais</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleExportCsv}
              className="bg-white border border-purple-200 text-purple-700 px-6 py-3 rounded-lg hover:bg-purple-50 transition-colors font-semibold"
            >
              ⬇️ Exportar CSV
            </button>
            <button
              onClick={() => {
                setEditingVideo(null);
                setShowModal(true);
              }}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold"
            >
              ➕ Adicionar Vídeo
            </button>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Carregando vídeos...</p>
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600 text-lg">Nenhum vídeo encontrado</p>
              <p className="text-gray-500 mt-2">Clique em "Adicionar Vídeo" para adicionar o primeiro</p>
            </div>
          ) : (
            <>
              <div className="mb-4 text-sm text-gray-600">
                Total: {videos.length} vídeos (Página {page} de {totalPages})
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map((video) => (
                  <div key={video.id} className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
                    <div className="relative h-48 bg-gray-200">
                      {video.thumbnail_url ? (
                        <img src={video.thumbnail_url} alt={video.title} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">🎥 Sem thumbnail</div>
                      )}
                      {video.duration && video.duration > 0 && (
                        <span className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white px-2 py-1 rounded text-sm">
                          {formatDuration(video.duration)}
                        </span>
                      )}
                    </div>

                    <div className="p-4">
                      <h3 className="font-bold text-gray-800 mb-2 line-clamp-2">{video.title}</h3>
                      <div className="flex gap-2 mb-3">
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-semibold">{video.level}</span>
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs font-semibold">{video.category}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <a href={video.youtube_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-700 text-sm font-semibold">
                          Ver no YouTube →
                        </a>
                        <div className="flex gap-2">
                          <button onClick={() => { setEditingVideo(video); setShowModal(true); }} className="text-gray-600 hover:text-gray-700">✏️</button>
                          <button onClick={() => handleDelete(video.id)} className="text-red-600 hover:text-red-700">🗑️</button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="mt-6 flex justify-center gap-2">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-4 py-2 bg-gray-200 rounded-lg disabled:opacity-50">
                    Anterior
                  </button>
                  <span className="px-4 py-2">Página {page} de {totalPages}</span>
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-4 py-2 bg-gray-200 rounded-lg disabled:opacity-50">
                    Próxima
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {showModal && (
        <VideoModal video={editingVideo} onClose={() => { setShowModal(false); setEditingVideo(null); }} onSave={handleSave} />
      )}
    </div>
  );
}

function VideoModal({ video, onClose, onSave }: { video: Video | null; onClose: () => void; onSave: (video: Partial<Video>) => void; }) {
  const [formData, setFormData] = useState<Partial<Video>>(
    video || {
      title: "",
      description: "",
      youtube_id: "",
      youtube_url: "",
      thumbnail_url: "",
      level: "A1",
      category: "other",
      tags: "",
      duration: 0,
      is_active: true,
      is_featured: false,
    }
  );

  const extractYoutubeId = (url: string) => {
    const match = url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/);
    return match ? match[1] : "";
  };

  const handleUrlChange = (url: string) => {
    const youtubeId = extractYoutubeId(url);
    setFormData({
      ...formData,
      youtube_url: url,
      youtube_id: youtubeId,
      thumbnail_url: youtubeId ? `https://img.youtube.com/vi/${youtubeId}/maxresdefault.jpg` : "",
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6">{video ? "Editar Vídeo" : "Novo Vídeo"}</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">URL do YouTube *</label>
              <input type="url" required value={formData.youtube_url} onChange={(e) => handleUrlChange(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="https://youtube.com/watch?v=..." />
              {formData.youtube_id && <p className="text-xs text-green-600 mt-1">✓ ID extraído: {formData.youtube_id}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Título *</label>
              <input type="text" required value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Descrição</label>
              <textarea value={formData.description || ""} onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3} className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Nível *</label>
                <select required value={formData.level} onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500">
                  <option value="A1">A1</option>
                  <option value="A2">A2</option>
                  <option value="B1">B1</option>
                  <option value="B2">B2</option>
                  <option value="C1">C1</option>
                  <option value="C2">C2</option>
                  <option value="ALL">Todos</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Categoria *</label>
                <select required value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500">
                  <option value="grammar">Gramática</option>
                  <option value="vocabulary">Vocabulário</option>
                  <option value="pronunciation">Pronúncia</option>
                  <option value="listening">Listening</option>
                  <option value="conversation">Conversação</option>
                  <option value="tips">Dicas</option>
                  <option value="culture">Cultura</option>
                  <option value="other">Outros</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Duração (segundos)</label>
                <input type="number" min="0" value={formData.duration || 0} onChange={(e) => setFormData({ ...formData, duration: parseInt(e.target.value) })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500" />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">Tags</label>
                <input type="text" value={formData.tags || ""} onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="grammar, beginner, verbs" />
              </div>
            </div>

            <div className="flex gap-4">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })} className="w-4 h-4" />
                <span className="text-sm font-semibold text-gray-700">Ativo</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={formData.is_featured} onChange={(e) => setFormData({ ...formData, is_featured: e.target.checked })} className="w-4 h-4" />
                <span className="text-sm font-semibold text-gray-700">Destaque</span>
              </label>
            </div>

            <div className="flex justify-end gap-4 pt-6">
              <button type="button" onClick={onClose} className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-semibold">
                Cancelar
              </button>
              <button type="submit" className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold">
                {video ? "Atualizar" : "Criar"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
