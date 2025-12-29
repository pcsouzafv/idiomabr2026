from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.core.database import Base


class DifficultyEnum(str, enum.Enum):
    EASY = "easy"       # Fácil - revisar em 3 dias
    MEDIUM = "medium"   # Médio - revisar amanhã
    HARD = "hard"       # Difícil - revisar hoje


class Review(Base):
    """
    Registra cada vez que o usuário revisa uma palavra.
    Usado para calcular o spaced repetition.
    """
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Direction of study
    # en_to_pt = English shown first, reveal Portuguese
    # pt_to_en = Portuguese shown first, reveal English
    direction = Column(String(20), default="en_to_pt")
    
    # Relationships
    user = relationship("User", back_populates="reviews")
    word = relationship("Word", back_populates="reviews")
