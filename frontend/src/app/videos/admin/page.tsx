'use client';

import { useState, useEffect } from 'react';
import { videosApi } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import Image from 'next/image';

interface Video {
  id: number;
  title: string;
  description: string;
  youtube_id: string;
  youtube_url: string;
  thumbnail_url: string;
  level: string;
  category: string;
  tags: string;
  duration: number;
  views_count: number;
  is_active: boolean;
  is_featured: boolean;
  order_index: number;
  created_at: string;
}

type AxiosLikeError = {
  response?: {
    data?: {
      detail?: string;
    };
  };
};

function getErrorDetail(error: unknown): string | undefined {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const detail = (error as AxiosLikeError).response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  return undefined;
}

const CATEGORIES = {
  grammar: 'Gramática',
  vocabulary: 'Vocabulário',
  pronunciation: 'Pronúncia',
  listening: 'Compreensão Auditiva',
  conversation: 'Conversação',
  tips: 'Dicas de Estudo',
  culture: 'Cultura',
  other: 'Outros',
};

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'ALL'];

export default function VideoAdminPage() {
  const router = useRouter();
  const { user, token, isLoading: authLoading, fetchUser } = useAuthStore();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingVideo, setEditingVideo] = useState<Video | null>(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    youtube_url: '',
    level: 'A1',
    category: 'other',
    tags: '',
    duration: 0,
    is_active: true,
    is_featured: false,
    order_index: 0,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (authLoading) return;
    if (!token) {
      router.replace('/login');
      return;
    }
    if (!user?.is_admin) {
      router.replace('/videos');
      return;
    }
  }, [authLoading, token, user, router]);

  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    setLoading(true);
    try {
      const response = await videosApi.getVideos({
        per_page: 100,
      });
      setVideos(response.data.items);
    } catch (error) {
      console.error('Erro ao carregar vídeos:', error);
      setError('Erro ao carregar vídeos');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      if (editingVideo) {
        await videosApi.updateVideo(editingVideo.id, formData);
        setSuccess('Vídeo atualizado com sucesso!');
      } else {
        await videosApi.createVideo(formData);
        setSuccess('Vídeo criado com sucesso!');
      }

      resetForm();
      loadVideos();
    } catch (error: unknown) {
      console.error('Erro ao salvar vídeo:', error);
      setError(getErrorDetail(error) || 'Erro ao salvar vídeo');
    }
  };

  const handleEdit = (video: Video) => {
    setEditingVideo(video);
    setFormData({
      title: video.title,
      description: video.description,
      youtube_url: video.youtube_url,
      level: video.level,
      category: video.category,
      tags: video.tags,
      duration: video.duration,
      is_active: video.is_active,
      is_featured: video.is_featured,
      order_index: video.order_index,
    });
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja deletar este vídeo?')) {
      return;
    }

    try {
      await videosApi.deleteVideo(id);
      setSuccess('Vídeo deletado com sucesso!');
      loadVideos();
    } catch (error) {
      console.error('Erro ao deletar vídeo:', error);
      setError('Erro ao deletar vídeo');
    }
  };

  const resetForm = () => {
    setEditingVideo(null);
    setFormData({
      title: '',
      description: '',
      youtube_url: '',
      level: 'A1',
      category: 'other',
      tags: '',
      duration: 0,
      is_active: true,
      is_featured: false,
      order_index: 0,
    });
    setShowForm(false);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Administração de Vídeos
            </h1>
            <p className="text-gray-600">
              Gerencie os vídeos de aulas do YouTube
            </p>
          </div>
          <div className="flex space-x-4">
            <button
              onClick={() => router.push('/videos')}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              Ver Vídeos
            </button>
            <button
              onClick={() => {
                resetForm();
                setShowForm(!showForm);
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              {showForm ? 'Cancelar' : 'Novo Vídeo'}
            </button>
          </div>
        </div>

        {/* Mensagens */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
            {success}
          </div>
        )}

        {/* Formulário */}
        {showForm && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-2xl font-bold mb-6">
              {editingVideo ? 'Editar Vídeo' : 'Novo Vídeo'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Título */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Título *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) =>
                      setFormData({ ...formData, title: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ex: Aula de Present Perfect"
                  />
                </div>

                {/* URL do YouTube */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    URL do YouTube *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.youtube_url}
                    onChange={(e) =>
                      setFormData({ ...formData, youtube_url: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="https://www.youtube.com/watch?v=..."
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Cole a URL completa do vídeo do YouTube
                  </p>
                </div>

                {/* Descrição */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Descrição
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    rows={4}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Descreva o conteúdo da aula..."
                  />
                </div>

                {/* Nível */}
                <div>
                  <label
                    htmlFor="video-level"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Nível
                  </label>
                  <select
                    id="video-level"
                    value={formData.level}
                    onChange={(e) =>
                      setFormData({ ...formData, level: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    title="Nível"
                  >
                    {LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Categoria */}
                <div>
                  <label
                    htmlFor="video-category"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Categoria
                  </label>
                  <select
                    id="video-category"
                    value={formData.category}
                    onChange={(e) =>
                      setFormData({ ...formData, category: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    title="Categoria"
                  >
                    {Object.entries(CATEGORIES).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Tags */}
                <div>
                  <label
                    htmlFor="video-tags"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Tags
                  </label>
                  <input
                    id="video-tags"
                    type="text"
                    value={formData.tags}
                    onChange={(e) =>
                      setFormData({ ...formData, tags: e.target.value })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ex: presente, perfeito, verbos"
                  />
                  <p className="mt-1 text-sm text-gray-500">
                    Separe as tags por vírgula
                  </p>
                </div>

                {/* Duração */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Duração (segundos)
                  </label>
                  <input
                    type="number"
                    value={formData.duration}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        duration: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ex: 600 (10 minutos)"
                  />
                </div>

                {/* Ordem */}
                <div>
                  <label
                    htmlFor="video-order-index"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Ordem de Exibição
                  </label>
                  <input
                    id="video-order-index"
                    type="number"
                    value={formData.order_index}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        order_index: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Ativo */}
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) =>
                      setFormData({ ...formData, is_active: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <label
                    htmlFor="is_active"
                    className="ml-2 text-sm font-medium text-gray-700"
                  >
                    Vídeo ativo
                  </label>
                </div>

                {/* Destaque */}
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_featured"
                    checked={formData.is_featured}
                    onChange={(e) =>
                      setFormData({ ...formData, is_featured: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <label
                    htmlFor="is_featured"
                    className="ml-2 text-sm font-medium text-gray-700"
                  >
                    Vídeo em destaque
                  </label>
                </div>
              </div>

              <div className="flex space-x-4 pt-4">
                <button
                  type="submit"
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                >
                  {editingVideo ? 'Atualizar' : 'Criar'} Vídeo
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 font-medium"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Lista de Vídeos */}
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vídeo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nível
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Categoria
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Visualizações
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Data
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {videos.map((video) => (
                  <tr key={video.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <Image
                          src={video.thumbnail_url}
                          alt={video.title}
                          className="h-12 w-20 rounded object-cover"
                          width={80}
                          height={48}
                        />
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">
                            {video.title}
                          </div>
                          <div className="text-sm text-gray-500">
                            ID: {video.youtube_id}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        {video.level}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {CATEGORIES[video.category as keyof typeof CATEGORIES]}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {video.views_count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex flex-col space-y-1">
                        {video.is_active ? (
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                            Ativo
                          </span>
                        ) : (
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                            Inativo
                          </span>
                        )}
                        {video.is_featured && (
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
                            Destaque
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(video.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => router.push(`/videos/${video.id}`)}
                        className="text-blue-600 hover:text-blue-900 mr-4"
                      >
                        Ver
                      </button>
                      <button
                        onClick={() => handleEdit(video)}
                        className="text-indigo-600 hover:text-indigo-900 mr-4"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(video.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Deletar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {videos.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500 text-lg">
                  Nenhum vídeo cadastrado ainda
                </p>
                <button
                  onClick={() => setShowForm(true)}
                  className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Adicionar Primeiro Vídeo
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
