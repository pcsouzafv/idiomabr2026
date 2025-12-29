from pydantic import BaseModel
from typing import Optional, List


class WordBase(BaseModel):
    english: str
    ipa: Optional[str] = None
    portuguese: str
    level: str = "A1"

    # Informações gramaticais e semânticas
    word_type: Optional[str] = None
    definition_en: Optional[str] = None
    definition_pt: Optional[str] = None
    synonyms: Optional[str] = None
    antonyms: Optional[str] = None

    # Exemplos e uso
    example_en: Optional[str] = None
    example_pt: Optional[str] = None
    example_sentences: Optional[str] = None
    usage_notes: Optional[str] = None
    collocations: Optional[str] = None

    # Categorização
    tags: Optional[str] = None


class WordCreate(WordBase):
    pass


class WordResponse(WordBase):
    id: int
    audio_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class WordWithProgress(WordResponse):
    """Palavra com informações de progresso do usuário"""
    is_learned: bool = False
    next_review: Optional[str] = None
    total_reviews: int = 0
    correct_count: int = 0


class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
