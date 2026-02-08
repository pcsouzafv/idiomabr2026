"""
Rotas para gerenciamento de vídeos
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import math

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_optional, require_admin
from app.models.user import User
from app.models.video import Video, VideoProgress, VideoLevel, VideoCategory
from app.schemas.video import (
    VideoCreate,
    VideoUpdate,
    VideoResponse,
    VideoListResponse,
    VideoProgressCreate,
    VideoProgressResponse,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])


def extract_youtube_id(url: str) -> Optional[str]:
    """Extrai ID do YouTube da URL"""
    import re
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_thumbnail_url(youtube_id: str) -> str:
    """Gera URL da thumbnail do YouTube"""
    return f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg"


# ========== ROTAS DE VÍDEOS ==========

@router.get("", response_model=VideoListResponse)
def list_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    level: Optional[VideoLevel] = None,
    category: Optional[VideoCategory] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Lista vídeos com filtros e paginação
    """
    query = db.query(Video)

    # Filtros
    if active_only:
        query = query.filter(Video.is_active == True)
    if featured_only:
        query = query.filter(Video.is_featured == True)
    if level:
        query = query.filter((Video.level == level) | (Video.level == VideoLevel.ALL))
    if category:
        query = query.filter(Video.category == category)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Video.title.ilike(search_term)) |
            (Video.description.ilike(search_term)) |
            (Video.tags.ilike(search_term))
        )

    # Ordenação
    query = query.order_by(Video.order_index.asc(), Video.created_at.desc())

    # Total
    total = query.count()

    # Paginação
    offset = (page - 1) * per_page
    videos = query.offset(offset).limit(per_page).all()

    # Adicionar progresso do usuário se autenticado
    if current_user:
        video_ids = [v.id for v in videos]
        progress_map = {}
        if video_ids:
            progresses = db.query(VideoProgress).filter(
                VideoProgress.user_id == current_user.id,
                VideoProgress.video_id.in_(video_ids)
            ).all()
            progress_map = {p.video_id: p for p in progresses}

        for video in videos:
            if video.id in progress_map:
                progress = progress_map[video.id]
                video.user_progress = progress.completion_percentage
                video.is_completed = progress.is_completed

    total_pages = math.ceil(total / per_page)

    # Converter para VideoResponse
    video_responses = [VideoResponse.model_validate(v) for v in videos]

    return VideoListResponse(
        items=video_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Obtém um vídeo específico por ID
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    # Incrementar contador de visualizações
    video.views_count += 1  # type: ignore[assignment]
    db.commit()

    # Adicionar progresso do usuário se autenticado
    if current_user:
        progress = db.query(VideoProgress).filter(
            VideoProgress.user_id == current_user.id,
            VideoProgress.video_id == video_id
        ).first()
        if progress:
            video.user_progress = progress.completion_percentage
            video.is_completed = progress.is_completed

    return video


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def create_video(
    video_data: VideoCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Cria um novo vídeo (requer autenticação)
    """
    # Extrair ID do YouTube
    youtube_id = extract_youtube_id(video_data.youtube_url)
    if not youtube_id:
        raise HTTPException(status_code=400, detail="URL do YouTube inválida")

    # Verificar se já existe
    existing = db.query(Video).filter(Video.youtube_id == youtube_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vídeo já cadastrado")

    # Criar vídeo
    video = Video(
        title=video_data.title,
        description=video_data.description,
        youtube_id=youtube_id,
        youtube_url=video_data.youtube_url,
        thumbnail_url=get_thumbnail_url(youtube_id),
        level=video_data.level,
        category=video_data.category,
        tags=video_data.tags,
        duration=video_data.duration,
        is_active=video_data.is_active,
        is_featured=video_data.is_featured,
        order_index=video_data.order_index,
    )

    db.add(video)
    db.commit()
    db.refresh(video)

    return video


@router.put("/{video_id}", response_model=VideoResponse)
def update_video(
    video_id: int,
    video_data: VideoUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Atualiza um vídeo existente (requer autenticação)
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    # Atualizar campos
    update_data = video_data.model_dump(exclude_unset=True)

    # Se URL foi alterada, atualizar youtube_id e thumbnail
    if "youtube_url" in update_data:
        youtube_id = extract_youtube_id(update_data["youtube_url"])
        if not youtube_id:
            raise HTTPException(status_code=400, detail="URL do YouTube inválida")
        update_data["youtube_id"] = youtube_id
        update_data["thumbnail_url"] = get_thumbnail_url(youtube_id)

    for field, value in update_data.items():
        setattr(video, field, value)

    db.commit()
    db.refresh(video)

    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """
    Deleta um vídeo (requer autenticação)
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    db.delete(video)
    db.commit()

    return None


# ========== ROTAS DE PROGRESSO ==========

@router.post("/progress", response_model=VideoProgressResponse, status_code=status.HTTP_201_CREATED)
def update_video_progress(
    progress_data: VideoProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualiza o progresso do usuário em um vídeo
    """
    # Verificar se vídeo existe
    video = db.query(Video).filter(Video.id == progress_data.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    # Buscar ou criar progresso
    progress = db.query(VideoProgress).filter(
        VideoProgress.user_id == current_user.id,
        VideoProgress.video_id == progress_data.video_id
    ).first()

    was_incomplete = progress is None or not progress.is_completed

    if progress:
        # Atualizar existente
        progress.watched_duration = progress_data.watched_duration  # type: ignore[assignment]
        progress.completion_percentage = progress_data.completion_percentage  # type: ignore[assignment]
        progress.last_watched_at = datetime.now(timezone.utc)  # type: ignore[assignment]

        # Marcar como completo se >= 90%
        if progress_data.completion_percentage >= 90 and not progress.is_completed:
            progress.is_completed = True  # type: ignore[assignment]
            progress.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    else:
        # Criar novo
        progress = VideoProgress(
            user_id=current_user.id,
            video_id=progress_data.video_id,
            watched_duration=progress_data.watched_duration,
            completion_percentage=progress_data.completion_percentage,
            is_completed=progress_data.completion_percentage >= 90
        )
        if progress.is_completed:
            progress.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]

        db.add(progress)

    db.commit()
    db.refresh(progress)

    # Dar XP ao usuário quando completar um vídeo pela primeira vez
    if progress.is_completed and was_incomplete:
        try:
            from app.services.achievements import award_xp
            # XP baseado na duração do vídeo
            base_xp = 20
            if video.duration:
                # Bônus por vídeos mais longos (1 XP por minuto)
                bonus_xp = min(30, video.duration // 60)
                base_xp += bonus_xp

            award_xp(db, current_user.id, base_xp)
        except Exception as e:
            # Não falhar se XP não puder ser concedido
            print(f"Erro ao conceder XP por vídeo: {e}")

    return progress


@router.get("/progress/me", response_model=list[VideoProgressResponse])
def get_my_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista o progresso do usuário em todos os vídeos
    """
    progresses = db.query(VideoProgress).filter(
        VideoProgress.user_id == current_user.id
    ).order_by(VideoProgress.last_watched_at.desc()).all()

    return progresses


@router.get("/categories/list", response_model=list[str])
def list_categories():
    """
    Lista todas as categorias disponíveis
    """
    return [cat.value for cat in VideoCategory]


@router.get("/levels/list", response_model=list[str])
def list_levels():
    """
    Lista todos os níveis disponíveis
    """
    return [level.value for level in VideoLevel]
