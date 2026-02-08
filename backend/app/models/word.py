from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LevelEnum(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    english: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ipa: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Transcrição fonética
    portuguese: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(10), default="A1")  # A1, A2, B1, B2, C1, C2

    # Informações gramaticais e semânticas
    word_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # noun, verb, adjective, adverb, etc
    definition_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Definição em inglês
    definition_pt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Definição em português
    synonyms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Sinônimos separados por vírgula
    antonyms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Antônimos separados por vírgula

    # Exemplos e uso
    example_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Frase de exemplo em inglês
    example_pt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Frase de exemplo em português
    example_sentences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON com múltiplos exemplos
    usage_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Dicas de uso, contexto, nuances
    collocations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Colocações comuns (JSON)

    # Categorização
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Tags separadas por vírgula: "comida,viagem,negócios"
    audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL do áudio (futuro)

    # Relationships
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="word")
    progress: Mapped[list["UserProgress"]] = relationship("UserProgress", back_populates="word")
