'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { wordsApi } from '@/lib/api';
import {
  BookOpen,
  ArrowLeft,
  Search,
  Volume2,
  ChevronLeft,
  ChevronRight,
  Filter,
} from 'lucide-react';

interface Word {
  id: number;
  english: string;
  ipa: string | null;
  portuguese: string;
  level: string;
  example_en: string | null;
  example_pt: string | null;
  tags: string | null;
}

interface WordListResponse {
  words: Word[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export default function WordsPage() {
  const { user, isLoading: authLoading, fetchUser } = useAuthStore();
  const router = useRouter();

  const [words, setWords] = useState<Word[]>([]);
  const [searchInput, setSearchInput] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevel, setSelectedLevel] = useState('');
  const [levels, setLevels] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedWord, setSelectedWord] = useState<Word | null>(null);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    const loadLevels = async () => {
      try {
        const response = await wordsApi.getLevels();
        setLevels(response.data);
      } catch (error) {
        console.error('Erro ao carregar níveis:', error);
      }
    };
    loadLevels();
  }, []);

  const loadWords = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await wordsApi.getWords({
        search: searchTerm || undefined,
        level: selectedLevel || undefined,
        page: currentPage,
        per_page: 20,
      });
      const data: WordListResponse = response.data;
      setWords(data.words);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (error) {
      console.error('Erro ao carregar palavras:', error);
    } finally {
      setIsLoading(false);
    }
  }, [searchTerm, selectedLevel, currentPage]);

  useEffect(() => {
    if (user) {
      loadWords();
    }
  }, [user, loadWords]);

  // Debounced search keeps typing responsive without flooding the API.
  useEffect(() => {
    const timer = setTimeout(() => {
      const normalizedSearch = searchInput.trim();
      setCurrentPage(1);
      setSearchTerm((prev) => (prev === normalizedSearch ? prev : normalizedSearch));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const speakWord = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 0.8;
      speechSynthesis.speak(utterance);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="flex items-center gap-2 text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-5 w-5" />
            <span>Voltar</span>
          </Link>
          
          <div className="flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-primary-600" />
            <span className="font-bold text-gray-900">Vocabulário</span>
          </div>

          <div className="text-sm text-gray-500">
            {total} palavras
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        {/* Search & Filters */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search Input */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Buscar palavra em inglês ou português..."
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>

            {/* Level Filter */}
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-400" />
              <select
                value={selectedLevel}
                onChange={(e) => {
                  setSelectedLevel(e.target.value);
                  setCurrentPage(1);
                }}
                className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                aria-label="Filtrar por nível"
              >
                <option value="">Todos os níveis</option>
                {levels.map((level) => (
                  <option key={level} value={level}>
                    Nível {level}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Words List */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : words.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">Nenhuma palavra encontrada.</p>
          </div>
        ) : (
          <>
            <div className="grid gap-3">
              {words.map((word) => (
                <div
                  key={word.id}
                  onClick={() => setSelectedWord(selectedWord?.id === word.id ? null : word)}
                  className={`bg-white rounded-xl p-4 shadow-sm cursor-pointer transition hover:shadow-md ${
                    selectedWord?.id === word.id ? 'ring-2 ring-primary-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-bold text-gray-900">
                          {word.english}
                        </h3>
                        {word.ipa && (
                          <span className="text-gray-500">/{word.ipa}/</span>
                        )}
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {word.level}
                        </span>
                      </div>
                      <p className="text-gray-600 mt-1">{word.portuguese}</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        speakWord(word.english);
                      }}
                      className="p-2 hover:bg-gray-100 rounded-full transition"
                      aria-label="Ouvir pronúncia"
                    >
                      <Volume2 className="h-5 w-5 text-gray-500" />
                    </button>
                  </div>

                  {/* Expanded details */}
                  {selectedWord?.id === word.id && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      {word.example_en && (
                        <div className="mb-3">
                          <p className="text-sm text-gray-500 mb-1">Exemplo:</p>
                          <p className="text-gray-700 italic">&quot;{word.example_en}&quot;</p>
                          {word.example_pt && (
                            <p className="text-gray-500 text-sm mt-1">
                              {word.example_pt}
                            </p>
                          )}
                        </div>
                      )}
                      {word.tags && (
                        <div className="flex flex-wrap gap-2">
                          {word.tags.split(',').map((tag) => (
                            <span
                              key={tag}
                              className="px-2 py-1 bg-primary-50 text-primary-600 rounded-full text-xs"
                            >
                              {tag.trim()}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="flex justify-center items-center gap-4 mt-6">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg bg-white shadow-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Página anterior"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>

              <span className="text-gray-600">
                Página {currentPage} de {totalPages}
              </span>

              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg bg-white shadow-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Próxima página"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
