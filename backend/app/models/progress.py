from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class UserProgress(Base):
    """
    Acompanha o progresso de cada palavra para cada usuário.
    Usado para implementar o algoritmo de spaced repetition.
    """
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    
    # Spaced Repetition Fields
    ease_factor = Column(Float, default=2.5)  # Fator de facilidade (SM-2 algorithm)
    interval = Column(Integer, default=0)  # Intervalo atual em dias
    repetitions = Column(Integer, default=0)  # Número de repetições consecutivas corretas
    
    # Scheduling
    next_review = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # Quando revisar novamente
    last_review = Column(DateTime, nullable=True)  # Última revisão

    # Statistics
    total_reviews = Column(Integer, default=0)  # Total de vezes revisada
    correct_count = Column(Integer, default=0)  # Vezes que acertou (fácil/médio)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="progress")
    word = relationship("Word", back_populates="progress")
