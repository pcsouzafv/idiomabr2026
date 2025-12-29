'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import toast from 'react-hot-toast';
import { ArrowLeft, Plus, Edit, Trash2, Save, X } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface Sentence {
  id: number;
  english: string;
  portuguese: string;
  level: string;
  category: string | null;
  difficulty_score: number;
  grammar_points: string | null;
  vocabulary_used: string | null;
  created_at: string;
}

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
const CATEGORIES = [
  'conversation',
  'business',
  'travel',
  'daily_life',
  'education',
  'health',
  'technology',
  'culture',
  'other'
];

export default function SentencesAdminPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuthStore();

  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingSentence, setEditingSentence] = useState<Sentence | null>(null);

  const [formData, setFormData] = useState({
    english: '',
    portuguese: '',
    level: 'A1',
    category: 'conversation',
    difficulty_score: 0,
    grammar_points: '',
    vocabulary_used: ''
  });

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (user) {
      loadSentences();
    }
  }, [user]);

  const loadSentences = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/api/sentences/', {
        params: { mode: 'all', limit: 1000 },
      });
      setSentences(response.data);
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao carregar frases');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const payload = {
        ...formData,
        difficulty_score: parseFloat(formData.difficulty_score.toString()) || 0,
      };

      if (editingSentence) {
        await api.put(`/api/sentences/admin/${editingSentence.id}`, payload);
      } else {
        await api.post('/api/sentences/admin/create', payload);
      }

      toast.success(editingSentence ? 'Frase atualizada!' : 'Frase criada!');
      resetForm();
      loadSentences();
    } catch (error: unknown) {
      console.error('Erro:', error);
      const errorObj = error as { response?: { data?: { detail?: string } }; message?: string };
      toast.error(errorObj?.response?.data?.detail || errorObj?.message || 'Erro ao salvar frase');
    }
  };

  const handleEdit = (sentence: Sentence) => {
    setEditingSentence(sentence);
    setFormData({
      english: sentence.english,
      portuguese: sentence.portuguese,
      level: sentence.level,
      category: sentence.category || 'conversation',
      difficulty_score: sentence.difficulty_score || 0,
      grammar_points: sentence.grammar_points || '',
      vocabulary_used: sentence.vocabulary_used || ''
    });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja deletar esta frase?')) return;

    try {
      await api.delete(`/api/sentences/admin/${id}`);

      toast.success('Frase deletada!');
      loadSentences();
    } catch (error) {
      console.error('Erro:', error);
      toast.error('Erro ao deletar frase');
    }
  };

  const resetForm = () => {
    setEditingSentence(null);
    setFormData({
      english: '',
      portuguese: '',
      level: 'A1',
      category: 'conversation',
      difficulty_score: 0,
      grammar_points: '',
      vocabulary_used: ''
    });
    setShowForm(false);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Administração de Frases
            </h1>
            <p className="text-gray-600">Gerencie as frases do banco de dados</p>
          </div>
          <div className="flex gap-4">
            <Link
              href="/sentences"
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
            >
              <ArrowLeft className="h-5 w-5" />
              Voltar
            </Link>
            <button
              onClick={() => {
                resetForm();
                setShowForm(!showForm);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              {showForm ? <X className="h-5 w-5" /> : <Plus className="h-5 w-5" />}
              {showForm ? 'Cancelar' : 'Nova Frase'}
            </button>
          </div>
        </div>

        {/* Formulário */}
        {showForm && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
            <h2 className="text-2xl font-bold mb-6">
              {editingSentence ? 'Editar Frase' : 'Nova Frase'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Inglês */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Frase em Inglês *
                  </label>
                  <textarea
                    required
                    value={formData.english}
                    onChange={(e) => setFormData({ ...formData, english: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    placeholder="Hello, my name is John."
                  />
                </div>

                {/* Português */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tradução em Português *
                  </label>
                  <textarea
                    required
                    value={formData.portuguese}
                    onChange={(e) => setFormData({ ...formData, portuguese: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    placeholder="Olá, meu nome é John."
                  />
                </div>

                {/* Nível */}
                <div>
                  <label htmlFor="sentence-level" className="block text-sm font-medium text-gray-700 mb-2">
                    Nível
                  </label>
                  <select
                    id="sentence-level"
                    value={formData.level}
                    onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    {LEVELS.map(level => (
                      <option key={level} value={level}>{level}</option>
                    ))}
                  </select>
                </div>

                {/* Categoria */}
                <div>
                  <label htmlFor="sentence-category" className="block text-sm font-medium text-gray-700 mb-2">
                    Categoria
                  </label>
                  <select
                    id="sentence-category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  >
                    {CATEGORIES.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                {/* Dificuldade */}
                <div>
                  <label htmlFor="sentence-difficulty" className="block text-sm font-medium text-gray-700 mb-2">
                    Pontuação de Dificuldade (0-10)
                  </label>
                  <input
                    id="sentence-difficulty"
                    type="number"
                    min="0"
                    max="10"
                    step="0.1"
                    value={formData.difficulty_score}
                    onChange={(e) => setFormData({ ...formData, difficulty_score: parseFloat(e.target.value) || 0 })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                {/* Pontos Gramaticais */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Pontos Gramaticais (JSON opcional)
                  </label>
                  <textarea
                    value={formData.grammar_points}
                    onChange={(e) => setFormData({ ...formData, grammar_points: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    placeholder='{"tense": "present_simple", "structures": ["subject + verb"]}'
                  />
                </div>

                {/* Vocabulário */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Vocabulário Usado (JSON opcional)
                  </label>
                  <textarea
                    value={formData.vocabulary_used}
                    onChange={(e) => setFormData({ ...formData, vocabulary_used: e.target.value })}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    rows={2}
                    placeholder='["hello", "name", "my"]'
                  />
                </div>
              </div>

              <div className="flex gap-4 pt-4">
                <button
                  type="submit"
                  className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                >
                  <Save className="h-5 w-5" />
                  {editingSentence ? 'Atualizar' : 'Criar'} Frase
                </button>
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Lista de Frases */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <p className="text-sm text-gray-600">
                Total: <span className="font-semibold text-gray-900">{sentences.length}</span> frases
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Inglês</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Português</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nível</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Categoria</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sentences.map((sentence) => (
                    <tr key={sentence.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {sentence.id}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                        {sentence.english}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">
                        {sentence.portuguese}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          {sentence.level}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {sentence.category || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => handleEdit(sentence)}
                          className="text-primary-600 hover:text-primary-900 mr-4"
                          aria-label="Editar frase"
                          title="Editar"
                        >
                          <Edit className="h-4 w-4 inline" />
                        </button>
                        <button
                          onClick={() => handleDelete(sentence.id)}
                          className="text-red-600 hover:text-red-900"
                          aria-label="Deletar frase"
                          title="Deletar"
                        >
                          <Trash2 className="h-4 w-4 inline" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {sentences.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">Nenhuma frase cadastrada ainda</p>
                  <button
                    onClick={() => setShowForm(true)}
                    className="mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    Adicionar Primeira Frase
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
