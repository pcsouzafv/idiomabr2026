"""
Schemas para rotas de administração
"""
from typing import Optional, Dict, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


# ============== ESTATÍSTICAS ==============

class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_words: int
    total_sentences: int
    total_videos: int
    total_reviews: int
    words_by_level: Dict[str, int]


# ============== USUÁRIOS ==============

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    is_active: bool
    is_admin: bool
    daily_goal: int
    current_streak: int
    last_study_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    daily_goal: Optional[int] = None


class UserCreateAdmin(BaseModel):
    email: EmailStr
    name: str
    password: str
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    daily_goal: Optional[int] = None


# ============== PALAVRAS ==============

class WordResponse(BaseModel):
    id: int
    english: str
    ipa: Optional[str]
    portuguese: str
    level: str
    word_type: Optional[str]
    definition_en: Optional[str]
    definition_pt: Optional[str]
    synonyms: Optional[str]
    antonyms: Optional[str]
    example_en: Optional[str]
    example_pt: Optional[str]
    usage_notes: Optional[str]
    tags: Optional[str]
    audio_url: Optional[str]

    class Config:
        from_attributes = True


class WordCreate(BaseModel):
    english: str
    ipa: Optional[str] = None
    portuguese: str
    level: str = "A1"
    word_type: Optional[str] = None
    definition_en: Optional[str] = None
    definition_pt: Optional[str] = None
    synonyms: Optional[str] = None
    antonyms: Optional[str] = None
    example_en: Optional[str] = None
    example_pt: Optional[str] = None
    example_sentences: Optional[str] = None
    usage_notes: Optional[str] = None
    collocations: Optional[str] = None
    tags: Optional[str] = None
    audio_url: Optional[str] = None


class WordUpdate(BaseModel):
    english: Optional[str] = None
    ipa: Optional[str] = None
    portuguese: Optional[str] = None
    level: Optional[str] = None
    word_type: Optional[str] = None
    definition_en: Optional[str] = None
    definition_pt: Optional[str] = None
    synonyms: Optional[str] = None
    antonyms: Optional[str] = None
    example_en: Optional[str] = None
    example_pt: Optional[str] = None
    example_sentences: Optional[str] = None
    usage_notes: Optional[str] = None
    collocations: Optional[str] = None
    tags: Optional[str] = None
    audio_url: Optional[str] = None


# ============== SENTENÇAS ==============

class SentenceResponse(BaseModel):
    id: int
    english: str
    portuguese: str
    level: str
    category: Optional[str]
    grammar_points: Optional[str]
    vocabulary_used: Optional[str]
    difficulty_score: Optional[float]
    audio_url: Optional[str]

    class Config:
        from_attributes = True


class SentenceCreate(BaseModel):
    english: str
    portuguese: str
    level: str = "A1"
    category: Optional[str] = None
    grammar_points: Optional[str] = None
    vocabulary_used: Optional[str] = None
    difficulty_score: Optional[float] = None
    audio_url: Optional[str] = None


class SentenceUpdate(BaseModel):
    english: Optional[str] = None
    portuguese: Optional[str] = None
    level: Optional[str] = None
    category: Optional[str] = None
    grammar_points: Optional[str] = None
    vocabulary_used: Optional[str] = None
    difficulty_score: Optional[float] = None
    audio_url: Optional[str] = None


# ============== VÍDEOS ==============

class VideoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    youtube_id: str
    youtube_url: str
    thumbnail_url: Optional[str]
    level: str
    category: str
    tags: Optional[str]
    duration: Optional[int]
    is_active: bool
    is_featured: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VideoCreate(BaseModel):
    title: str
    description: Optional[str] = None
    youtube_id: str
    youtube_url: str
    thumbnail_url: Optional[str] = None
    level: str = "A1"
    category: str = "other"
    tags: Optional[str] = None
    duration: Optional[int] = None
    is_active: bool = True
    is_featured: bool = False


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    youtube_id: Optional[str] = None
    youtube_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    level: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    duration: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


# ============== BULK IMPORT ==============

class BulkImportResponse(BaseModel):
    created: int
    updated: int
    errors: List[str]
    total_processed: int


# ============== TEXTOS (LEITURA & ESCRITA) ==============

class StudyTextAdminListItem(BaseModel):
    id: int
    title: str
    level: str
    audio_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudyTextAdminResponse(BaseModel):
    id: int
    title: str
    level: str
    content_en: str
    content_pt: Optional[str] = None
    audio_url: Optional[str] = None
    tags: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudyTextAdminCreate(BaseModel):
    title: str
    level: str = "A1"
    content_en: str
    content_pt: Optional[str] = None
    audio_url: Optional[str] = None
    tags: Optional[dict] = None


class StudyTextAdminUpdate(BaseModel):
    title: Optional[str] = None
    level: Optional[str] = None
    content_en: Optional[str] = None
    content_pt: Optional[str] = None
    audio_url: Optional[str] = None
    tags: Optional[dict] = None
