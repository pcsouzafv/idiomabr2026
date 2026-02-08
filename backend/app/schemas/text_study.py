from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal, Any


class StudyTextListItem(BaseModel):
    id: int
    title: str
    level: str
    word_count: int


class StudyTextDetail(BaseModel):
    id: int
    title: str
    level: str
    content_en: str
    content_pt: Optional[str] = None
    audio_url: Optional[str] = None
    tags: Optional[Any] = None


class StudyTextAttemptCreate(BaseModel):
    task: Literal["writing", "summary", "translation"] = "writing"
    user_text: str = Field(min_length=1)


class StudyTextAttemptResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    text_id: int
    task: str
    user_text: str
    ai_feedback: Optional[str] = None
    model_used: Optional[str] = None


class StudyTextAttemptListItem(BaseModel):
    id: int
    text_id: int
    task: str
    created_at: str
