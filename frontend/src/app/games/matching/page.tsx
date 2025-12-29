
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  ArrowLeft, 
  RefreshCw,
  Trophy,
  Star,
  Clock,
  CheckCircle
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { gamesApi } from '@/lib/api';

function shuffleInPlace<T>(arr: T[]): T[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

interface MatchingCardResponse {
  id: string;
  content: string;
  type: 'english' | 'portuguese';
  pair_id: number;
}

interface MatchingCard extends MatchingCardResponse {
  matched: boolean;
}

interface MatchingSession {
  session_id: string;
  total_pairs: number;
  due_pairs?: number;
  new_pairs?: number;
  review_ratio?: number;
}

interface MatchingResult {
  score: number;
  time_spent: number;
  moves: number;
  xp_earned: number;
  is_best_time: boolean;
}

type MatchExample = {
  word_en: string;
  word_pt: string;
  sentence_en: string;
  sentence_pt: string;
};

function buildExample(wordEn: string, wordPt: string): MatchExample {
  // Frase simples, sempre correta e com tradução direta.
  const safeEn = wordEn.trim();
  const safePt = wordPt.trim();
  return {
    word_en: safeEn,
    word_pt: safePt,
    sentence_en: `The word "${safeEn}" means "${safePt}".`,
    sentence_pt: `A palavra "${safeEn}" significa "${safePt}".`,
  };
}

export default function MatchingPage() {
  const searchParams = useSearchParams();
  const level = searchParams.get('level');
  
  const [game, setGame] = useState<MatchingSession | null>(null);
  const [cards, setCards] = useState<MatchingCard[]>([]);
  const [selectedCards, setSelectedCards] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<MatchingResult | null>(null);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [isChecking, setIsChecking] = useState(false);
  const [moves, setMoves] = useState(0);
  const [wrongCards, setWrongCards] = useState<string[]>([]);
  const [lastExample, setLastExample] = useState<MatchExample | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitOnceRef = useRef(false);
  const selectedCardsRef = useRef<string[]>([]);
  const movesRef = useRef(0);

  const submitGame = useCallback(async (completed = true, movesOverride?: number) => {
    if (!game) return;
    if (submitOnceRef.current) return;

    submitOnceRef.current = true;
    setIsSubmitting(true);
    try {
      const response = await gamesApi.submitMatching({
        session_id: game.session_id,
        time_spent: timeElapsed,
        moves: movesOverride ?? moves,
        completed,
      });
      const data: MatchingResult = response.data;
      setResult(data);

      confetti({
        particleCount: 200,
        spread: 100,
        origin: { y: 0.6 }
      });
    } catch (error) {
      // Se falhar, libera para tentar de novo (sem travar a UI no “estático”).
      submitOnceRef.current = false;
      console.error('Error submitting game:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [game, timeElapsed, moves]);

  const startGame = useCallback(async () => {
    try {
      setLoading(true);
      setResult(null);
      setSelectedCards([]);
      setWrongCards([]);
      setLastExample(null);
      setTimeElapsed(0);
      setMoves(0);
      setIsSubmitting(false);
      submitOnceRef.current = false;
      selectedCardsRef.current = [];
      movesRef.current = 0;

      const normalize = (text: string) => text.replace(/\u00A0/g, ' ').trim().replace(/\s+/g, ' ').toLowerCase();
      const hasDuplicates = (items: MatchingCardResponse[]) => {
        const en = new Set<string>();
        const pt = new Set<string>();
        for (const c of items) {
          const key = normalize(c.content);
          if (!key) return true;
          if (c.type === 'english') {
            if (en.has(key)) return true;
            en.add(key);
          } else {
            if (pt.has(key)) return true;
            pt.add(key);
          }
        }
        return false;
      };

      const maxRetries = 2;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        const response = await gamesApi.startMatching({
          num_pairs: 6,
          level: level ?? undefined,
        });
        const data = response.data as {
          session_id: string;
          cards: MatchingCardResponse[];
          total_pairs: number;
          due_pairs?: number;
          new_pairs?: number;
          review_ratio?: number;
        };
        if (hasDuplicates(data.cards) && attempt < maxRetries) {
          continue;
        }

        setGame({
          session_id: data.session_id,
          total_pairs: data.total_pairs,
          due_pairs: data.due_pairs,
          new_pairs: data.new_pairs,
          review_ratio: data.review_ratio,
        });
        setCards(
          shuffleInPlace(
            data.cards
              .map((card) => ({
                ...card,
                matched: false,
              }))
              .slice()
          )
        );
        break;
      }
    } catch (error) {
      console.error('Error starting game:', error);
    } finally {
      setLoading(false);
    }
  }, [level]);

  useEffect(() => {
    startGame();
  }, [startGame]);

  useEffect(() => {
    selectedCardsRef.current = selectedCards;
  }, [selectedCards]);

  useEffect(() => {
    movesRef.current = moves;
  }, [moves]);

  // Timer
  useEffect(() => {
    if (!game || result) return;

    const interval = setInterval(() => {
      setTimeElapsed(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [game, result]);

  // Finalização confiável: quando todas as cartas estiverem marcadas, submete.
  useEffect(() => {
    if (!game) return;
    if (result) return;
    if (isSubmitting) return;
    if (cards.length === 0) return;
    if (!cards.every((c) => c.matched)) return;

    submitGame(true);
  }, [cards, game, isSubmitting, result, submitGame]);

  const handleCardClick = (cardId: string) => {
    if (isChecking || result) return;
    
    const card = cards.find((c) => c.id === cardId);
    if (!card || card.matched || selectedCards.includes(cardId)) return;

    // Mantém seleção consistente mesmo com cliques rápidos (evita estado stale).
    const prevSelected = selectedCardsRef.current;
    if (prevSelected.includes(cardId)) return;
    const newSelected = [...prevSelected, cardId];
    selectedCardsRef.current = newSelected;
    setSelectedCards(newSelected);
    setWrongCards([]);

    if (newSelected.length === 2) {
      setIsChecking(true);

      const nextMoves = movesRef.current + 1;
      movesRef.current = nextMoves;
      setMoves(nextMoves);

      const [firstId, secondId] = newSelected;
      const firstCard = cards.find((c) => c.id === firstId);
      const secondCard = cards.find((c) => c.id === secondId);
      if (!firstCard || !secondCard) {
        setSelectedCards([]);
        setIsChecking(false);
        return;
      }

      const isMatch = firstCard.pair_id === secondCard.pair_id && firstCard.type !== secondCard.type;

      setTimeout(() => {
        if (isMatch) {
          const en = firstCard.type === 'english' ? firstCard.content : secondCard.content;
          const pt = firstCard.type === 'portuguese' ? firstCard.content : secondCard.content;
          setLastExample(buildExample(en, pt));

          confetti({
            particleCount: 30,
            spread: 40,
            origin: { y: 0.7 }
          });
          setCards((prevCards) => {
            return prevCards.map((c) =>
              c.pair_id === firstCard.pair_id ? { ...c, matched: true } : c
            );
          });
        } else {
          setWrongCards([firstId, secondId]);
        }
        setSelectedCards([]);
        selectedCardsRef.current = [];
        setIsChecking(false);
      }, 500);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-16 h-16 border-4 border-green-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-300">Preparando jogo...</p>
        </div>
      </div>
    );
  }

  if (!game) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-300 mb-4">Não foi possível carregar o jogo.</p>
          <Link href="/games" className="text-indigo-400 hover:text-indigo-300">
            Voltar aos jogos
          </Link>
        </div>
      </div>
    );
  }

  const matchedCount = cards.filter(c => c.matched).length / 2;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/games" aria-label="Voltar para a lista de jogos" className="text-gray-400 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          
          <h1 className="text-xl font-bold text-white">Combinar Palavras</h1>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-gray-400">
              <Clock className="w-4 h-4" />
              <span className="font-mono">{formatTime(timeElapsed)}</span>
            </div>
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle className="w-4 h-4" />
              <span>{matchedCount}/{game.total_pairs}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Instruções */}
        <p className="text-center text-gray-400 mb-2">
          Encontre os pares combinando palavras em inglês com suas traduções
        </p>
        {typeof game.due_pairs === 'number' && typeof game.new_pairs === 'number' && (
          <p className="text-center text-gray-500 mb-6">
            Modo estudo: revisão {game.due_pairs} / novas {game.new_pairs}
          </p>
        )}

        {/* Grid de cartas */}
        <div className="grid grid-cols-3 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
          {cards.map((card) => {
            const isSelected = selectedCards.includes(card.id);
            const isMatched = card.matched;
            const isWrong = wrongCards.includes(card.id);
            
            return (
              <motion.button
                key={card.id}
                whileHover={!isMatched ? { scale: 1.05 } : {}}
                whileTap={!isMatched ? { scale: 0.95 } : {}}
                onClick={() => handleCardClick(card.id)}
                type="button"
                aria-label={`Carta ${card.type === 'english' ? 'Inglês' : 'Português'}: ${card.content}`}
                disabled={isMatched || isChecking}
                  className={`aspect-square rounded-xl p-3 font-medium text-center flex items-center justify-center transition-all ${
                    isMatched
                      ? 'bg-green-500/20 border-2 border-green-500 text-green-400'
                      : isWrong
                      ? 'bg-red-500/20 border-2 border-red-500 text-red-300'
                      : isSelected
                      ? 'bg-indigo-500/30 border-2 border-indigo-500 text-white'
                      : `bg-gray-800 border-2 text-white ${
                          card.type === 'english'
                            ? 'border-blue-500/40 hover:border-blue-400/60'
                            : 'border-purple-500/40 hover:border-purple-400/60'
                        }`
                  }`}
                >
                <span className={`text-sm md:text-base ${isMatched ? 'line-through opacity-50' : ''}`}>
                  {card.content}
                </span>
              </motion.button>
            );
          })}
        </div>

        {/* Legenda */}
        <div className="flex justify-center gap-6 mt-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-500/30 border border-blue-500"></div>
            <span className="text-gray-400">Inglês</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-purple-500/30 border border-purple-500"></div>
            <span className="text-gray-400">Português</span>
          </div>
        </div>

        {/* Exemplo após acerto */}
        {lastExample && !result && (
          <div className="max-w-2xl mx-auto mt-6 bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <p className="text-gray-400 text-sm mb-2">Exemplo</p>
            <p className="text-white font-medium">{lastExample.sentence_en}</p>
            <p className="text-gray-300">{lastExample.sentence_pt}</p>
          </div>
        )}

        {/* Finalizando (evita sensação de travamento) */}
        {!result && isSubmitting && (
          <div className="max-w-2xl mx-auto mt-6 text-center text-gray-400">
            Finalizando resultado...
          </div>
        )}

        {/* Resultado */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8"
          >
            <div className="bg-green-500/20 border border-green-500/30 rounded-2xl p-6 text-center">
              <div className="w-16 h-16 mx-auto rounded-full bg-green-500/20 flex items-center justify-center mb-4">
                <Trophy className="w-8 h-8 text-green-400" />
              </div>

              <h2 className="text-2xl font-bold text-green-400 mb-2">
                Parabéns!
              </h2>

              <p className="text-gray-300 mb-4">
                Você encontrou todos os pares em {formatTime(result.time_spent)}!
              </p>
              <p className="text-gray-400 mb-4">Movimentos: {result.moves}</p>
              {result.is_best_time && (
                <p className="text-green-400 font-semibold mb-4">Novo recorde de tempo!</p>
              )}

              <div className="flex items-center justify-center gap-2 text-yellow-400 mb-6">
                <Star className="w-6 h-6" />
                <span className="text-2xl font-bold">+{result.xp_earned} XP</span>
              </div>

              <div className="flex gap-3 justify-center">
                <Link
                  href="/games"
                  className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition"
                >
                  Voltar
                </Link>
                <button
                  onClick={startGame}
                  type="button"
                  className="px-6 py-3 bg-green-600 hover:bg-green-500 text-white rounded-xl font-medium transition flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Jogar Novamente
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
