from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class SentenceBase(BaseModel):
    english: str
    portuguese: str
    level: str = "A1"
    category: Optional[str] = None
    difficulty_score: Optional[float] = 0.0
    grammar_points: Optional[str] = None
    vocabulary_used: Optional[str] = None


class SentenceCreate(SentenceBase):
    pass


class SentenceResponse(SentenceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SentenceReviewCreate(BaseModel):
    sentence_id: int
    difficulty: str  # easy, medium, hard
    direction: str  # en_to_pt, pt_to_en


class SentenceReviewResponse(BaseModel):
    id: int
    sentence_id: int
    difficulty: str
    direction: str
    reviewed_at: datetime

    class Config:
        from_attributes = True


class StudyCard(BaseModel):
    sentence: SentenceResponse
    direction: str
    is_new: bool


class StudySession(BaseModel):
    cards: List[StudyCard]
    total_new: int
    total_review: int
    session_size: int


class AITeacherRequest(BaseModel):
    sentence_id: Optional[int] = None
    user_message: str
    include_context: bool = True


class AITeacherResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    response: str
    model_used: str
    context_used: Optional[dict] = None
    suggestions: Optional[List[str]] = None


class AIConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    user_message: str
    ai_response: str
    model_used: Optional[str] = None
    created_at: datetime
