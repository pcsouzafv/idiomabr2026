from app.routes.auth import router as auth_router
from app.routes.words import router as words_router
from app.routes.study import router as study_router
from app.routes.games import router as games_router
from app.routes.stats import router as stats_router
from app.routes.videos import router as videos_router
from app.routes.sentences import router as sentences_router
from app.routes.admin import router as admin_router
from app.routes.texts import router as texts_router

__all__ = ["auth_router", "words_router", "study_router", "games_router", "stats_router", "videos_router", "sentences_router", "admin_router", "texts_router"]
