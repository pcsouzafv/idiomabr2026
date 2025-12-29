from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.sentence import Sentence, UserSentenceProgress
from app.models.word import Word
from app.models.user import User
from app.models.progress import UserProgress


class RAGService:
    """
    Retrieval-Augmented Generation Service
    Busca contexto relevante do banco de dados para enriquecer as respostas da IA
    """

    @staticmethod
    async def get_sentence_context(
        db: Session,
        sentence_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """Obtém contexto completo sobre uma frase específica"""

        sentence = db.query(Sentence).filter(Sentence.id == sentence_id).first()
        if not sentence:
            return {}

        # Buscar progresso do usuário nesta frase
        progress = db.query(UserSentenceProgress).filter(
            and_(
                UserSentenceProgress.sentence_id == sentence_id,
                UserSentenceProgress.user_id == user_id
            )
        ).first()

        # Extrair vocabulário da frase
        related_vocab = await RAGService._extract_related_vocabulary(db, sentence.english)

        # Buscar estatísticas do usuário
        user_stats = await RAGService._get_user_stats(db, user_id)

        return {
            "sentence": {
                "id": sentence.id,
                "english": sentence.english,
                "portuguese": sentence.portuguese,
                "level": sentence.level,
                "category": sentence.category,
                "grammar_points": sentence.grammar_points,
                "vocabulary_used": sentence.vocabulary_used
            },
            "user_progress": {
                "easiness_factor": progress.easiness_factor if progress else 2.5,
                "repetitions": progress.repetitions if progress else 0,
                "last_reviewed": progress.last_reviewed.isoformat() if progress and progress.last_reviewed else None
            },
            "related_vocabulary": related_vocab,
            "user_stats": user_stats
        }

    @staticmethod
    async def _extract_related_vocabulary(
        db: Session,
        sentence_text: str
    ) -> List[Dict[str, Any]]:
        """Extrai palavras do banco que aparecem na frase"""

        # Tokenizar a frase (simplificado)
        words = sentence_text.lower().split()
        # Remover pontuação
        words = [word.strip('.,!?;:"()[]{}') for word in words]

        # Buscar palavras no banco
        vocabulary = db.query(Word).filter(
            func.lower(Word.english).in_(words)
        ).limit(10).all()

        return [
            {
                "id": word.id,
                "english": word.english,
                "portuguese": word.portuguese,
                "ipa": word.ipa,
                "word_type": word.word_type,
                "definition_pt": word.definition_pt
            }
            for word in vocabulary
        ]

    @staticmethod
    async def _get_user_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Obtém estatísticas do usuário para personalizar ensino"""

        # Total de palavras aprendidas
        total_words = db.query(func.count(UserProgress.id)).filter(
            and_(
                UserProgress.user_id == user_id,
                UserProgress.repetitions > 0
            )
        ).scalar() or 0

        # Nível estimado baseado em palavras aprendidas
        if total_words < 500:
            estimated_level = "A1"
        elif total_words < 1000:
            estimated_level = "A2"
        elif total_words < 1500:
            estimated_level = "B1"
        elif total_words < 2000:
            estimated_level = "B2"
        elif total_words < 2500:
            estimated_level = "C1"
        else:
            estimated_level = "C2"

        # Total de frases estudadas
        total_sentences = db.query(func.count(UserSentenceProgress.id)).filter(
            and_(
                UserSentenceProgress.user_id == user_id,
                UserSentenceProgress.repetitions > 0
            )
        ).scalar() or 0

        return {
            "total_words_learned": total_words,
            "total_sentences_studied": total_sentences,
            "estimated_level": estimated_level
        }

    @staticmethod
    async def search_similar_sentences(
        db: Session,
        query: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca frases similares baseado em query"""

        filters = []

        # Filtro por nível
        if level:
            filters.append(Sentence.level == level)

        # Filtro por categoria
        if category:
            filters.append(Sentence.category == category)

        # Busca textual simples (pode ser melhorado com FTS ou embeddings)
        search_filter = or_(
            Sentence.english.ilike(f"%{query}%"),
            Sentence.portuguese.ilike(f"%{query}%")
        )

        if filters:
            query_filter = and_(search_filter, *filters)
        else:
            query_filter = search_filter

        sentences = db.query(Sentence).filter(query_filter).limit(limit).all()

        return [
            {
                "id": sent.id,
                "english": sent.english,
                "portuguese": sent.portuguese,
                "level": sent.level,
                "category": sent.category
            }
            for sent in sentences
        ]

    @staticmethod
    async def get_grammar_context(
        db: Session,
        grammar_point: str
    ) -> List[Dict[str, Any]]:
        """Busca frases que contêm um ponto gramatical específico"""

        sentences = db.query(Sentence).filter(
            Sentence.grammar_points.ilike(f"%{grammar_point}%")
        ).limit(10).all()

        return [
            {
                "id": sent.id,
                "english": sent.english,
                "portuguese": sent.portuguese,
                "level": sent.level,
                "grammar_points": sent.grammar_points
            }
            for sent in sentences
        ]

    @staticmethod
    async def get_learning_recommendations(
        db: Session,
        user_id: int,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Recomenda próximas frases para estudar baseado no progresso do usuário"""

        # Obter nível estimado do usuário
        user_stats = await RAGService._get_user_stats(db, user_id)
        estimated_level = user_stats["estimated_level"]

        # Buscar frases não estudadas do nível apropriado
        studied_sentence_ids = db.query(UserSentenceProgress.sentence_id).filter(
            UserSentenceProgress.user_id == user_id
        ).all()
        studied_ids = [sid[0] for sid in studied_sentence_ids]

        # Frases recomendadas
        recommended = db.query(Sentence).filter(
            and_(
                Sentence.level == estimated_level,
                ~Sentence.id.in_(studied_ids) if studied_ids else True
            )
        ).order_by(Sentence.difficulty_score).limit(limit).all()

        return {
            "user_level": estimated_level,
            "recommended_sentences": [
                {
                    "id": sent.id,
                    "english": sent.english,
                    "portuguese": sent.portuguese,
                    "level": sent.level,
                    "category": sent.category,
                    "difficulty_score": sent.difficulty_score
                }
                for sent in recommended
            ]
        }


# Singleton instance
rag_service = RAGService()
