from sqlalchemy import Column, DateTime, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AICacheEntry(Base):
    __tablename__ = "ai_cache"

    id = Column(Integer, primary_key=True, index=True)

    # Deterministic key based on operation + scope + request payload
    cache_key = Column(String(64), unique=True, index=True, nullable=False)

    # e.g. "global" or "user:123"
    scope = Column(String(64), index=True, nullable=False, default="global")

    operation = Column(String(64), index=True, nullable=False)

    provider = Column(String(32), nullable=True)
    model = Column(String(64), nullable=True)

    request_json = Column(JSONB, nullable=False)

    response_text = Column(Text, nullable=True)
    response_json = Column(JSONB, nullable=True)
    response_bytes = Column(LargeBinary, nullable=True)

    status = Column(String(16), nullable=False, default="ok")
    error = Column(Text, nullable=True)

    hit_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
