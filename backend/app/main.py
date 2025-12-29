import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app.routes import auth_router, words_router, study_router, games_router, stats_router, videos_router, sentences_router, admin_router, texts_router

# Importar modelos para criar tabelas
from app.models import gamification  # type: ignore[unused-import]  # noqa: F401
from app.models import sentence  # type: ignore[unused-import]  # noqa: F401

# Criar tabelas
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    # Permite frontends expostos via ngrok e Cloud Run
    allow_origin_regex=r"https://.*\.(ngrok-free\.app|run\.app|a\.run\.app)",
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
