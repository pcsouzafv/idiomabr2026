"""
Modelos para o sistema de vídeos/aulas
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class VideoLevel(str, enum.Enum):
    """Níveis de dificuldade dos vídeos"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    ALL = "ALL"  # Para vídeos que servem para todos os níveis


class VideoCategory(str, enum.Enum):
    """Categorias de vídeos"""
    GRAMMAR = "grammar"  # Gramática
    VOCABULARY = "vocabulary"  # Vocabulário
    PRONUNCIATION = "pronunciation"  # Pronúncia
    LISTENING = "listening"  # Compreensão auditiva
    CONVERSATION = "conversation"  # Conversação
    TIPS = "tips"  # Dicas de estudo
    CULTURE = "culture"  # Cultura
    OTHER = "other"  # Outros


class Video(Base):
    """Modelo para vídeos de aulas do YouTube"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)

    # Informações básicas
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    youtube_id = Column(String(50), nullable=False, unique=True, index=True)  # ID do vídeo do YouTube
    youtube_url = Column(String(255), nullable=False)  # URL completa
    thumbnail_url = Column(String(500))  # URL da thumbnail

    # Categorização
    level = Column(Enum(VideoLevel), default=VideoLevel.A1, index=True)
    category = Column(Enum(VideoCategory), default=VideoCategory.OTHER, index=True)
    tags = Column(String(500))  # Tags separadas por vírgula

    # Metadados
    duration = Column(Integer)  # Duração em segundos
    views_count = Column(Integer, default=0)  # Contador de visualizações
    order_index = Column(Integer, default=0)  # Ordem de exibição

    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Destacado na página inicial

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))  # Data de publicação no YouTube

    # Relacionamentos
    progress = relationship("VideoProgress", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video {self.title}>"


class VideoProgress(Base):
    """Progresso do usuário em um vídeo"""
    __tablename__ = "video_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)

    # Progresso
    watched_duration = Column(Integer, default=0)  # Tempo assistido em segundos
    is_completed = Column(Boolean, default=False)
    completion_percentage = Column(Integer, default=0)  # Porcentagem assistida (0-100)

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_watched_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True))

    # Relacionamentos
    video = relationship("Video", back_populates="progress")
    user = relationship("User", back_populates="video_progress")

    def __repr__(self):
        return f"<VideoProgress user={self.user_id} video={self.video_id} {self.completion_percentage}%>"
