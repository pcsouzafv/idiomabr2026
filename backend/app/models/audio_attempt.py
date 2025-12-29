from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AudioAttempt(Base):
    __tablename__ = "audio_attempts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    sentence_id = Column(Integer, ForeignKey("sentences.id", ondelete="SET NULL"), index=True, nullable=True)

    filename = Column(String(255), nullable=True)
    content_type = Column(String(100), nullable=True)

    audio_sha256 = Column(String(64), index=True, nullable=False)
    audio_bytes = Column(LargeBinary, nullable=False)

    expected_text = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)

    similarity = Column(Integer, nullable=True)  # 0-100

    ai_feedback = Column(Text, nullable=True)
    ai_json = Column(JSONB, nullable=True)

    model_used = Column(String(32), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
