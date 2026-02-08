import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app.core.config import get_settings
from app.routes import auth_router, words_router, study_router, games_router, stats_router, videos_router, sentences_router, admin_router, texts_router, exams_router, conversation_router

# Importar modelos para criar tabelas
from app.models import gamification  # type: ignore[unused-import]  # noqa: F401
from app.models import sentence  # type: ignore[unused-import]  # noqa: F401
from app.models import conversation_lesson  # type: ignore[unused-import]  # noqa: F401

settings = get_settings()

# Criar tabelas (apenas em desenvolvimento)
if settings.environment.lower() != "production":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="IdiomasBR",
    description="API para aprendizado de inglês com flashcards e spaced repetition",
    version="1.0.0"
)

# Static files (e.g., generated TTS audio)
_static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# CORS
_default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    # Production (VPS) defaults
    "https://idiomasbr.com",
    "https://www.idiomasbr.com",
    "https://app.idiomasbr.com",
]
_extra_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
_allow_origins = list(dict.fromkeys(_default_origins + _extra_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    # Permite frontends expostos via ngrok e Cloud Run (e custom via env)
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(auth_router)
app.include_router(words_router)
app.include_router(study_router)
app.include_router(games_router)
app.include_router(stats_router)
app.include_router(videos_router)
app.include_router(sentences_router)
app.include_router(admin_router)
app.include_router(texts_router)
app.include_router(exams_router)
app.include_router(conversation_router)


@app.get("/")
def root():
    return {
        "message": "Bem-vindo à API IdiomasBR!",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
