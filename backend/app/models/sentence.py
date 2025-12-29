from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Sentence(Base):
    """Modelo para frases de estudo"""
    __tablename__ = "sentences"

    id = Column(Integer, primary_key=True, index=True)
    english = Column(Text, nullable=False, index=True)
    portuguese = Column(Text, nullable=False)
    level = Column(String(10), default="A1")  # A1, A2, B1, B2, C1, C2

    # Contexto e metadados
    category = Column(String(100), nullable=True)  # conversation, business, travel, etc
    difficulty_score = Column(Float, default=0.0)  # 0.0 - 10.0

    # Análise gramatical
    grammar_points = Column(Text, nullable=True)  # JSON com pontos gramaticais
    vocabulary_used = Column(Text, nullable=True)  # JSON com palavras-chave

    # Audio (futuro)
    audio_url = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reviews = relationship("SentenceReview", back_populates="sentence")
    progress = relationship("UserSentenceProgress", back_populates="sentence")


class SentenceReview(Base):
    """Histórico de revisões de frases"""
    __tablename__ = "sentence_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sentence_id = Column(Integer, ForeignKey("sentences.id"), nullable=False)

    # Dados da revisão
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    direction = Column(String(20), nullable=False)  # en_to_pt, pt_to_en

    # Timestamp
    reviewed_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
    sentence = relationship("Sentence", back_populates="reviews")


class UserSentenceProgress(Base):
    """Progresso do usuário em frases específicas"""
    __tablename__ = "user_sentence_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sentence_id = Column(Integer, ForeignKey("sentences.id"), nullable=False, index=True)

    # Progresso
    easiness_factor = Column(Float, default=2.5)  # SM-2 algorithm
    interval = Column(Integer, default=0)  # Days until next review
    repetitions = Column(Integer, default=0)

    # Timestamps
    last_reviewed = Column(DateTime, nullable=True)
    next_review = Column(DateTime, nullable=True, index=True)

    # Relationships
    user = relationship("User")
    sentence = relationship("Sentence", back_populates="progress")


class AIConversation(Base):
    """Conversas com o professor de IA"""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sentence_id = Column(Integer, ForeignKey("sentences.id"), nullable=True)

    # Dados da conversa
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # JSON com contexto adicional

    # Metadados
    model_used = Column(String(50), nullable=True)  # openai, ollama, etc
    tokens_used = Column(Integer, default=0)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")
    sentence = relationship("Sentence")
