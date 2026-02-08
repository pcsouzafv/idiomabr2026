from pydantic import BaseModel
from typing import List
from datetime import datetime

from app.schemas.word import WordResponse


class ReviewCreate(BaseModel):
    word_id: int
    difficulty: str  # easy, medium, hard
    direction: str = "en_to_pt"  # en_to_pt or pt_to_en


class ReviewResponse(BaseModel):
    id: int
    word_id: int
    difficulty: str
    direction: str
    reviewed_at: datetime
    
    class Config:
        from_attributes = True


class StudyCard(BaseModel):
    """Um cartão de estudo com todas as informações necessárias"""
    word: WordResponse
    direction: str  # en_to_pt or pt_to_en
    is_new: bool  # Palavra nova ou revisão
    
    class Config:
        from_attributes = True


class StudySession(BaseModel):
    """Sessão de estudo com múltiplos cartões"""
    cards: List[StudyCard]
    total_new: int
    total_review: int
    session_size: int


class ProgressStats(BaseModel):
    """Estatísticas de progresso do usuário"""
    total_words_studied: int
    total_words_learned: int
    words_studied_today: int
    current_streak: int
    words_to_review_today: int
    new_words_available: int
    daily_goal: int
    daily_goal_progress: float  # Porcentagem
