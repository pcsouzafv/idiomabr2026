from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class StudyText(Base):
    __tablename__ = "study_texts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    level = Column(String(8), index=True, nullable=False, default="A1")

    content_en = Column(Text, nullable=False)
    content_pt = Column(Text, nullable=True)

    audio_url = Column(Text, nullable=True)

    tags = Column(JSONB, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class StudyTextAttempt(Base):
    __tablename__ = "study_text_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    text_id = Column(Integer, ForeignKey("study_texts.id", ondelete="CASCADE"), index=True, nullable=False)

    task = Column(String(32), nullable=False, default="writing")  # writing|summary|translation

    user_text = Column(Text, nullable=False)

    ai_feedback = Column(Text, nullable=True)
    ai_json = Column(JSONB, nullable=True)
    model_used = Column(String(32), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
