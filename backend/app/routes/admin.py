"""
Rotas de administração do sistema
Requer autenticação como admin (is_admin=True)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, Integer, cast, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone, timedelta
import logging
import os
import json
import hashlib
import csv
import io

from app.core.database import get_db
from app.core.security import require_admin, get_password_hash
from app.core.config import get_settings
from app.models.user import User
from app.models.word import Word
from app.models.sentence import Sentence
from app.models.video import Video
from app.models.review import Review
from app.models.ai_usage import AIUsageLog
from app.models.progress import UserProgress
from app.models.text_study import StudyText
from app.utils.text_sanitize import sanitize_unmatched_brackets
from app.services.ai_teacher import ai_teacher_service
from services.dictionary_api import enrich_word_from_api
from enrich_words_api import translate_en_to_pt_br, translate_pt_br_to_en
from app.schemas.admin import (
    AdminStats,
    AdminPerformanceReport,
    AdminPerformanceOverview,
    AdminUserPerformance,
    AdminAIUsageReport,
    AdminAIUsageOverview,
    AdminAIUsageUser,
    AdminAIUsageProvider,
    PaginatedUsersResponse,
    UserCreateAdmin,
    WordCreate,
    WordUpdate,
    WordAIFillRequest,
    WordResponse,
    SentenceCreate,
    SentenceUpdate,
    SentenceResponse,
    VideoCreate,
    VideoUpdate,
    VideoResponse,
    UserResponse,
    UserUpdate,
    BulkImportResponse,
    StudyTextAdminListItem,
    StudyTextAdminResponse,
    StudyTextAdminCreate,
    StudyTextAdminUpdate
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


def _extract_db_error_message(exc: Exception) -> str:
    """Extrai mensagem útil do erro de banco para resposta administrativa."""
    raw = str(getattr(exc, "orig", exc) or "").strip()
    if not raw:
        return "erro desconhecido no banco de dados"
    return raw.splitlines()[0]


def _cleanup_user_dependencies(db: Session, user_id: int) -> None:
    """Remove/neutraliza registros que referenciam um usuário antes do delete.

    Suporta bancos antigos onde algumas FKs para users ficaram com NO ACTION.
    """
    fk_rows = db.execute(
        text(
            """
            SELECT DISTINCT
                n.nspname AS schema_name,
                c.relname AS table_name,
                a.attname AS column_name,
                con.confdeltype AS confdeltype,
                cols.is_nullable AS is_nullable
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN unnest(con.conkey) AS k(attnum) ON TRUE
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
            LEFT JOIN information_schema.columns cols
                ON cols.table_schema = n.nspname
                AND cols.table_name = c.relname
                AND cols.column_name = a.attname
            WHERE con.contype = 'f'
              AND con.confrelid = 'users'::regclass
              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
              AND c.relname <> 'users'
            ORDER BY n.nspname, c.relname, a.attname
            """
        )
    ).mappings().all()

    for row in fk_rows:
        schema_name = str(row["schema_name"])
        table_name = str(row["table_name"])
        column_name = str(row["column_name"])
        confdeltype = str(row["confdeltype"] or "")
        is_nullable = str(row["is_nullable"] or "").upper() == "YES"
        qualified_table = f'"{schema_name}"."{table_name}"'

        # confdeltype n = ON DELETE SET NULL
        should_set_null = confdeltype == "n" or is_nullable
        if should_set_null:
            db.execute(
                text(f'UPDATE {qualified_table} SET "{column_name}" = NULL WHERE "{column_name}" = :user_id'),
                {"user_id": user_id},
            )
        else:
            db.execute(
                text(f'DELETE FROM {qualified_table} WHERE "{column_name}" = :user_id'),
                {"user_id": user_id},
            )


# ============== DASHBOARD & ESTATÍSTICAS ==============

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Dashboard principal com estatísticas do sistema"""

    # Contadores gerais
    total_users = db.query(func.count(User.id)).scalar()
    total_words = db.query(func.count(Word.id)).scalar()
    total_sentences = db.query(func.count(Sentence.id)).scalar()
    total_videos = db.query(func.count(Video.id)).scalar()
    total_reviews = db.query(func.count(Review.id)).scalar()

    # Usuários ativos (estudaram nos últimos 7 dias)
    from datetime import timedelta
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_users = db.query(func.count(User.id)).filter(
        User.last_study_date >= seven_days_ago
    ).scalar()

    # Palavras por nível
    words_by_level = db.query(
        Word.level,
        func.count(Word.id).label("count")
    ).group_by(Word.level).all()

    words_by_level_dict = {level: count for level, count in words_by_level}

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_words": total_words,
        "total_sentences": total_sentences,
        "total_videos": total_videos,
        "total_reviews": total_reviews,
        "words_by_level": words_by_level_dict
    }


