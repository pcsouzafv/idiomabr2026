from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from pathlib import Path

# Encontra o diretório raiz do projeto (onde está o .env)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        env_file_encoding="cp1252",
        extra="ignore"
    )

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/idiomasbr"

    # JWT
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # CORS
    # Comma-separated list of origins (e.g. "https://app.idiomasbr.com,https://idiomasbr.com")
    cors_allow_origins: str = ""
    # Regex for dynamic preview domains (ngrok/Cloud Run, etc.)
    cors_allow_origin_regex: str = r"https://.*\.(ngrok-free\.app|run\.app|a\.run\.app)"

    # Frontend base URL (for password reset links)
    frontend_base_url: str = "http://localhost:3000"

    # SMTP (password reset emails)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True
    smtp_ssl: bool = False

    # AI Services
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    # Conversation (LLM chat)
    # auto|deepseek|openai
    conversation_ai_provider: str = "auto"
    conversation_openai_model: str = "gpt-4o-mini"
    conversation_deepseek_model: str = "deepseek-chat"
    conversation_history_messages: int = 6
    conversation_max_tokens: int = 350
    conversation_temperature: float = 0.6
    conversation_timeout_seconds: float = 20.0
    conversation_max_retries: int = 1
    # TTS (OpenAI) - keep explicit so it doesn't inherit any OpenAI-compatible LLM base_url (e.g. DeepSeek)
    openai_tts_base_url: str = "https://api.openai.com/v1"
    openai_tts_model: str = "tts-1"
    # Lemonfox (STT/TTS)
    lemonfox_api_key: str = ""
    lemonfox_base_url: str = "https://api.lemonfox.ai/v1"
    lemonfox_enabled: bool = False
    ollama_url: str = "http://localhost:11434"
    use_ollama_fallback: bool = False
    
    # ElevenLabs API
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)

    # App
    environment: str = "development"  # development|production
    debug: bool = True

    # Session store (Redis)
    redis_enabled: bool = False
    redis_url: str = ""
    session_ttl_seconds: int = 6 * 60 * 60


@lru_cache()
def get_settings() -> Settings:
    loaded = Settings()
    if loaded.environment.lower() == "production" and loaded.secret_key == "your-super-secret-key-change-in-production":
        raise ValueError("SECRET_KEY must be set in production")
    return loaded


settings = get_settings()
