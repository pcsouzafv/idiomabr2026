from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.word import Word
from app.models.progress import UserProgress
from app.schemas.word import WordResponse, WordCreate, WordListResponse, WordWithProgress
from app.services.word_examples import get_best_word_example

router = APIRouter(prefix="/api/words", tags=["Words"])


@router.get("", response_model=WordListResponse)
def get_words(
    search: Optional[str] = Query(None, description="Busca por palavra em inglês ou português"),
    level: Optional[str] = Query(None, description="Filtrar por nível (A1, A2, B1, etc)"),
    tags: Optional[str] = Query(None, description="Filtrar por tags (separadas por vírgula)"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Listar palavras com busca e filtros"""
    query = db.query(Word)
    
    # Filtros
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Word.english.ilike(search_term),
                Word.portuguese.ilike(search_term)
            )
        )
    
    if level:
        query = query.filter(Word.level == level)
    
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        for tag in tag_list:
            query = query.filter(Word.tags.ilike(f"%{tag}%"))
    
    # Contagem total
    total = query.count()
    
    # Paginação
    words = query.offset((page - 1) * per_page).limit(per_page).all()

    # Converter para WordResponse
    word_responses = [WordResponse.model_validate(w) for w in words]

    return WordListResponse(
        words=word_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/{word_id}", response_model=WordWithProgress)
def get_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter detalhes de uma palavra com progresso do usuário"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Palavra não encontrada")
    
    # Buscar progresso do usuário
    progress = db.query(UserProgress).filter(
        UserProgress.user_id == current_user.id,
        UserProgress.word_id == word_id
    ).first()
    
    word_data = WordWithProgress(
        id=word.id,
        english=word.english,
        ipa=word.ipa,
        portuguese=word.portuguese,
        level=word.level,

        # Informações gramaticais e semânticas
        word_type=word.word_type,
        definition_en=word.definition_en,
        definition_pt=word.definition_pt,
        synonyms=word.synonyms,
        antonyms=word.antonyms,

        # Exemplos e uso
        example_en=word.example_en,
        example_pt=word.example_pt,
        example_sentences=word.example_sentences,
        usage_notes=word.usage_notes,
        collocations=word.collocations,

        # Categorização
        tags=word.tags,
        audio_url=word.audio_url,

        # Progresso
        is_learned=progress is not None and progress.repetitions >= 3,
        next_review=progress.next_review.isoformat() if progress and progress.next_review else None,
        total_reviews=progress.total_reviews if progress else 0,
        correct_count=progress.correct_count if progress else 0,
    )
    
    return word_data


@router.post("", response_model=WordResponse)
def create_word(
    word_data: WordCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Criar nova palavra (para importação)"""
    word = Word(**word_data.model_dump())
    db.add(word)
    db.commit()
    db.refresh(word)
    return word


@router.post("/bulk", response_model=dict)
def create_words_bulk(
    words: List[WordCreate],
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Importar múltiplas palavras de uma vez"""
    created = 0
    skipped = 0
    
    for word_data in words:
        # Verificar se já existe
        existing = db.query(Word).filter(Word.english == word_data.english).first()
        if existing:
            skipped += 1
            continue
        
        word = Word(**word_data.model_dump())
        db.add(word)
        created += 1
    
    db.commit()
    
    return {
        "created": created,
        "skipped": skipped,
        "total": len(words)
    }


@router.get("/levels/list", response_model=List[str])
def get_levels(db: Session = Depends(get_db)):
    """Listar todos os níveis disponíveis"""
    levels = db.query(Word.level).distinct().all()
    return [l[0] for l in levels if l[0]]


@router.get("/tags/list", response_model=List[str])
def get_tags(db: Session = Depends(get_db)):
    """Listar todas as tags disponíveis"""
    words_with_tags = db.query(Word.tags).filter(Word.tags.isnot(None)).all()
    all_tags = set()
    for (tags,) in words_with_tags:
        if tags:
            for tag in tags.split(","):
                all_tags.add(tag.strip())
    return sorted(list(all_tags))


@router.post("/{word_id}/generate-example", response_model=dict)
async def generate_word_example(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera exemplo de frase para uma palavra"""
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Palavra não encontrada")

    # Gera exemplo (IA com cache; fallback legado se necessário)
    example_en, example_pt = await get_best_word_example(word, db)

    # Atualiza palavra no banco
    if example_en and example_pt:
        word.example_en = example_en  # type: ignore[assignment]
        word.example_pt = example_pt  # type: ignore[assignment]
        db.commit()

    return {
        "word_id": word_id,
        "example_en": example_en,
        "example_pt": example_pt
    }
