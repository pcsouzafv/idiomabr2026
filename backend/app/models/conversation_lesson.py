from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class ConversationLessonAttempt(Base):
    __tablename__ = "conversation_lesson_attempts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    native_language = Column(String(16), nullable=False, default="pt-BR")
    target_language = Column(String(16), nullable=False, default="en")

    questions = Column(JSONB, nullable=False)
    answers = Column(JSONB, nullable=False)

    ai_feedback = Column(Text, nullable=True)
    ai_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)