"""
Schemas para vídeos
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.video import VideoLevel, VideoCategory
import re


class VideoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    youtube_url: str
    level: VideoLevel = VideoLevel.A1
    category: VideoCategory = VideoCategory.OTHER
    tags: Optional[str] = None
    duration: Optional[int] = None
    is_active: bool = True
    is_featured: bool = False
    order_index: int = 0

    @field_validator('youtube_url')
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Valida e extrai ID do YouTube da URL"""
        # Padrões de URL do YouTube
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, v)
            if match:
                return v

        raise ValueError('URL do YouTube inválida')

    @staticmethod
    def extract_youtube_id(url: str) -> Optional[str]:
        """Extrai o ID do vídeo do YouTube da URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None


class VideoCreate(VideoBase):
    """Schema para criar vídeo"""
    pass


class VideoUpdate(BaseModel):
    """Schema para atualizar vídeo"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    youtube_url: Optional[str] = None
    level: Optional[VideoLevel] = None
    category: Optional[VideoCategory] = None
    tags: Optional[str] = None
    duration: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    order_index: Optional[int] = None

    @field_validator('youtube_url')
    @classmethod
    def validate_youtube_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Usar mesma validação do VideoBase
        return VideoBase.validate_youtube_url(v)


class VideoResponse(VideoBase):
    """Schema de resposta com dados completos do vídeo"""
    id: int
    youtube_id: str
    thumbnail_url: Optional[str]
    views_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    published_at: Optional[datetime]

    # Progresso do usuário (se autenticado)
    user_progress: Optional[int] = None  # Porcentagem 0-100
    is_completed: Optional[bool] = None

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    """Schema para lista de vídeos"""
    items: list[VideoResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class VideoProgressBase(BaseModel):
    watched_duration: int = Field(..., ge=0)
    completion_percentage: int = Field(..., ge=0, le=100)


class VideoProgressCreate(VideoProgressBase):
    """Schema para criar/atualizar progresso"""
    video_id: int


class VideoProgressUpdate(BaseModel):
    """Schema para atualizar progresso"""
    watched_duration: Optional[int] = Field(None, ge=0)
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)


class VideoProgressResponse(VideoProgressBase):
    """Schema de resposta do progresso"""
    id: int
    user_id: int
    video_id: int
    is_completed: bool
    started_at: datetime
    last_watched_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Dados do vídeo
    video: Optional[VideoResponse] = None

    class Config:
        from_attributes = True
