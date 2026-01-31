#!/usr/bin/env python3
"""Adiciona/atualiza verbos modais no banco, já com enriquecimento.

Objetivo
- Garantir que os principais verbos modais existam em `words`.
- Preencher campos ricos (definition_en/pt, exemplos, usage_notes, collocations, etc.).
- Operação segura: NÃO remove nada; faz upsert e só completa campos vazios.

Uso
- Local (usando DATABASE_URL/.env):
  python backend/scripts/add_modal_verbs.py

- Com Docker Compose:
  docker-compose exec backend python scripts/add_modal_verbs.py

Flags
- --dry-run: não faz commit
- --no-dictionary: não consulta APIs de dicionário para completar IPA/áudio/sinônimos
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.word import Word

try:
    from services.dictionary_api import enrich_word_from_api
except Exception:
    enrich_word_from_api = None  # type: ignore


def _is_blank(value: Optional[str]) -> bool:
    return value is None or str(value).strip() == ""


def _merge_csv_tags(existing: Optional[str], to_add: Iterable[str]) -> str:
    existing_set = {t.strip() for t in (existing or "").split(",") if t.strip()}
    add_set = {t.strip() for t in to_add if t.strip()}
    merged = sorted(existing_set | add_set)
    return ",".join(merged)


def _remove_csv_tag(existing: Optional[str], tag_to_remove: str) -> str:
    tags = [t.strip() for t in (existing or "").split(",") if t.strip()]
    filtered = [t for t in tags if t.lower() != tag_to_remove.lower()]
    return ",".join(filtered)


def _is_complete_for_enrichment(word: Word) -> bool:
    # Keep aligned with backend/scripts/update_words_from_csv.py
    return (
        not _is_blank(word.ipa)
        and not _is_blank(word.word_type)
        and not _is_blank(word.definition_en)
        and not _is_blank(word.definition_pt)
        and not _is_blank(word.example_en)
        and not _is_blank(word.example_pt)
    )


@dataclass(frozen=True)
class ModalEntry:
    english: str
    portuguese: str
    level: str
    word_type: str
    definition_en: str
    definition_pt: str
    synonyms: str
    antonyms: str
    example_sentences: list[dict[str, str]]
    usage_notes: str
    collocations: list[str]
    tags: list[str]


MODALS: list[ModalEntry] = [
    ModalEntry(
        english="can",
        portuguese="poder / conseguir",
        level="A1",
        word_type="modal verb",
        definition_en="Used to say someone is able to do something, or that something is possible.",
        definition_pt="Usado para dizer que alguém consegue fazer algo ou que algo é possível.",
        synonyms="be able to, be allowed to",
        antonyms="be unable to",
        example_sentences=[
            {"en": "I can swim.", "pt": "Eu sei nadar."},
            {"en": "Can you help me?", "pt": "Você pode me ajudar?"},
            {"en": "It can be dangerous.", "pt": "Pode ser perigoso."},
        ],
        usage_notes=(
            "Use 'can' for ability (I can...), permission (Can I...?), and possibility (It can...). "
            "Negative: can't / cannot. Questions: Can you...?, Can I...?"
        ),
        collocations=["can you", "can I", "can't wait", "can be"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="could",
        portuguese="poderia / conseguia / pôde",
        level="A2",
        word_type="modal verb",
        definition_en="Past form of 'can', also used to make polite requests or talk about possibilities.",
        definition_pt="Passado de 'can' e também usado para pedidos educados ou possibilidades.",
        synonyms="was able to, might",
        antonyms="couldn't",
        example_sentences=[
            {"en": "I could run fast when I was a kid.", "pt": "Eu conseguia correr rápido quando era criança."},
            {"en": "Could you open the window?", "pt": "Você poderia abrir a janela?"},
            {"en": "It could rain later.", "pt": "Pode chover mais tarde."},
        ],
        usage_notes=(
            "Use 'could' as the past of 'can' (ability), for polite requests (Could you...?), "
            "and for possibility (It could...). Negative: couldn't."
        ),
        collocations=["could you", "could I", "could be", "could have"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="may",
        portuguese="poder (formal) / talvez",
        level="B1",
        word_type="modal verb",
        definition_en="Used for polite permission requests and to say something is possible.",
        definition_pt="Usado para pedir permissão de forma educada e para dizer que algo é possível.",
        synonyms="might",
        antonyms="may not",
        example_sentences=[
            {"en": "May I come in?", "pt": "Posso entrar?"},
            {"en": "You may leave now.", "pt": "Você pode sair agora."},
            {"en": "It may take a few minutes.", "pt": "Pode levar alguns minutos."},
        ],
        usage_notes=(
            "Use 'may' for formal permission (May I...?) and possibility (It may...). "
            "In modern English, 'can' is more common for permission in informal contexts."
        ),
        collocations=["may I", "may be", "may not", "may have"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="might",
        portuguese="talvez / poderia",
        level="B1",
        word_type="modal verb",
        definition_en="Used to say something is possible but not certain.",
        definition_pt="Usado para dizer que algo é possível, mas não certo.",
        synonyms="may",
        antonyms="definitely will",
        example_sentences=[
            {"en": "I might go out tonight.", "pt": "Talvez eu saia hoje à noite."},
            {"en": "It might be true.", "pt": "Pode ser verdade."},
            {"en": "You might want to rest.", "pt": "Talvez seja melhor você descansar."},
        ],
        usage_notes=(
            "Use 'might' for weak possibility (less certain than 'may') and soft suggestions (You might want to...)."
        ),
        collocations=["might be", "might have", "might want to"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="must",
        portuguese="dever / precisar",
        level="A2",
        word_type="modal verb",
        definition_en="Used to say something is necessary or to give a strong order; also used for strong conclusions.",
        definition_pt="Usado para dizer que algo é necessário ou para dar uma ordem forte; também para deduções.",
        synonyms="have to, need to",
        antonyms="mustn't / don't have to",
        example_sentences=[
            {"en": "You must wear a seatbelt.", "pt": "Você deve usar cinto de segurança."},
            {"en": "I must finish this today.", "pt": "Eu preciso terminar isso hoje."},
            {"en": "She must be tired.", "pt": "Ela deve estar cansada."},
        ],
        usage_notes=(
            "Use 'must' for obligation (You must...) and strong deduction (She must be...). "
            "Careful: 'mustn't' means prohibited, while 'don't have to' means not necessary."
        ),
        collocations=["must be", "must have", "must do"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="shall",
        portuguese="dever (formal) / vamos (proposta)",
        level="B2",
        word_type="modal verb",
        definition_en="Used mostly in formal English to talk about the future or to make suggestions/questions.",
        definition_pt="Usado principalmente em inglês formal para falar do futuro ou fazer sugestões/perguntas.",
        synonyms="will (formal), should (in questions)",
        antonyms="shan't",
        example_sentences=[
            {"en": "Shall we start?", "pt": "Vamos começar?"},
            {"en": "Shall I open the door?", "pt": "Quer que eu abra a porta?"},
            {"en": "We shall overcome.", "pt": "Nós vamos superar."},
        ],
        usage_notes=(
            "'Shall' is common in questions for offers/suggestions (Shall we...?, Shall I...?) and in very formal writing."
        ),
        collocations=["shall we", "shall I", "we shall"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="should",
        portuguese="deveria",
        level="A2",
        word_type="modal verb",
        definition_en="Used to give advice, make recommendations, or talk about what is expected.",
        definition_pt="Usado para dar conselhos, recomendações ou falar do que é esperado.",
        synonyms="ought to",
        antonyms="shouldn't",
        example_sentences=[
            {"en": "You should drink more water.", "pt": "Você deveria beber mais água."},
            {"en": "I should call my mom.", "pt": "Eu deveria ligar para minha mãe."},
            {"en": "It should be easy.", "pt": "Deve ser fácil."},
        ],
        usage_notes=(
            "Use 'should' for advice (You should...), expectations (It should...), and mild obligation. Negative: shouldn't."
        ),
        collocations=["should be", "should have", "should do"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="will",
        portuguese="vai / irá",
        level="A1",
        word_type="modal verb",
        definition_en="Used to talk about the future, decisions, promises, and willingness.",
        definition_pt="Usado para falar do futuro, decisões, promessas e disposição.",
        synonyms="be going to",
        antonyms="won't",
        example_sentences=[
            {"en": "I will call you tomorrow.", "pt": "Eu vou te ligar amanhã."},
            {"en": "It will be okay.", "pt": "Vai ficar tudo bem."},
            {"en": "Will you help me?", "pt": "Você vai me ajudar?"},
        ],
        usage_notes=(
            "Use 'will' for future (I will...), promises (I will do it), offers/requests (Will you...?), and willingness."
        ),
        collocations=["will be", "will do", "will you"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="would",
        portuguese="iria / gostaria / poderia",
        level="B1",
        word_type="modal verb",
        definition_en="Used for polite requests, hypothetical situations, and habits in the past.",
        definition_pt="Usado para pedidos educados, situações hipotéticas e hábitos no passado.",
        synonyms="could (polite), used to",
        antonyms="wouldn't",
        example_sentences=[
            {"en": "Would you like some coffee?", "pt": "Você gostaria de um café?"},
            {"en": "I would travel more if I had time.", "pt": "Eu viajaria mais se tivesse tempo."},
            {"en": "When I was a kid, I would play outside.", "pt": "Quando eu era criança, eu costumava brincar lá fora."},
        ],
        usage_notes=(
            "Use 'would' for polite offers/requests (Would you...?), conditionals (I would... if...), and past habits (would + verb)."
        ),
        collocations=["would you", "would like", "would be"],
        tags=["grammar", "modal", "verb"],
    ),
    ModalEntry(
        english="ought",
        portuguese="deveria",
        level="B2",
        word_type="modal verb",
        definition_en="Used to say what is the right thing to do; similar to 'should'.",
        definition_pt="Usado para dizer o que é certo fazer; parecido com 'should'.",
        synonyms="should",
        antonyms="oughtn't",
        example_sentences=[
            {"en": "You ought to see a doctor.", "pt": "Você deveria ver um médico."},
            {"en": "We ought to be careful.", "pt": "Nós deveríamos ter cuidado."},
            {"en": "I ought to apologize.", "pt": "Eu deveria me desculpar."},
        ],
        usage_notes=(
            "'Ought (to)' is less common in everyday speech than 'should'. It often expresses advice or moral obligation."
        ),
        collocations=["ought to", "ought to be"],
        tags=["grammar", "modal", "verb"],
    ),
]


def _apply_entry_fields(word: Word, entry: ModalEntry) -> tuple[bool, bool]:
    """Returns (created, updated_any_field)."""

    created = False
    updated = False

    if word.id is None:
        created = True

    # Required-ish fields
    if _is_blank(word.portuguese):
        word.portuguese = entry.portuguese
        updated = True

    if _is_blank(word.level):
        word.level = entry.level
        updated = True

    # Enriched fields (only fill blanks)
    if _is_blank(word.word_type):
        word.word_type = entry.word_type
        updated = True

    if _is_blank(word.definition_en):
        word.definition_en = entry.definition_en
        updated = True

    if _is_blank(word.definition_pt):
        word.definition_pt = entry.definition_pt
        updated = True

    if _is_blank(word.synonyms):
        word.synonyms = entry.synonyms
        updated = True

    if _is_blank(word.antonyms):
        word.antonyms = entry.antonyms
        updated = True

    if _is_blank(word.example_sentences):
        word.example_sentences = json.dumps(entry.example_sentences, ensure_ascii=False)
        updated = True

    # Keep example_en/example_pt aligned with the first example
    if _is_blank(word.example_en) and entry.example_sentences:
        word.example_en = entry.example_sentences[0].get("en")
        updated = True

    if _is_blank(word.example_pt) and entry.example_sentences:
        word.example_pt = entry.example_sentences[0].get("pt")
        updated = True

    if _is_blank(word.usage_notes):
        word.usage_notes = entry.usage_notes
        updated = True

    if _is_blank(word.collocations):
        word.collocations = json.dumps(entry.collocations, ensure_ascii=False)
        updated = True

    # Tags: merge
    merged_tags = _merge_csv_tags(word.tags, entry.tags)
    if merged_tags != (word.tags or ""):
        word.tags = merged_tags
        updated = True

    return created, updated


def _apply_dictionary_fill(word: Word) -> bool:
    """Completa alguns campos via DictionaryAPI se estiverem vazios."""

    if enrich_word_from_api is None:
        return False

    # Free Dictionary API não lida bem com frases (com espaço)
    if " " in (word.english or "").strip():
        return False

    data = enrich_word_from_api(word.english)
    if not data:
        return False

    updated = False

    if _is_blank(word.ipa) and data.get("ipa"):
        word.ipa = data.get("ipa")
        updated = True

    if _is_blank(word.audio_url) and data.get("audio_url"):
        word.audio_url = data.get("audio_url")
        updated = True

    if _is_blank(word.word_type) and data.get("word_type"):
        word.word_type = data.get("word_type")
        updated = True

    if _is_blank(word.definition_en) and data.get("definition_en"):
        word.definition_en = data.get("definition_en")
        updated = True

    if _is_blank(word.synonyms) and data.get("synonyms"):
        word.synonyms = data.get("synonyms")
        updated = True

    if _is_blank(word.antonyms) and data.get("antonyms"):
        word.antonyms = data.get("antonyms")
        updated = True

    # Collocations: store as JSON array
    collocations = data.get("collocations")
    if _is_blank(word.collocations) and collocations and isinstance(collocations, list):
        word.collocations = json.dumps(collocations, ensure_ascii=False)
        updated = True

    # Example sentences from dictionary (JSON list of {en, pt})
    examples = data.get("example_sentences")
    if _is_blank(word.example_sentences) and examples and isinstance(examples, list):
        word.example_sentences = json.dumps(examples, ensure_ascii=False)
        updated = True

        # Also set example_en/example_pt if missing
        first = examples[0] if examples else None
        if _is_blank(word.example_en) and isinstance(first, dict) and first.get("en"):
            word.example_en = first.get("en")
            updated = True

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert de verbos modais enriquecidos")
    parser.add_argument("--dry-run", action="store_true", help="Não faz commit no banco")
    parser.add_argument(
        "--no-dictionary",
        action="store_true",
        help="Não consulta DictionaryAPI para complementar IPA/áudio/sinônimos",
    )
    args = parser.parse_args()

    db: Session = SessionLocal()

    created_count = 0
    updated_count = 0
    unchanged_count = 0

    try:
        for entry in MODALS:
            english = entry.english.strip().lower()
            existing = db.query(Word).filter(Word.english.ilike(english)).first()

            if existing is None:
                word = Word(
                    english=english,
                    portuguese=entry.portuguese,
                    level=entry.level,
                )
                db.add(word)
                db.flush()  # assign id
                created = True
            else:
                word = existing
                created = False

            # Fill from curated dataset
            _created, updated_any = _apply_entry_fields(word, entry)
            created = created or _created

            # Optional: complement with DictionaryAPI
            if not args.no_dictionary:
                dict_updated = _apply_dictionary_fill(word)
                updated_any = updated_any or dict_updated

            # If now complete, remove the marker tag
            if _is_complete_for_enrichment(word) and (word.tags or ""):
                cleaned = _remove_csv_tag(word.tags, "needs_enrichment")
                if cleaned != (word.tags or ""):
                    word.tags = cleaned
                    updated_any = True

            if created:
                created_count += 1
                updated_count += 1  # created implies changes
            elif updated_any:
                updated_count += 1
            else:
                unchanged_count += 1

        if args.dry_run:
            db.rollback()
            print("\n[DRY-RUN] Nenhuma alteração foi persistida.")
        else:
            db.commit()
            print("\n✓ Commit realizado.")

        print("\n" + "=" * 50)
        print("MODAL VERBS - RESULTADO")
        print("=" * 50)
        print(f"Criados: {created_count}")
        print(f"Atualizados: {updated_count - created_count}")
        print(f"Sem mudanças: {unchanged_count}")
        print("=" * 50)

        return 0

    except Exception as e:
        db.rollback()
        print(f"\n✗ Erro: {e}")
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
