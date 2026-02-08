'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  ArrowLeft, 
  Heart,
  RefreshCw,
  Trophy,
  Star,
  Volume2
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { gamesApi } from '@/lib/api';

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

interface HangmanSessionResponse {
  session_id: string;
  word_id: number;
  display: string;
  guessed_letters: string[];
  attempts_left: number;
  max_attempts: number;
  hint: string;
  ipa: string;

  level?: string;
  word_type?: string | null;
  tags?: string[];
  definition_pt?: string | null;
  definition_en?: string | null;
  example_en?: string | null;
  example_pt?: string | null;
  usage_notes?: string | null;
  length?: number;
}

interface HangmanGuessResponse {
  correct: boolean;
  display: string;
  guessed_letters: string[];
  attempts_left: number;
  game_over: boolean;
  won: boolean;
  word?: string;
  xp_earned?: number;
}

interface HangmanGameState {
  sessionId: string;
  display: string;
  guessedLetters: string[];
  attemptsLeft: number;
  maxAttempts: number;
  hint: string;
  ipa: string;

  level?: string;
  wordType?: string | null;
  tags?: string[];
  definitionPt?: string | null;
  definitionEn?: string | null;
  exampleEn?: string | null;
  examplePt?: string | null;
  usageNotes?: string | null;
  length?: number;

  gameOver: boolean;
  won: boolean;
  word?: string;
  xpEarned?: number;
}

