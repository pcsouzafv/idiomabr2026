from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
import enum

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

    id = Column(Integer, primary_key=True, index=True)
    english = Column(String(255), nullable=False, index=True)
    ipa = Column(String(255), nullable=True)  # Transcrição fonética
    portuguese = Column(String(255), nullable=False)
    level = Column(String(10), default="A1")  # A1, A2, B1, B2, C1, C2

    # Informações gramaticais e semânticas
    word_type = Column(String(50), nullable=True)  # noun, verb, adjective, adverb, etc
    definition_en = Column(Text, nullable=True)  # Definição em inglês
    definition_pt = Column(Text, nullable=True)  # Definição em português
    synonyms = Column(Text, nullable=True)  # Sinônimos separados por vírgula
    antonyms = Column(Text, nullable=True)  # Antônimos separados por vírgula

    # Exemplos e uso
    example_en = Column(Text, nullable=True)  # Frase de exemplo em inglês
    example_pt = Column(Text, nullable=True)  # Frase de exemplo em português
    example_sentences = Column(Text, nullable=True)  # JSON com múltiplos exemplos
    usage_notes = Column(Text, nullable=True)  # Dicas de uso, contexto, nuances
    collocations = Column(Text, nullable=True)  # Colocações comuns (JSON)

    # Categorização
    tags = Column(String(500), nullable=True)  # Tags separadas por vírgula: "comida,viagem,negócios"
    audio_url = Column(String(500), nullable=True)  # URL do áudio (futuro)

    # Relationships
    reviews = relationship("Review", back_populates="word")
    progress = relationship("UserProgress", back_populates="word")
