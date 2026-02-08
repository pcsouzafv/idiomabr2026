"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
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

interface User {
  id: number;
  name: string;
  email: string;
  phone_number?: string | null;
  is_active: boolean;
  is_admin: boolean;
  current_streak: number;
  daily_goal: number;
  created_at: string;
}

interface CreateUserPayload {
  name: string;
  email: string;
  phone_number: string;
  password: string;
  is_active: boolean;
  is_admin: boolean;
  daily_goal?: number;
}

interface UserEditPayload extends Partial<User> {
  password?: string;
}

export default function AdminUsersPage() {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      const searchParam = search ? `&search=${search}` : "";
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/users?page=${page}&per_page=50${searchParam}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setUsers(response.data.items || []);
      setTotalPages(response.data.pages || 1);
    } catch (error) {
      console.error("Erro ao carregar usuários:", error);
    } finally {
      setLoading(false);
    }
  }, [page, search, token]);

  useEffect(() => {
    if (!user?.is_admin) {
      router.push("/dashboard");
      return;
    }
    void loadUsers();
  }, [user, router, loadUsers]);

  const handleSearch = () => {
    setPage(1);
    setSearch(searchInput.trim());
  };

  const toggleAdmin = async (userId: number, currentIsAdmin: boolean) => {
    const action = currentIsAdmin ? "revogar" : "conceder";
    if (!confirm(`Tem certeza que deseja ${action} privilégios de admin para este usuário?`)) return;

    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${userId}`,
        { is_admin: !currentIsAdmin },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadUsers();
    } catch (error) {
      console.error("Erro ao alterar permissão:", error);
      alert("Erro ao alterar permissão de admin");
    }
  };

  const toggleActive = async (userId: number, currentIsActive: boolean) => {
    const action = currentIsActive ? "desativar" : "ativar";
    if (!confirm(`Tem certeza que deseja ${action} este usuário?`)) return;

    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${userId}`,
        { is_active: !currentIsActive },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadUsers();
    } catch (error) {
      console.error("Erro ao alterar status:", error);
      alert("Erro ao alterar status do usuário");
    }
  };

  const handleDelete = async (userId: number) => {
    if (userId === user?.id) {
      alert("Você não pode deletar sua própria conta!");
      return;
    }

    if (!confirm("Tem certeza que deseja deletar este usuário? Esta ação não pode ser desfeita!")) return;

    try {
      await axios.delete(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${userId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadUsers();
    } catch (error) {
      console.error("Erro ao deletar usuário:", error);
      alert("Erro ao deletar usuário");
    }
  };

  const handleSaveUser = async (userData: UserEditPayload) => {
    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/users/${editingUser?.id}`,
        userData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert("Usuário atualizado com sucesso!");
      setShowModal(false);
      setEditingUser(null);
      loadUsers();
    } catch (error: unknown) {
      console.error("Erro ao salvar usuário:", error);
      alert(getErrorDetail(error) || "Erro ao salvar usuário");
    }
  };

  const handleCreateUser = async (payload: CreateUserPayload) => {
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/admin/users`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert("Usuário criado com sucesso!");
      setShowCreateModal(false);
      loadUsers();
    } catch (error: unknown) {
      console.error("Erro ao criar usuário:", error);
      alert(getErrorDetail(error) || "Erro ao criar usuário");
    }
  };

  if (!user?.is_admin) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start gap-4">
            <div>
              <Link href="/admin" className="text-purple-600 hover:text-purple-700 mb-2 inline-block">
                ← Voltar ao Painel Admin
              </Link>
              <h1 className="text-4xl font-bold text-gray-800">Gerenciar Usuários</h1>
              <p className="text-gray-600 mt-2">Visualize, edite permissões e gerencie usuários do sistema</p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition-colors font-semibold"
            >
              ➕ Novo Usuário
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Buscar por nome ou email..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
            <button
              onClick={handleSearch}
              className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors font-semibold"
            >
              🔍 Buscar
            </button>
            {search && (
              <button
                onClick={() => {
                  setSearchInput("");
                  setSearch("");
                  setPage(1);
                }}
                className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Limpar
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          {loading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
              <p className="text-gray-600 mt-4">Carregando usuários...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600 text-lg">Nenhum usuário encontrado</p>
            </div>
          ) : (
            <>
              <div className="mb-4 text-sm text-gray-600">
                Total: {users.length} usuários (Página {page} de {totalPages})
              </div>

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">ID</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Nome</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Email</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700">Telefone</th>
                      <th className="text-center py-3 px-4 font-semibold text-gray-700">Streak</th>
                      <th className="text-center py-3 px-4 font-semibold text-gray-700">Meta</th>
                      <th className="text-center py-3 px-4 font-semibold text-gray-700">Status</th>
                      <th className="text-center py-3 px-4 font-semibold text-gray-700">Admin</th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-700">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-gray-600">{u.id}</td>
                        <td className="py-3 px-4">
                          <div className="font-medium text-gray-800">{u.name}</div>
                          {u.id === user?.id && (
                            <span className="text-xs text-purple-600 font-semibold">(Você)</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-gray-600">{u.email}</td>
                        <td className="py-3 px-4 text-gray-600">{u.phone_number || '—'}</td>
                        <td className="py-3 px-4 text-center">
                          <span className="font-bold text-orange-600">🔥 {u.current_streak}</span>
                        </td>
                        <td className="py-3 px-4 text-center text-gray-600">{u.daily_goal}</td>
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => toggleActive(u.id, u.is_active)}
                            className={`px-3 py-1 rounded-full text-xs font-semibold ${
                              u.is_active
                                ? "bg-green-100 text-green-700 hover:bg-green-200"
                                : "bg-red-100 text-red-700 hover:bg-red-200"
                            }`}
                          >
                            {u.is_active ? "✅ Ativo" : "❌ Inativo"}
                          </button>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <button
                            onClick={() => toggleAdmin(u.id, u.is_admin)}
                            disabled={u.id === user?.id}
                            className={`px-3 py-1 rounded-full text-xs font-semibold ${
                              u.is_admin
                                ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                            } disabled:opacity-50 disabled:cursor-not-allowed`}
                          >
                            {u.is_admin ? "👑 Admin" : "👤 User"}
                          </button>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setEditingUser(u);
                              setShowModal(true);
                            }}
                            className="text-blue-600 hover:text-blue-700 font-semibold mr-3"
                          >
                            Editar
                          </button>
                          <button
                            onClick={() => handleDelete(u.id)}
                            disabled={u.id === user?.id}
                            className="text-red-600 hover:text-red-700 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
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

      {showModal && editingUser && (
        <UserEditModal user={editingUser} onClose={() => { setShowModal(false); setEditingUser(null); }} onSave={handleSaveUser} />
      )}

      {showCreateModal && (
        <UserCreateModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateUser}
        />
      )}
    </div>
  );
}

function UserCreateModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (payload: CreateUserPayload) => void;
}) {
  const [formData, setFormData] = useState<CreateUserPayload>({
    name: "",
    email: "",
    phone_number: "",
    password: "",
    is_active: true,
    is_admin: false,
    daily_goal: 20,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6">Novo Usuário</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Nome *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                title="Nome"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Email *</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                title="Email"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Telefone *</label>
              <input
                type="tel"
                required
                value={formData.phone_number}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                title="Telefone"
                placeholder="+55 11 99999-9999"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Senha *</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                title="Senha"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Meta Diária</label>
              <input
                type="number"
                min="1"
                max="100"
                value={formData.daily_goal ?? 20}
                onChange={(e) => setFormData({ ...formData, daily_goal: parseInt(e.target.value) })}
                title="Meta Diária"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-xs text-gray-500 mt-1">Número de palavras para estudar por dia</p>
            </div>

            <div className="flex gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  title="Conta Ativa"
                  className="w-4 h-4"
                />
                <span className="text-sm font-semibold text-gray-700">Conta Ativa</span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_admin}
                  onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                  title="Admin"
                  className="w-4 h-4"
                />
                <span className="text-sm font-semibold text-gray-700">Admin</span>
              </label>
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
                Criar Usuário
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function UserEditModal({ user, onClose, onSave }: { user: User; onClose: () => void; onSave: (user: UserEditPayload) => void; }) {
  const [formData, setFormData] = useState<UserEditPayload>({
    name: user.name,
    email: user.email,
    phone_number: user.phone_number ?? '',
    daily_goal: user.daily_goal,
    is_active: user.is_active,
    is_admin: user.is_admin,
    password: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = { ...formData };
    if (!payload.password) {
      delete payload.password;
    }
    onSave(payload);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6">Editar Usuário</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Nome *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                title="Nome"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Email *</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                title="Email"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Telefone</label>
              <input
                type="tel"
                value={formData.phone_number ?? ''}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                title="Telefone"
                placeholder="+55 11 99999-9999"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Meta Diária</label>
              <input
                type="number"
                min="1"
                max="100"
                value={formData.daily_goal}
                onChange={(e) => setFormData({ ...formData, daily_goal: parseInt(e.target.value) })}
                title="Meta Diária"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-xs text-gray-500 mt-1">Número de palavras para estudar por dia</p>
            </div>

            <div className="flex gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  title="Conta Ativa"
                  className="w-4 h-4"
                />
                <span className="text-sm font-semibold text-gray-700">Conta Ativa</span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_admin}
                  onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                  title="Admin"
                  className="w-4 h-4"
                />
                <span className="text-sm font-semibold text-gray-700">Admin</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Nova Senha (opcional)</label>
              <input
                type="password"
                value={formData.password ?? ''}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                title="Nova Senha"
                placeholder="Minimo 6 caracteres"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="bg-gray-50 rounded-lg p-4 mt-6">
              <h3 className="font-semibold text-gray-700 mb-2">Informações do Usuário</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">ID:</span> <span className="font-medium">{user.id}</span>
                </div>
                <div>
                  <span className="text-gray-500">Streak Atual:</span> <span className="font-medium text-orange-600">🔥 {user.current_streak} dias</span>
                </div>
                <div className="col-span-2">
                  <span className="text-gray-500">Criado em:</span> <span className="font-medium">{new Date(user.created_at).toLocaleDateString('pt-BR')}</span>
                </div>
              </div>
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
                Salvar Alterações
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
