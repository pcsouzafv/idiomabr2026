"""
Schemas para sistema de gamificação.
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ============== XP e Stats ==============

class UserStatsBase(BaseModel):
    total_xp: int = 0
    level: int = 1
    words_learned: int = 0
    words_mastered: int = 0
    total_reviews: int = 0
    correct_answers: int = 0
    games_played: int = 0
    games_won: int = 0
    longest_streak: int = 0


class UserStatsResponse(UserStatsBase):
    id: int
    user_id: int
    best_quiz_score: int = 0
    best_hangman_streak: int = 0
    best_matching_time: Optional[int] = None
    perfect_games: int = 0
    xp_to_next_level: int = 0
    level_progress: float = 0.0
    
    class Config:
        from_attributes = True


# ============== Conquistas ==============

class AchievementBase(BaseModel):
    name: str
    description: str
    icon: str = "🏆"
    type: str = "words"
    requirement: int = 1
    xp_reward: int = 50


class AchievementResponse(AchievementBase):
    id: int
    
    class Config:
        from_attributes = True


class UserAchievementResponse(BaseModel):
    achievement: AchievementResponse
    unlocked_at: datetime
    
    class Config:
        from_attributes = True


# ============== Jogos ==============

class GameSessionCreate(BaseModel):
    game_type: str
    score: int
    max_score: int
    time_spent: int = 0
    level_filter: Optional[str] = None
    completed: bool = True


class GameSessionResponse(BaseModel):
    id: int
    game_type: str
    score: int
    max_score: int
    time_spent: int
    xp_earned: int
    played_at: datetime
    
    class Config:
        from_attributes = True


# ============== Quiz ==============

class QuizQuestion(BaseModel):
    word_id: int
    english: str
    ipa: str
    correct_answer: str
    options: List[str]


class QuizSessionRequest(BaseModel):
    level: Optional[str] = None
    count: int = 10


class QuizSessionResponse(BaseModel):
    session_id: str
    questions: List[QuizQuestion]
    total: int


class QuizAnswerRequest(BaseModel):
    word_id: int
    answer: str


class QuizResultRequest(BaseModel):
    session_id: str
    answers: List[int]  # Índices das respostas escolhidas
    time_spent: int = 0


class QuizResultResponse(BaseModel):
    score: int
    total: int
    percentage: float
    xp_earned: int
    correct_words: List[str]
    incorrect_words: List[dict]
    new_achievements: List[AchievementResponse] = []


# ============== Hangman ==============

class HangmanStartRequest(BaseModel):
    level: Optional[str] = None


class HangmanState(BaseModel):
    session_id: str
    word_id: int
    display: str  # "_ _ _ _" formato
    guessed_letters: List[str]
    attempts_left: int
    max_attempts: int = 6
    hint: str  # Tradução em português
    ipa: str

    # Contexto extra para dicas melhores (opcionais)
    level: Optional[str] = None
    word_type: Optional[str] = None
    tags: List[str] = []
    definition_pt: Optional[str] = None
    definition_en: Optional[str] = None
    example_en: Optional[str] = None
    example_pt: Optional[str] = None
    usage_notes: Optional[str] = None
    length: int = 0


class HangmanGuessRequest(BaseModel):
    letter: str


class HangmanGuessResponse(BaseModel):
    correct: bool
    display: str
    guessed_letters: List[str]
    attempts_left: int
    game_over: bool
    won: bool
    word: Optional[str] = None
    xp_earned: int = 0
    new_achievements: List[AchievementResponse] = []


# ============== Matching ==============

class MatchingCard(BaseModel):
    id: str
    content: str
    type: str  # "english" ou "portuguese"
    pair_id: int


class MatchingGameRequest(BaseModel):
    level: Optional[str] = None
    pairs: int = 8


class MatchingGameResponse(BaseModel):
    session_id: str
    cards: List[MatchingCard]
    total_pairs: int
    due_pairs: int = 0
    new_pairs: int = 0
    review_ratio: float = 0.0


class MatchingResultRequest(BaseModel):
    session_id: str
    time_spent: int
    moves: int
    completed: bool = True


class MatchingResultResponse(BaseModel):
    score: int
    time_spent: int
    moves: int
    xp_earned: int
    is_best_time: bool = False
    new_achievements: List[AchievementResponse] = []


# ============== Ditado ==============

class DictationWord(BaseModel):
    word_id: int
    word: str  # Palavra em inglês para o text-to-speech
    ipa: str
    hint: str  # Tradução em português como dica


class DictationSessionRequest(BaseModel):
    level: Optional[str] = None
    count: int = 10


class DictationSessionResponse(BaseModel):
    session_id: str
    words: List[DictationWord]
    total: int


class DictationAnswerRequest(BaseModel):
    word_id: int
    answer: str


class DictationResultRequest(BaseModel):
    session_id: str
    answers: List[DictationAnswerRequest]
    time_spent: int = 0


class DictationResultResponse(BaseModel):
    score: int
    total: int
    percentage: float
    xp_earned: int
    results: List[dict]
    new_achievements: List[AchievementResponse] = []


# ============== Montar Frases (Sentence Builder) ==============

class SentenceBuilderItem(BaseModel):
    item_id: str
    word_id: int
    focus_word: str
    sentence_en: str
    sentence_pt: str
    tokens: List[str]
    audio_url: Optional[str] = None


class SentenceBuilderSessionResponse(BaseModel):
    session_id: str
    items: List[SentenceBuilderItem]
    total: int


class SentenceBuilderAnswer(BaseModel):
    item_id: str
    tokens: List[str]


class SentenceBuilderSubmitRequest(BaseModel):
    session_id: str
    answers: List[SentenceBuilderAnswer]
    time_spent: int = 0


class SentenceBuilderSubmitResponse(BaseModel):
    score: int
    total: int
    percentage: float
    xp_earned: int
    results: List[dict]
    new_achievements: List[AchievementResponse] = []


# ============== Gramática (Grammar Builder) ==============

class GrammarBuilderItem(BaseModel):
    item_id: str
    sentence_pt: str
    tokens: List[str]
    verb: str
    tip: str
    explanation: str
    level: int
    tense: str
    expected: str
    audio_url: Optional[str] = None


class GrammarBuilderSessionResponse(BaseModel):
    session_id: str
    items: List[GrammarBuilderItem]
    total: int


class GrammarBuilderAnswer(BaseModel):
    item_id: str
    tokens: List[str]


class GrammarBuilderSubmitRequest(BaseModel):
    session_id: str
    answers: List[GrammarBuilderAnswer]
    time_spent: int = 0


class GrammarBuilderSubmitResponse(BaseModel):
    score: int
    total: int
    percentage: float
    xp_earned: int
    results: List[dict]
    new_achievements: List[AchievementResponse] = []


# ============== Desafio Diário ==============

class DailyChallengeResponse(BaseModel):
    id: int
    challenge_type: str
    target: int
    xp_reward: int
    description: str
    progress: int = 0
    completed: bool = False
    
    class Config:
        from_attributes = True


# ============== Ranking ==============

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    name: str
    total_xp: int
    level: int
    words_learned: int


class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
    user_rank: Optional[int] = None