export default function HangmanPage() {
  const searchParams = useSearchParams();
  const level = searchParams.get('level');
  
  const [game, setGame] = useState<HangmanGameState | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLetter, setSelectedLetter] = useState<string | null>(null);

  const alphabet = ALPHABET;

  const startGame = useCallback(async () => {
    try {
      setLoading(true);
      const response = await gamesApi.startHangman(level ? { level } : undefined);
      const data: HangmanSessionResponse = response.data;
      setGame({
        sessionId: data.session_id,
        display: data.display,
        guessedLetters: data.guessed_letters,
        attemptsLeft: data.attempts_left,
        maxAttempts: data.max_attempts,
        hint: data.hint,
        ipa: data.ipa,
        level: data.level,
        wordType: data.word_type ?? null,
        tags: data.tags ?? [],
        definitionPt: data.definition_pt ?? null,
        definitionEn: data.definition_en ?? null,
        exampleEn: data.example_en ?? null,
        examplePt: data.example_pt ?? null,
        usageNotes: data.usage_notes ?? null,
        length: data.length,
        gameOver: false,
        won: false,
        word: undefined,
        xpEarned: undefined,
      });
    } catch (error) {
      console.error('Error starting game:', error);
    } finally {
      setLoading(false);
    }
  }, [level]);

  useEffect(() => {
    startGame();
  }, [startGame]);

  const guessLetter = useCallback(async (letter: string) => {
    if (!game || game.gameOver || game.guessedLetters.includes(letter.toLowerCase())) {
      return;
    }

    setSelectedLetter(letter);

    try {
      const response = await gamesApi.guessHangman(game.sessionId, { letter: letter.toLowerCase() });
      const data: HangmanGuessResponse = response.data;
      setGame((prev) =>
        prev
          ? {
              ...prev,
              display: data.display,
              guessedLetters: data.guessed_letters,
              attemptsLeft: data.attempts_left,
              gameOver: data.game_over,
              won: data.won,
              word: data.word ?? prev.word,
              xpEarned: data.xp_earned ?? prev.xpEarned,
            }
          : prev
      );
      
      if (data.game_over && data.won) {
        confetti({
          particleCount: 200,
          spread: 100,
          origin: { y: 0.6 }
        });
      }
    } catch (error) {
      console.error('Error guessing letter:', error);
    } finally {
      setSelectedLetter(null);
    }
  }, [game]);

  const speakWord = (word: string) => {
    const cleanWord = word.replace(/_/g, '');
    if (cleanWord) {
      const utterance = new SpeechSynthesisUtterance(word.replace(/_/g, ''));
      utterance.lang = 'en-US';
      speechSynthesis.speak(utterance);
    }
  };

  // Teclas do teclado
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const letter = e.key.toUpperCase();
      if (alphabet.includes(letter)) {
        guessLetter(letter);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [alphabet, guessLetter]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-16 h-16 border-4 border-red-500 border-t-transparent rounded-full mx-auto mb-4"></div>
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

  const isGameOver = game.gameOver;

  const answerWord = (game.word || game.display.replace(/\s/g, '')).toLowerCase();
  const firstLetter = answerWord && answerWord !== '_' ? answerWord[0]?.toUpperCase() : '';
  const lastLetter = answerWord && answerWord !== '_' ? answerWord[answerWord.length - 1]?.toUpperCase() : '';
  const length = game.length ?? answerWord.replace(/_/g, '').length;

  const extraHints: Array<{ title: string; value: string }> = [];
  // Dicas progressivas: quanto menos tentativas, mais contexto.
  // 6 = só o básico; 5..1 vai liberando.
  if (game.attemptsLeft <= 5 && firstLetter) {
    extraHints.push({ title: 'Primeira letra', value: firstLetter });
  }
  if (game.attemptsLeft <= 4 && lastLetter) {
    extraHints.push({ title: 'Última letra', value: lastLetter });
  }
  if (game.attemptsLeft <= 3) {
    const def = game.definitionPt || game.definitionEn;
    if (def) extraHints.push({ title: 'Definição', value: def });
  }
  if (game.attemptsLeft <= 2) {
    const ex = game.exampleEn || game.examplePt;
    if (ex) extraHints.push({ title: 'Exemplo', value: ex });
  }
  if (game.attemptsLeft <= 1 && game.usageNotes) {
    extraHints.push({ title: 'Uso / contexto', value: game.usageNotes });
  }

  const moodLine = (() => {
    if (game.won) return 'Mandou bem! Quer aumentar a sequência?';
    if (game.gameOver && !game.won) return 'Sem estresse — essa era pegadinha. Bora outra?';
    if (game.attemptsLeft >= 5) return 'Começou bem. Vai no feeling!';
    if (game.attemptsLeft >= 3) return 'A corda está apertando… mas dá pra virar!';
    return 'Agora é modo sobrevivência. Use as dicas!';
  })();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-800/50 backdrop-blur-md border-b border-gray-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/games" className="text-gray-400 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          
          <h1 className="text-xl font-bold text-white">Jogo da Forca</h1>
          
          {/* Vidas */}
          <div className="flex items-center gap-1">
            {[...Array(game.maxAttempts)].map((_, i) => (
              <Heart
                key={i}
                className={`w-5 h-5 ${
                  i < game.attemptsLeft
                    ? 'text-red-500 fill-red-500'
                    : 'text-gray-600'
                }`}
              />
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        {/* Boneco da Forca */}
        <div className="flex justify-center mb-8">
          <svg viewBox="0 0 200 200" className="w-48 h-48">
            {/* Estrutura */}
            <line x1="20" y1="180" x2="100" y2="180" stroke="#4B5563" strokeWidth="4" />
            <line x1="60" y1="180" x2="60" y2="20" stroke="#4B5563" strokeWidth="4" />
            <line x1="60" y1="20" x2="140" y2="20" stroke="#4B5563" strokeWidth="4" />
            <line x1="140" y1="20" x2="140" y2="40" stroke="#4B5563" strokeWidth="4" />
            
            {/* Partes do corpo */}
            {/* Cabeça */}
            {game.attemptsLeft < 6 && (
              <circle cx="140" cy="55" r="15" stroke="#EF4444" strokeWidth="3" fill="none" />
            )}
            {/* Corpo */}
            {game.attemptsLeft < 5 && (
              <line x1="140" y1="70" x2="140" y2="120" stroke="#EF4444" strokeWidth="3" />
            )}
            {/* Braço esquerdo */}
            {game.attemptsLeft < 4 && (
              <line x1="140" y1="80" x2="115" y2="100" stroke="#EF4444" strokeWidth="3" />
            )}
            {/* Braço direito */}
            {game.attemptsLeft < 3 && (
              <line x1="140" y1="80" x2="165" y2="100" stroke="#EF4444" strokeWidth="3" />
            )}
            {/* Perna esquerda */}
            {game.attemptsLeft < 2 && (
              <line x1="140" y1="120" x2="115" y2="155" stroke="#EF4444" strokeWidth="3" />
            )}
            {/* Perna direita */}
            {game.attemptsLeft < 1 && (
              <line x1="140" y1="120" x2="165" y2="155" stroke="#EF4444" strokeWidth="3" />
            )}
          </svg>
        </div>

        {/* Palavra */}
        <div className="flex justify-center mb-4">
          <button
            onClick={() => speakWord(game.word || game.display)}
            className="flex items-center gap-2 group"
          >
            <div className="flex gap-2">
              {game.display.split(' ').map((char, i) => (
                <motion.span
                  key={i}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: i * 0.05 }}
                  className={`w-10 h-12 flex items-center justify-center text-2xl font-bold border-b-4 ${
                    char === '_'
                      ? 'border-gray-600 text-gray-600'
                      : 'border-green-500 text-white'
                  }`}
                >
                  {char === '_' ? '' : char.toUpperCase()}
                </motion.span>
              ))}
            </div>
            <Volume2 className="w-5 h-5 text-gray-400 group-hover:text-indigo-400 transition" />
          </button>
        </div>

        {/* Dica */}
        <div className="mb-8">
          <div className="text-center mb-3">
            <p className="text-gray-400">
              <span className="text-gray-500">Dica principal:</span> {game.hint}
            </p>
            <p className="text-gray-500 text-sm mt-1">{moodLine}</p>
          </div>

          <div className="bg-gray-800/40 border border-gray-700 rounded-2xl p-4">
            <div className="flex flex-wrap items-center justify-center gap-2">
              <span className="text-xs px-2 py-1 rounded-full bg-gray-700/60 text-gray-200">
                {length} letras
              </span>
              {game.level && (
                <span className="text-xs px-2 py-1 rounded-full bg-gray-700/60 text-gray-200">
                  Nível {game.level}
                </span>
              )}
              {game.wordType && (
                <span className="text-xs px-2 py-1 rounded-full bg-gray-700/60 text-gray-200">
                  {game.wordType}
                </span>
              )}
              {(game.tags || []).slice(0, 3).map((t) => (
                <span key={t} className="text-xs px-2 py-1 rounded-full bg-gray-700/60 text-gray-400">
                  #{t}
                </span>
              ))}
            </div>

            {extraHints.length > 0 && (
              <div className="mt-4">
                <p className="text-center text-sm text-gray-400 mb-2">
                  Dicas desbloqueadas ({extraHints.length})
                </p>
                <div className="space-y-2">
                  {extraHints.map((h) => (
                    <motion.div
                      key={h.title}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-gray-900/30 border border-gray-700 rounded-xl p-3"
                    >
                      <div className="text-xs text-gray-500 mb-1">{h.title}</div>
                      <div className="text-gray-200 text-sm whitespace-pre-wrap">{h.value}</div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Teclado */}
        {!isGameOver && (
          <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto">
            {alphabet.map((letter) => {
              const normalizedWord = (game.word || game.display.replace(/\s/g, '')).toLowerCase();
              const isGuessed = game.guessedLetters.includes(letter.toLowerCase());
              const isInWord = normalizedWord.includes(letter.toLowerCase());
              
              return (
                <motion.button
                  key={letter}
                  whileHover={!isGuessed ? { scale: 1.1 } : {}}
                  whileTap={!isGuessed ? { scale: 0.95 } : {}}
                  onClick={() => guessLetter(letter)}
                  disabled={isGuessed || selectedLetter === letter}
                  className={`w-10 h-10 rounded-lg font-bold text-lg transition ${
                    isGuessed
                      ? isInWord
                        ? 'bg-green-500/20 text-green-400 border border-green-500'
                        : 'bg-gray-700/50 text-gray-500 border border-gray-600'
                      : 'bg-gray-700 text-white hover:bg-gray-600 border border-gray-600'
                  }`}
                >
                  {letter}
                </motion.button>
              );
            })}
          </div>
        )}

        {/* Resultado */}
        <AnimatePresence>
          {isGameOver && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8"
            >
              <div className={`rounded-2xl p-6 text-center ${
                game.won
                  ? 'bg-green-500/20 border border-green-500/30'
                  : 'bg-red-500/20 border border-red-500/30'
              }`}>
                <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4 ${
                  game.won ? 'bg-green-500/20' : 'bg-red-500/20'
                }`}>
                  <Trophy className={`w-8 h-8 ${
                    game.won ? 'text-green-400' : 'text-red-400'
                  }`} />
                </div>

                <h2 className={`text-2xl font-bold mb-2 ${
                  game.won ? 'text-green-400' : 'text-red-400'
                }`}>
                  {game.won ? 'Você Venceu!' : 'Você Perdeu!'}
                </h2>

                <p className="text-white text-xl font-bold mb-2">
                  A palavra era: {game.word?.toUpperCase()}
                </p>

                {game.xpEarned !== undefined && game.xpEarned > 0 && (
                  <div className="flex items-center justify-center gap-2 text-yellow-400 mb-4">
                    <Star className="w-5 h-5" />
                    <span className="font-bold">+{game.xpEarned} XP</span>
                  </div>
                )}

                <div className="flex gap-3 justify-center mt-4">
                  <Link
                    href="/games"
                    className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition"
                  >
                    Voltar
                  </Link>
                  <button
                    onClick={startGame}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium transition flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Jogar Novamente
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