@router.get("/performance", response_model=AdminPerformanceReport)
async def get_admin_performance(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Relatório de desempenho geral e individual dos alunos"""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.last_study_date >= since).scalar() or 0

    reviews_base = db.query(Review).filter(Review.reviewed_at >= since)
    total_reviews = reviews_base.count() or 0
    total_unique_words = (
        reviews_base.with_entities(func.count(func.distinct(Review.word_id))).scalar() or 0
    )
    correct_reviews = (
        reviews_base.filter(Review.difficulty.in_(["easy", "medium"])).count() or 0
    )

    accuracy_percent = (correct_reviews / total_reviews * 100) if total_reviews else 0.0
    reviews_per_active_user = (total_reviews / active_users) if active_users else 0.0

    overview = AdminPerformanceOverview(
        total_users=total_users,
        active_users=active_users,
        total_reviews=total_reviews,
        total_unique_words=total_unique_words,
        accuracy_percent=round(accuracy_percent, 2),
        reviews_per_active_user=round(reviews_per_active_user, 2)
    )

    correct_reviews_expr = func.coalesce(
        func.sum(cast(Review.difficulty.in_(["easy", "medium"]), Integer)),
        0
    ).label("correct_reviews")

    user_rows = (
        db.query(
            User.id.label("user_id"),
            User.name,
            User.email,
            User.last_study_date,
            User.current_streak,
            func.count(Review.id).label("total_reviews"),
            func.count(func.distinct(Review.word_id)).label("unique_words"),
            correct_reviews_expr
        )
        .outerjoin(
            Review,
            and_(Review.user_id == User.id, Review.reviewed_at >= since)
        )
        .group_by(User.id)
        .order_by(desc("total_reviews"), User.name.asc())
        .limit(limit)
        .all()
    )

    users: List[AdminUserPerformance] = []
    for row in user_rows:
        total_user_reviews = int(row.total_reviews or 0)
        correct_user_reviews = int(row.correct_reviews or 0)
        user_accuracy = (correct_user_reviews / total_user_reviews * 100) if total_user_reviews else 0.0
        users.append(
            AdminUserPerformance(
                user_id=row.user_id,
                name=row.name,
                email=row.email,
                last_study_date=row.last_study_date,
                current_streak=row.current_streak,
                total_reviews=total_user_reviews,
                unique_words=int(row.unique_words or 0),
                accuracy_percent=round(user_accuracy, 2)
            )
        )

    return AdminPerformanceReport(period_days=days, overview=overview, users=users)


@router.get("/ai-usage", response_model=AdminAIUsageReport)
async def get_admin_ai_usage(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Relatório de uso de IA (tokens) por usuário e por modelo/provedor."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    settings = get_settings()

    if not inspect(db.bind).has_table(AIUsageLog.__tablename__):
        budget_tokens = max(0, int(getattr(settings, "ai_usage_budget_tokens", 0) or 0))
        overview = AdminAIUsageOverview(
            period_days=days,
            total_requests=0,
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0,
            budget_tokens=budget_tokens,
            budget_used_percent=0.0,
            remaining_tokens=budget_tokens if budget_tokens > 0 else None,
            budget_status="unconfigured" if budget_tokens <= 0 else "ok",
        )
        return AdminAIUsageReport(
            generated_at=datetime.now(timezone.utc),
            overview=overview,
            users=[],
            providers=[],
            system_usage_requests=0,
            system_usage_tokens=0,
        )

    totals_row = (
        db.query(
            func.count(AIUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(AIUsageLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
        )
        .filter(AIUsageLog.created_at >= since)
        .first()
    )

    user_rows = (
        db.query(
            User.id.label("user_id"),
            User.name.label("name"),
            User.email.label("email"),
            func.count(AIUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(AIUsageLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
            func.max(AIUsageLog.created_at).label("last_usage_at"),
        )
        .join(User, User.id == AIUsageLog.user_id)
        .filter(AIUsageLog.created_at >= since)
        .group_by(User.id)
        .order_by(desc("total_tokens"), desc("total_requests"))
        .limit(limit)
        .all()
    )

    provider_rows = (
        db.query(
            AIUsageLog.provider.label("provider"),
            AIUsageLog.model.label("model"),
            func.count(AIUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
        )
        .filter(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.provider, AIUsageLog.model)
        .order_by(desc("total_tokens"), desc("total_requests"))
        .all()
    )

    system_usage_row = (
        db.query(
            func.count(AIUsageLog.id).label("total_requests"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
        )
        .filter(
            AIUsageLog.created_at >= since,
            AIUsageLog.user_id.is_(None),
        )
        .first()
    )

    budget_tokens = max(0, int(getattr(settings, "ai_usage_budget_tokens", 0) or 0))
    warn_pct = float(getattr(settings, "ai_usage_warning_percent", 80.0) or 80.0)
    critical_pct = float(getattr(settings, "ai_usage_critical_percent", 95.0) or 95.0)

    total_requests = int((totals_row.total_requests if totals_row else 0) or 0)
    total_prompt_tokens = int((totals_row.prompt_tokens if totals_row else 0) or 0)
    total_completion_tokens = int((totals_row.completion_tokens if totals_row else 0) or 0)
    total_tokens = int((totals_row.total_tokens if totals_row else 0) or 0)

    if budget_tokens > 0:
        budget_used_percent = round((total_tokens / budget_tokens) * 100, 2)
        remaining_tokens = max(0, budget_tokens - total_tokens)
        if budget_used_percent >= critical_pct:
            budget_status = "critical"
        elif budget_used_percent >= warn_pct:
            budget_status = "warning"
        else:
            budget_status = "ok"
    else:
        budget_used_percent = 0.0
        remaining_tokens = None
        budget_status = "unconfigured"

    users = [
        AdminAIUsageUser(
            user_id=int(row.user_id),
            name=row.name,
            email=row.email,
            total_requests=int(row.total_requests or 0),
            prompt_tokens=int(row.prompt_tokens or 0),
            completion_tokens=int(row.completion_tokens or 0),
            total_tokens=int(row.total_tokens or 0),
            last_usage_at=row.last_usage_at,
        )
        for row in user_rows
    ]

    providers = [
        AdminAIUsageProvider(
            provider=str(row.provider or "unknown"),
            model=row.model,
            total_requests=int(row.total_requests or 0),
            total_tokens=int(row.total_tokens or 0),
        )
        for row in provider_rows
    ]

    overview = AdminAIUsageOverview(
        period_days=days,
        total_requests=total_requests,
        total_prompt_tokens=total_prompt_tokens,
        total_completion_tokens=total_completion_tokens,
        total_tokens=total_tokens,
        budget_tokens=budget_tokens,
        budget_used_percent=budget_used_percent,
        remaining_tokens=remaining_tokens,
        budget_status=budget_status,
    )

    return AdminAIUsageReport(
        generated_at=datetime.now(timezone.utc),
        overview=overview,
        users=users,
        providers=providers,
        system_usage_requests=int((system_usage_row.total_requests if system_usage_row else 0) or 0),
        system_usage_tokens=int((system_usage_row.total_tokens if system_usage_row else 0) or 0),
    )


# ============== GERENCIAMENTO DE USUÁRIOS ==============

@router.get("/users", response_model=PaginatedUsersResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todos os usuários com paginação"""
    query = db.query(User)

    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )

    total = query.count()
    users = query.order_by(desc(User.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    import math
    return {
        "items": users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 1
    }


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user_data: UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Criar novo usuário (admin)"""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email já registrado")
    phone_number = user_data.phone_number.strip()
    if not phone_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone é obrigatório")
    existing_phone = db.query(User).filter(User.phone_number == phone_number).first()
    if existing_phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone já registrado")

    new_user = User(
        email=user_data.email,
        phone_number=phone_number,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        is_active=bool(user_data.is_active),
        is_admin=bool(user_data.is_admin),
        email_verified_at=datetime.now(timezone.utc) if bool(user_data.email_verified) else None,
    )
    if user_data.daily_goal is not None:
        setattr(new_user, "daily_goal", user_data.daily_goal)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter detalhes de um usuário específico"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atualizar dados de um usuário"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data:
        password_value = (update_data.get("password") or "").strip()
        if password_value:
            if len(password_value) < 6:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha muito curta")
            setattr(user, "hashed_password", get_password_hash(password_value))
        update_data.pop("password", None)
    if "phone_number" in update_data:
        phone_value = (update_data.get("phone_number") or "").strip()
        if phone_value:
            existing_phone = db.query(User).filter(User.phone_number == phone_value, User.id != user_id).first()
            if existing_phone:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone já registrado")
            update_data["phone_number"] = phone_value
        else:
            update_data["phone_number"] = None
    if "email_verified" in update_data:
        email_verified_value = update_data.pop("email_verified")
        if email_verified_value is True:
            if not user.email_verified_at:
                user.email_verified_at = datetime.now(timezone.utc)
        elif email_verified_value is False:
            user.email_verified_at = None

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deletar um usuário (cuidado!)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        _cleanup_user_dependencies(db, user_id)
        db.delete(user)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        reason = _extract_db_error_message(exc)
        logger.exception("Falha ao deletar usuario %s (%s): %s", user.id, user.email, reason)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não foi possível deletar usuário devido a vínculos de dados: {reason}",
        )
    except Exception as exc:
        db.rollback()
        reason = _extract_db_error_message(exc)
        logger.exception("Falha inesperada ao deletar usuario %s (%s): %s", user.id, user.email, reason)
        raise HTTPException(status_code=500, detail=f"Falha ao deletar usuário: {reason}")

    return {"message": "Usuário deletado com sucesso"}


# ============== GERENCIAMENTO DE PALAVRAS ==============

@router.get("/words", response_model=List[WordResponse])
async def list_words_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todas as palavras com filtros"""
    query = db.query(Word)

    if search:
        query = query.filter(
            (Word.english.ilike(f"%{search}%")) |
            (Word.portuguese.ilike(f"%{search}%"))
        )

    if level:
        query = query.filter(Word.level == level)

    total = query.count()
    words = query.order_by(Word.english).offset((page - 1) * per_page).limit(per_page).all()

    return words


@router.get("/words/export")
async def export_words_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exportar palavras em CSV"""
    words = db.query(Word).order_by(Word.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "english",
        "ipa",
        "portuguese",
        "level",
        "word_type",
        "definition_en",
        "definition_pt",
        "example_en",
        "example_pt",
        "tags",
    ])

    for w in words:
        writer.writerow([
            w.id,
            w.english,
            w.ipa or "",
            w.portuguese,
            w.level,
            getattr(w, "word_type", None) or "",
            getattr(w, "definition_en", None) or "",
            getattr(w, "definition_pt", None) or "",
            getattr(w, "example_en", None) or "",
            getattr(w, "example_pt", None) or "",
            getattr(w, "tags", None) or "",
        ])

    filename = f"words_export_{datetime.now(timezone.utc).date().isoformat()}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/words", response_model=WordResponse, status_code=status.HTTP_201_CREATED)
async def create_word(
    word: WordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Criar uma nova palavra"""
    payload = word.model_dump()
    payload["english"] = sanitize_unmatched_brackets(payload.get("english"))
    payload["portuguese"] = sanitize_unmatched_brackets(payload.get("portuguese"))

    # Verificar se já existe
    existing = db.query(Word).filter(Word.english == payload["english"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="Palavra já existe")

    new_word = Word(**payload)
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    return new_word


@router.patch("/words/{word_id}", response_model=WordResponse)
async def update_word(
    word_id: int,
    word_data: WordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atualizar uma palavra existente"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Palavra não encontrada")

    update_data = word_data.model_dump(exclude_unset=True)
    if "english" in update_data:
        update_data["english"] = sanitize_unmatched_brackets(update_data.get("english"))
    if "portuguese" in update_data:
        update_data["portuguese"] = sanitize_unmatched_brackets(update_data.get("portuguese"))
    for field, value in update_data.items():
        setattr(word, field, value)

    db.commit()
    db.refresh(word)
    return word


@router.post("/words/{word_id}/ai-fill", response_model=WordResponse)
async def ai_fill_word(
    word_id: int,
    payload: WordAIFillRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Preenche campos faltantes de uma palavra usando IA/APIs de dicionário."""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Palavra não encontrada")

    fields = set(payload.fields or [
        "portuguese",
        "word_type",
        "definition_en",
        "definition_pt",
        "example_en",
        "example_pt",
        "ipa",
        "synonyms",
        "antonyms",
    ])
    overwrite = bool(payload.overwrite)

    def _is_empty(value: Optional[str]) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    def _should_fill(field_name: str) -> bool:
        if overwrite:
            return True
        return _is_empty(getattr(word, field_name, None))

    updated = False
    api_data = enrich_word_from_api(word.english) or {}

    if "portuguese" in fields and _should_fill("portuguese"):
        if word.definition_en:
            translated = translate_en_to_pt_br(word.definition_en)
            if translated:
                setattr(word, "portuguese", translated)
                updated = True

    if "word_type" in fields and _should_fill("word_type"):
        value = api_data.get("word_type")
        if value:
            setattr(word, "word_type", value)
            updated = True

    if "ipa" in fields and _should_fill("ipa"):
        value = api_data.get("ipa")
        if value:
            setattr(word, "ipa", value)
            updated = True

    if "synonyms" in fields and _should_fill("synonyms"):
        value = api_data.get("synonyms")
        if value:
            setattr(word, "synonyms", value)
            updated = True

    if "antonyms" in fields and _should_fill("antonyms"):
        value = api_data.get("antonyms")
        if value:
            setattr(word, "antonyms", value)
            updated = True

    if "definition_en" in fields and _should_fill("definition_en"):
        value = api_data.get("definition_en")
        if value:
            setattr(word, "definition_en", value)
            updated = True
        elif word.definition_pt:
            translated = translate_pt_br_to_en(word.definition_pt)
            if translated:
                setattr(word, "definition_en", translated)
                updated = True

    if "definition_pt" in fields and _should_fill("definition_pt"):
        if word.definition_en:
            translated = translate_en_to_pt_br(word.definition_en)
            if translated:
                setattr(word, "definition_pt", translated)
                updated = True

    if "example_en" in fields and _should_fill("example_en"):
        examples = api_data.get("example_sentences") or []
        example_en = None
        if isinstance(examples, list) and examples:
            first = examples[0]
            if isinstance(first, dict):
                example_en = first.get("en")
            elif isinstance(first, str):
                example_en = first
        if example_en:
            setattr(word, "example_en", example_en)
            updated = True

    if "example_pt" in fields and _should_fill("example_pt"):
        if word.example_en:
            translated = translate_en_to_pt_br(word.example_en)
            if translated:
                setattr(word, "example_pt", translated)
                updated = True

    missing_fields = [f for f in fields if _should_fill(f)]

    if missing_fields:
        system_prompt = (
            "You are a bilingual lexicographer. Fill missing fields for an English word. "
            "Return ONLY valid JSON with the keys: portuguese, word_type, definition_en, definition_pt, "
            "example_en, example_pt, ipa, synonyms, antonyms. Use empty string for unknown fields."
        )
        user_prompt = {
            "english": word.english,
            "level": word.level,
            "current": {
                "portuguese": word.portuguese,
                "word_type": word.word_type,
                "definition_en": word.definition_en,
                "definition_pt": word.definition_pt,
                "example_en": word.example_en,
                "example_pt": word.example_pt,
                "ipa": word.ipa,
                "synonyms": word.synonyms,
                "antonyms": word.antonyms,
            },
            "missing_fields": missing_fields,
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ]

        try:
            ai_result = await ai_teacher_service.get_ai_response_messages_prefer_deepseek(
                messages,
                db=db,
                cache_operation="words.ai.fill",
                cache_scope="global",
            )
            ai_text = (ai_result.get("response") or "").strip()
            ai_json = None
            try:
                ai_json = json.loads(ai_text)
            except json.JSONDecodeError:
                start = ai_text.find("{")
                end = ai_text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    ai_json = json.loads(ai_text[start:end + 1])

            if isinstance(ai_json, dict):
                for key in missing_fields:
                    if key not in ai_json:
                        continue
                    value = ai_json.get(key)
                    if isinstance(value, str) and value.strip():
                        setattr(word, key, value.strip())
                        updated = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Falha ao preencher com IA: {e}")

    if updated:
        db.commit()
        db.refresh(word)

    return word


@router.delete("/words/{word_id}")
async def delete_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deletar uma palavra"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Palavra não encontrada")

    db.delete(word)
    db.commit()
    return {"message": "Palavra deletada com sucesso"}


@router.post("/words/bulk", response_model=BulkImportResponse)
async def bulk_import_words(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Importar palavras em massa via CSV

    Formato esperado:
    english,ipa,portuguese,level,word_type,definition_en,definition_pt,example_en,example_pt,tags
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Apenas arquivos CSV são aceitos")

    content = await file.read()
    csv_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_content))

    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(csv_reader, start=2):
        try:
            english = sanitize_unmatched_brackets(row.get('english', ''))
            if not english:
                errors.append(f"Linha {row_num}: campo 'english' vazio")
                continue

            # Verificar se já existe
            existing_word = db.query(Word).filter(Word.english == english).first()

            word_data = {
                'english': english,
                'ipa': row.get('ipa', '').strip() or None,
                'portuguese': sanitize_unmatched_brackets(row.get('portuguese', '')),
                'level': row.get('level', 'A1').strip(),
                'word_type': row.get('word_type', '').strip() or None,
                'definition_en': row.get('definition_en', '').strip() or None,
                'definition_pt': row.get('definition_pt', '').strip() or None,
                'example_en': row.get('example_en', '').strip() or None,
                'example_pt': row.get('example_pt', '').strip() or None,
                'tags': row.get('tags', '').strip() or None,
            }

            if existing_word:
                # Atualizar palavra existente
                for field, value in word_data.items():
                    if value is not None:  # Só atualiza se tiver valor
                        setattr(existing_word, field, value)
                updated += 1
            else:
                # Criar nova palavra
                new_word = Word(**word_data)
                db.add(new_word)
                created += 1

        except Exception as e:
            errors.append(f"Linha {row_num}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no banco: {str(e)}")

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_processed": created + updated
    }


# ============== GERENCIAMENTO DE SENTENÇAS ==============

@router.get("/sentences")
async def list_sentences_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todas as sentenças"""
    query = db.query(Sentence)

    if search:
        query = query.filter(
            (Sentence.english.ilike(f"%{search}%")) |
            (Sentence.portuguese.ilike(f"%{search}%"))
        )

    if level:
        query = query.filter(Sentence.level == level)

    total = query.count()
    sentences = query.order_by(Sentence.id).offset((page - 1) * per_page).limit(per_page).all()

    import math
    return {
        "items": sentences,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 1
    }


@router.get("/sentences/export")
async def export_sentences_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exportar sentenças em CSV"""
    sentences = db.query(Sentence).order_by(Sentence.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "english",
        "portuguese",
        "level",
        "category",
        "grammar_points",
    ])

    for s in sentences:
        writer.writerow([
            s.id,
            s.english,
            s.portuguese,
            s.level,
            s.category or "",
            s.grammar_points or "",
        ])

    filename = f"sentences_export_{datetime.now(timezone.utc).date().isoformat()}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/sentences", response_model=SentenceResponse, status_code=status.HTTP_201_CREATED)
async def create_sentence(
    sentence: SentenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Criar uma nova sentença"""
    new_sentence = Sentence(**sentence.model_dump())
    db.add(new_sentence)
    db.commit()
    db.refresh(new_sentence)
    return new_sentence


@router.patch("/sentences/{sentence_id}", response_model=SentenceResponse)
async def update_sentence(
    sentence_id: int,
    sentence_data: SentenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atualizar uma sentença"""
    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentença não encontrada")

    update_data = sentence_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sentence, field, value)

    db.commit()
    db.refresh(sentence)
    return sentence


@router.delete("/sentences/{sentence_id}")
async def delete_sentence(
    sentence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deletar uma sentença"""
    sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentença não encontrada")

    db.delete(sentence)
    db.commit()
    return {"message": "Sentença deletada com sucesso"}


@router.post("/sentences/bulk", response_model=BulkImportResponse)
async def bulk_import_sentences(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Importar sentenças em massa via CSV

    Formato: english,portuguese,level,category,grammar_points
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Apenas arquivos CSV são aceitos")

    content = await file.read()
    csv_content = content.decode('utf-8')
    csv_reader = csv.DictReader(io.StringIO(csv_content))

    created = 0
    errors = []

    for row_num, row in enumerate(csv_reader, start=2):
        try:
            english = row.get('english', '').strip()
            portuguese = row.get('portuguese', '').strip()

            if not english or not portuguese:
                errors.append(f"Linha {row_num}: campos obrigatórios vazios")
                continue

            sentence_data = {
                'english': english,
                'portuguese': portuguese,
                'level': row.get('level', 'A1').strip(),
                'category': row.get('category', '').strip() or None,
                'grammar_points': row.get('grammar_points', '').strip() or None,
            }

            new_sentence = Sentence(**sentence_data)
            db.add(new_sentence)
            created += 1

        except Exception as e:
            errors.append(f"Linha {row_num}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar: {str(e)}")

    return {
        "created": created,
        "updated": 0,
        "errors": errors,
        "total_processed": created
    }


# ============== GERENCIAMENTO DE VÍDEOS ==============

@router.get("/videos")
async def list_videos_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar todos os vídeos"""
    query = db.query(Video)
    total = query.count()
    videos = query.order_by(desc(Video.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    import math
    return {
        "items": videos,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": math.ceil(total / per_page) if total > 0 else 1
    }


@router.get("/videos/export")
async def export_videos_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Exportar vídeos em CSV"""
    videos = db.query(Video).order_by(Video.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "title",
        "description",
        "youtube_id",
        "youtube_url",
        "thumbnail_url",
        "level",
        "category",
        "tags",
        "duration",
        "views_count",
        "order_index",
        "is_active",
        "is_featured",
        "created_at",
        "updated_at",
        "published_at",
    ])

    def to_iso(dt: object) -> str:
        if dt is None:
            return ""
        if isinstance(dt, datetime):
            return dt.astimezone(timezone.utc).isoformat()
        return str(dt)

    for v in videos:
        writer.writerow([
            v.id,
            v.title,
            v.description or "",
            v.youtube_id,
            v.youtube_url,
            v.thumbnail_url,
            v.level,
            v.category,
            v.tags or "",
            v.duration or 0,
            v.views_count or 0,
            v.order_index or 0,
            bool(v.is_active),
            bool(v.is_featured),
            to_iso(v.created_at),
            to_iso(v.updated_at),
            to_iso(v.published_at),
        ])

    filename = f"videos_export_{datetime.now(timezone.utc).date().isoformat()}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def create_video(
    video: VideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Adicionar novo vídeo"""
    new_video = Video(**video.model_dump())
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    return new_video


@router.patch("/videos/{video_id}", response_model=VideoResponse)
async def update_video(
    video_id: int,
    video_data: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atualizar vídeo"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    update_data = video_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(video, field, value)

    db.commit()
    db.refresh(video)
    return video


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deletar vídeo"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    db.delete(video)
    db.commit()
    return {"message": "Vídeo deletado com sucesso"}


# ============== GERENCIAMENTO DE TEXTOS (LEITURA & ESCRITA) ==============

@router.get("/texts", response_model=List[StudyTextAdminListItem])
async def list_texts_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Listar textos de estudo"""
    query = db.query(StudyText)

    if search:
        query = query.filter(
            (StudyText.title.ilike(f"%{search}%")) |
            (StudyText.content_en.ilike(f"%{search}%"))
        )

    if level:
        query = query.filter(StudyText.level == level)

    texts = (
        query.order_by(desc(StudyText.updated_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return texts


@router.get("/texts/{text_id}", response_model=StudyTextAdminResponse)
async def get_text_admin(
    text_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Obter detalhes de um texto"""
    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")
    return text


@router.post("/texts", response_model=StudyTextAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_text_admin(
    payload: StudyTextAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Criar um texto de estudo"""
    new_text = StudyText(**payload.model_dump())
    db.add(new_text)
    db.commit()
    db.refresh(new_text)
    return new_text


@router.patch("/texts/{text_id}", response_model=StudyTextAdminResponse)
async def update_text_admin(
    text_id: int,
    payload: StudyTextAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Atualizar um texto de estudo"""
    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(text, field, value)

    db.commit()
    db.refresh(text)
    return text


@router.delete("/texts/{text_id}")
async def delete_text_admin(
    text_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Deletar texto"""
    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    db.delete(text)
    db.commit()
    return {"message": "Texto deletado com sucesso"}


@router.post("/texts/{text_id}/generate-audio", response_model=StudyTextAdminResponse)
async def generate_text_audio_admin(
    text_id: int,
    voice: str = Query("nova"),
    speed: float | None = Query(None, ge=0.65, le=1.05),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Gera áudio (TTS) do conteúdo EN do texto e salva em /static/texts."""

    text = db.query(StudyText).filter(StudyText.id == text_id).first()
    if not text:
        raise HTTPException(status_code=404, detail="Texto não encontrado")

    content = (text.content_en or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Texto (EN) vazio")

    # Limite atual do OpenAI TTS (o serviço trunca, mas aqui preferimos falhar para evitar áudio parcial)
    if len(content) > 4096:
        raise HTTPException(
            status_code=400,
            detail="Texto muito longo para gerar áudio de uma vez (limite ~4096 caracteres). Divida em partes menores.",
        )

    try:
        audio_bytes = await ai_teacher_service.generate_speech(
            content,
            voice=voice,
            speed=speed,
            db=db,
            cache_operation="texts.ai.tts",
            cache_scope="global",
        )
    except Exception as e:
        msg = str(e)
        if "TTS requer OpenAI API Key" in msg or "OpenAI API Key" in msg:
            raise HTTPException(
                status_code=503,
                detail="Text-to-Speech não disponível. Configure OPENAI_API_KEY para gerar áudio.",
            )
        raise HTTPException(status_code=500, detail=f"Erro ao gerar áudio: {msg}")

    # Nome determinístico para reaproveitar áudio quando o texto não muda
    speed_for_hash = ai_teacher_service._normalize_tts_speed(speed, default=ai_teacher_service.tts_speed)
    sha = hashlib.sha256(f"{voice}|{speed_for_hash}|{content}".encode("utf-8")).hexdigest()[:16]
    filename = f"text_{text_id}_{sha}.mp3"

    # /app/app/routes -> /app/static/texts (mesmo diretório montado em /static no FastAPI)
    static_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "static", "texts")
    )
    os.makedirs(static_dir, exist_ok=True)
    out_path = os.path.join(static_dir, filename)

    try:
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de áudio: {str(e)}")

    setattr(text, "audio_url", f"/static/texts/{filename}")
    db.commit()
    db.refresh(text)
    return text


# ============== LIMPEZA E MANUTENÇÃO ==============

@router.delete("/cleanup/orphaned-progress")
async def cleanup_orphaned_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Remove progresso de palavras que não existem mais"""
    deleted = db.query(UserProgress).filter(
        ~UserProgress.word_id.in_(db.query(Word.id))
    ).delete(synchronize_session=False)

    db.commit()
    return {"message": f"{deleted} registros órfãos removidos"}


@router.delete("/cleanup/old-reviews")
async def cleanup_old_reviews(
    days: int = Query(365, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Remove reviews antigas (mais de X dias)"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = db.query(Review).filter(Review.reviewed_at < cutoff_date).delete()

    db.commit()
    return {"message": f"{deleted} reviews antigas removidas"}
