'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { videosApi } from '@/lib/api';
import Link from 'next/link';

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
  user_progress?: number;
  is_completed?: boolean;
  created_at: string;
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

export default function VideoPlayerPage() {
  const params = useParams();
  const router = useRouter();
  const [video, setVideo] = useState<Video | null>(null);
  const [loading, setLoading] = useState(true);
  const watchedSecondsRef = useRef(0);
  const progressInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const updateProgress = useCallback(async (videoId: number, seconds: number, duration: number) => {
    if (!duration) return;

    const percentage = Math.min(100, Math.round((seconds / duration) * 100));

    try {
      await videosApi.updateProgress({
        video_id: videoId,
        watched_duration: seconds,
        completion_percentage: percentage,
      });
    } catch (error) {
      console.error('Erro ao atualizar progresso:', error);
    }
  }, []);

  const startProgressTracking = useCallback((videoId: number, duration: number) => {
    if (progressInterval.current) {
      clearInterval(progressInterval.current);
    }

    watchedSecondsRef.current = 0;
    // Atualizar progresso a cada 5 segundos
    progressInterval.current = setInterval(() => {
      watchedSecondsRef.current += 5;
      void updateProgress(videoId, watchedSecondsRef.current, duration);
    }, 5000);
  }, [updateProgress]);

  const loadVideo = useCallback(async (id: number) => {
    setLoading(true);
    try {
      const response = await videosApi.getVideo(id);
      const loadedVideo: Video = response.data;
      setVideo(loadedVideo);

      // Iniciar rastreamento de progresso
      startProgressTracking(loadedVideo.id, loadedVideo.duration);
    } catch (error) {
      console.error('Erro ao carregar vídeo:', error);
    } finally {
      setLoading(false);
    }
  }, [startProgressTracking]);

  useEffect(() => {
    if (params.id) {
      void loadVideo(Number(params.id));
    }

    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, [loadVideo, params.id]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Vídeo não encontrado
          </h2>
          <button
            onClick={() => router.push('/videos')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Voltar para vídeos
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <Link
          href="/dashboard"
          className="mb-2 inline-flex items-center text-gray-600 hover:text-gray-900"
        >
          <svg
            className="w-5 h-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Voltar ao Dashboard
        </Link>
        {/* Botão voltar */}
        <button
          onClick={() => router.push('/videos')}
          className="mb-4 flex items-center text-gray-600 hover:text-gray-900"
        >
          <svg
            className="w-5 h-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Voltar para vídeos
        </button>

        {/* Player */}
        <div className="bg-white rounded-lg shadow-lg overflow-hidden mb-8">
          <div className="relative aspect-video bg-black">
            <iframe
              src={`https://www.youtube.com/embed/${video.youtube_id}?autoplay=0&rel=0`}
              title={video.title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="absolute top-0 left-0 w-full h-full"
            />
          </div>

          {/* Progresso */}
          {video.user_progress !== undefined && video.user_progress > 0 && (
            <div className="px-6 py-2 bg-gray-50 border-b">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">
                  Progresso: {video.user_progress}%
                </span>
                {video.is_completed && (
                  <span className="text-sm text-green-600 font-medium">
                    ✓ Concluído
                  </span>
                )}
              </div>
              <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 transition-all duration-300"
                  style={{ width: `${video.user_progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Informações */}
          <div className="p-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              {video.title}
            </h1>

            {/* Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">
                {video.level}
              </span>
              <span className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm font-medium">
                {CATEGORIES[video.category as keyof typeof CATEGORIES]}
              </span>
              {video.tags && video.tags.split(',').map((tag, index) => (
                <span
                  key={index}
                  className="bg-gray-100 text-gray-700 px-3 py-1 rounded-full text-sm"
                >
                  {tag.trim()}
                </span>
              ))}
            </div>

            {/* Estatísticas */}
            <div className="flex items-center space-x-6 text-sm text-gray-600 mb-6">
              <div className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
                {video.views_count} visualizações
              </div>
              <div className="flex items-center">
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                {formatDate(video.created_at)}
              </div>
            </div>

            {/* Descrição */}
            {video.description && (
              <div className="border-t pt-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-3">
                  Sobre este vídeo
                </h2>
                <p className="text-gray-700 whitespace-pre-wrap">
                  {video.description}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Ações */}
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => router.push('/videos')}
            className="px-6 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium"
          >
            Ver mais vídeos
          </button>
          <button
            onClick={() => window.open(video.youtube_url, '_blank')}
            className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium flex items-center"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
            </svg>
            Assistir no YouTube
          </button>
        </div>
      </div>
    </div>
  );
}
