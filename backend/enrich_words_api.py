"""
Script de enriquecimento em massa usando APIs de dicionário.

Este script busca automaticamente definições, sinônimos, exemplos e outras
informações para todas as palavras do banco de dados.

Usa:
- Free Dictionary API (gratuita, sem limite)
- Datamuse API (gratuita, para sinônimos e colocações)
"""

import json
import hashlib
import asyncio
import os
import sys
import re
import traceback
import urllib.parse
from time import sleep
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import requests

from typing import Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.word import Word
from services.dictionary_api import enrich_word_from_api


_HAS_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")
_HEADWORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")


_OPENAI_CLIENT: Optional["OpenAI"] = None
_DEEPSEEK_CLIENT: Optional["OpenAI"] = None


def _words_static_dir() -> str:
    # This script lives in backend/. Static is backend/static (mounted at /static by FastAPI).
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "words"))


def _word_tts_filename(*, word_id: int, english: str, voice: str) -> str:
    sha = hashlib.sha256(f"{voice}|{(english or '').strip()}".encode("utf-8")).hexdigest()[:16]
    return f"word_{word_id}_{sha}.mp3"


def maybe_generate_word_tts_audio_url(
    db: Session,
    word: Word,
    *,
    voice: str = "nova",
    force: bool = False,
) -> Optional[str]:
    """Generate and persist a local /static/words/*.mp3 for a Word.

    Returns the audio_url to store ("/static/words/<file>") or None.
    """

    english = (word.english or "").strip()
    if not english:
        return None

    if not force and (word.audio_url or "").strip():
        return None

    static_dir = _words_static_dir()
    os.makedirs(static_dir, exist_ok=True)

    filename = _word_tts_filename(word_id=int(word.id), english=english, voice=voice)
    out_path = os.path.join(static_dir, filename)

    # If file already exists, just point audio_url to it.
    if os.path.isfile(out_path):
        return f"/static/words/{filename}"

    try:
        from app.services.ai_teacher import ai_teacher_service
    except Exception as e:
        print(f"[WARN] Não foi possível importar ai_teacher_service (TTS): {e}")
        return None

    try:
        audio_bytes = asyncio.run(
            ai_teacher_service.generate_speech(
                english,
                voice=voice,
                db=db,
                cache_operation="words.ai.tts",
                cache_scope="global",
            )
        )
    except Exception as e:
        msg = str(e)
        if "TTS requer OpenAI API Key" in msg or "OpenAI API Key" in msg:
            print("[TTS] indisponível (OPENAI_API_KEY não configurada)")
            return None
        print(f"[TTS ERROR] Falha ao gerar áudio para '{english}': {msg}")
        return None

    try:
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
    except Exception as e:
        print(f"[TTS ERROR] Falha ao salvar arquivo '{out_path}': {e}")
        return None

    return f"/static/words/{filename}"


def _get_openai_client() -> Optional["OpenAI"]:
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is not None:
        return _OPENAI_CLIENT

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not OpenAI:
        _OPENAI_CLIENT = None
        return None

    _OPENAI_CLIENT = OpenAI(api_key=api_key)
    return _OPENAI_CLIENT


def _get_deepseek_client() -> Optional["OpenAI"]:
    global _DEEPSEEK_CLIENT
    if _DEEPSEEK_CLIENT is not None:
        return _DEEPSEEK_CLIENT

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or not OpenAI:
        _DEEPSEEK_CLIENT = None
        return None

    _DEEPSEEK_CLIENT = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return _DEEPSEEK_CLIENT


def translate_en_to_pt_br(text: str) -> Optional[str]:
    """Tradução EN -> pt-BR.

    Preferência:
    1) LLM (OpenAI/DeepSeek) se chaves estiverem configuradas.
    2) MyMemory (gratuito) como fallback.

    Retorna None se não conseguir traduzir.
    """

    src = (text or "").strip()
    if not src:
        return None

    # Prefer OpenAI, fallback DeepSeek.
    client = _get_openai_client()
    model = os.getenv("OPENAI_TRANSLATE_MODEL", "gpt-4o-mini")
    provider = "openai"
    if client is None:
        client = _get_deepseek_client()
        model = os.getenv("DEEPSEEK_TRANSLATE_MODEL", "deepseek-chat")
        provider = "deepseek"

    if client is None:
        return _translate_en_to_pt_mymemory(src)

    system_prompt = (
        "You translate English to Brazilian Portuguese (pt-BR). "
        "Return ONLY the translated text (no quotes, no markdown, no explanations)."
    )
    user_prompt = src

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        out = (resp.choices[0].message.content or "").strip()
        # Defensive cleanup: strip quotes if model adds them.
        out = out.strip().strip('"').strip("'").strip()
        if not out:
            return None
        if out.lower() == src.lower():
            # If translation equals source, treat as failure.
            return None
        return out
    except Exception as e:
        print(f"[WARN] Translation failed ({provider}): {e}")
        return _translate_en_to_pt_mymemory(src)


def _translate_en_to_pt_mymemory(text: str) -> Optional[str]:
    """Fallback EN->pt-BR via MyMemory (sem chave).

    Evita retornar o próprio texto de entrada e aplica timeouts curtos.
    """

    src = (text or "").strip()
    if not src:
        return None


def translate_pt_br_to_en(text: str) -> Optional[str]:
    """Tradução pt-BR -> EN.

    Preferência:
    1) LLM (OpenAI/DeepSeek) se chaves estiverem configuradas.
    2) MyMemory (gratuito) como fallback.
    """

    src = (text or "").strip()
    if not src:
        return None

    client = _get_openai_client()
    model = os.getenv("OPENAI_TRANSLATE_MODEL", "gpt-4o-mini")
    provider = "openai"
    if client is None:
        client = _get_deepseek_client()
        model = os.getenv("DEEPSEEK_TRANSLATE_MODEL", "deepseek-chat")
        provider = "deepseek"

    if client is None:
        return _translate_pt_to_en_mymemory(src)

    system_prompt = (
        "You translate Brazilian Portuguese (pt-BR) to English. "
        "Return ONLY the translated text (no quotes, no markdown, no explanations)."
    )
    user_prompt = src

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        out = (resp.choices[0].message.content or "").strip()
        out = out.strip().strip('"').strip("'").strip()
        if not out:
            return None
        if out.lower() == src.lower():
            return None
        return out
    except Exception as e:
        print(f"[WARN] Translation failed ({provider}): {e}")
        return _translate_pt_to_en_mymemory(src)


def _translate_pt_to_en_mymemory(text: str) -> Optional[str]:
    src = (text or "").strip()
    if not src:
        return None

    url = (
        "https://api.mymemory.translated.net/get?"
        + "q="
        + urllib.parse.quote(src)
        + "&langpair=pt-br|en"
    )

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        translated = (
            ((data or {}).get("responseData") or {}).get("translatedText") or ""
        ).strip()
        translated = translated.strip().strip('"').strip("'").strip()
        if not translated:
            return None
        if translated.lower() == src.lower():
            return None
        return translated
    except Exception:
        return None


def detect_word_type_simple(word: str) -> Optional[str]:
    """Heurística simples para preencher word_type quando API falha."""
    w = (word or "").strip().lower()
    if not w:
        return None

    if w.endswith(("ing", "ed", "ate", "ize", "ify", "en")):
        return "verb"
    if w.endswith("ly"):
        return "adverb"
    if w.endswith(("tion", "sion", "ness", "ment", "ity", "er", "or", "ism", "ist", "ance", "ence")):
        return "noun"
    if w.endswith(("ful", "less", "ous", "ious", "ive", "able", "ible", "al", "ic", "ical")):
        return "adjective"

    # Nacionalidades/demônimos e adjetivos comuns
    if w.endswith(("ian", "ean", "ese")):
        return "adjective"

    return None

    # Endpoint público e simples
    url = (
        "https://api.mymemory.translated.net/get?"
        + "q="
        + urllib.parse.quote(src)
        + "&langpair=en|pt-br"
    )

    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        translated = (
            ((data or {}).get("responseData") or {}).get("translatedText") or ""
        ).strip()
        translated = translated.strip().strip('"').strip("'").strip()
        if not translated:
            return None
        if translated.lower() == src.lower():
            return None
        return translated
    except Exception:
        return None


def is_headword_candidate_for_english_dictionary(text: str) -> bool:
    """Heurística conservadora para evitar chamadas inúteis à Free Dictionary API."""
    if not text:
        return False
    t = text.strip()
    if not t:
        return False

    # Free Dictionary API trabalha bem com headwords simples; frases tendem a falhar.
    if re.search(r"\s", t):
        return False

    # Evita textos em PT com diacríticos / notas.
    if _HAS_NON_ASCII_RE.search(t):
        return False

    # Muito longo geralmente é nota ou frase colada.
    if len(t) > 60:
        return False

    # Evita tokens com parênteses, barras, pontuação etc (tendem a dar 404).
    if not _HEADWORD_TOKEN_RE.match(t):
        return False

    return True


def is_probably_rotated_import_row(word: Word) -> bool:
    """Detecta registros onde 'ipa' parece headword e 'portuguese' parece IPA.

    Esses registros normalmente vêm de importação com colunas deslocadas ou duplicatas.
    Melhor pular no enriquecimento (para não gerar 404) e tratar via scripts de correção.
    """

    ipa = (word.ipa or "").strip()
    pt = (word.portuguese or "").strip()
    if not ipa or not pt:
        return False

    # 'ipa' com headword ASCII e 'portuguese' com caracteres IPA é um sinal forte.
    if _HEADWORD_TOKEN_RE.match(ipa) and _HAS_NON_ASCII_RE.search(pt):
        return True

    return False


def enrich_all_words(
    db: Session,
    limit: int = None,
    skip_existing: bool = True,
    delay: float = 0.3,
    commit_every: int = 50,
    min_id: int | None = None,
    max_id: int | None = None,
    tts_missing_audio: bool = False,
    tts_voice: str = "nova",
    tts_delay: float = 0.0,
    only_audio: bool = False,
    include_examples: bool = False,
):
    """
    Enriquece todas as palavras do banco usando APIs.

    Args:
        db: Sessão do banco de dados
        limit: Limite de palavras a processar (None = todas)
        skip_existing: Se True, pula palavras já enriquecidas
        delay: Delay entre requisições (rate limiting)
    """
    print("🚀 Iniciando enriquecimento via API...\n")

    # Construir query
    query = db.query(Word)

    if min_id is not None:
        query = query.filter(Word.id >= min_id)
    if max_id is not None:
        query = query.filter(Word.id <= max_id)

    if only_audio:
        query = query.filter((Word.audio_url == None) | (Word.audio_url == ""))
    elif skip_existing:
        # Pular palavras que já têm todos os campos de enriquecimento preenchidos.
        # Importante: mesmo que já tenha definição, pode estar faltando exemplos,
        # colocações, notas de uso, etc.
        missing_filters = [
            (Word.word_type == None) | (Word.word_type == ""),
            (Word.definition_en == None) | (Word.definition_en == ""),
            (Word.synonyms == None) | (Word.synonyms == ""),
            (Word.antonyms == None) | (Word.antonyms == ""),
            (Word.collocations == None) | (Word.collocations == ""),
            (Word.usage_notes == None) | (Word.usage_notes == ""),
            (Word.ipa == None) | (Word.ipa == ""),
        ]

        # Exemplos são preferencialmente preenchidos via generate_examples.py.
        if include_examples:
            missing_filters.append((Word.example_sentences == None) | (Word.example_sentences == ""))

        # Só considere áudio como "faltando" quando estiver gerando TTS.
        # (O áudio do dicionário ainda será preenchido quando a palavra cair por outros motivos.)
        if tts_missing_audio:
            missing_filters.append((Word.audio_url == None) | (Word.audio_url == ""))

        query = query.filter(or_(*missing_filters))

        # Evita ficar repetindo chamadas para headwords que já deram 404 no dicionário.
        query = query.filter(func.coalesce(Word.tags, "").notlike("%dict_en_404%"))

    if limit:
        query = query.limit(limit)

    words = query.all()
    total = len(words)

    if total == 0:
        print("✅ Todas as palavras já estão enriquecidas!")
        return

    print(f"📊 Total de palavras a processar: {total}")
    print(f"⏱️  Tempo estimado: ~{int(total * delay / 60)} minutos\n")

    success_count = 0
    error_count = 0
    skipped_count = 0
    invalid_count = 0
    rotated_count = 0
    tts_generated_count = 0

    for i, word in enumerate(words, 1):
        print(f"[{i}/{total}] {word.english}...", end=" ")

        if only_audio:
            url = None
            if tts_missing_audio and not (word.audio_url or "").strip():
                url = maybe_generate_word_tts_audio_url(db, word, voice=tts_voice)
            if url:
                word.audio_url = url
                tts_generated_count += 1
                print("✓")
                if tts_delay:
                    sleep(tts_delay)
            else:
                print("⊘")

            if commit_every and i % commit_every == 0:
                db.commit()
                print(f"\n💾 Salvando progresso... ({tts_generated_count} áudios TTS)\n")

            sleep(delay)
            continue

        if is_probably_rotated_import_row(word):
            print("⊘ (registro rotacionado/duplicado - revisar)")
            rotated_count += 1
            sleep(delay)
            continue

        if not is_headword_candidate_for_english_dictionary(word.english or ""):
            print("⊘ (entrada inválida p/ dicionário EN)")
            invalid_count += 1
            sleep(delay)
            continue

        updated = False
        api_tried = False
        api_data = None

        # Só chama a API quando realmente precisa de algo que ela pode fornecer.
        # (Exemplos/definições PT/notas podem ser preenchidos localmente.)
        needs_api = (
            not (word.word_type or "").strip()
            or not (word.definition_en or "").strip()
            or not (word.synonyms or "").strip()
            or not (word.antonyms or "").strip()
            or not (word.collocations or "").strip()
            or not (word.ipa or "").strip()
        )

        if needs_api:
            api_tried = True
            api_data = enrich_word_from_api(word.english)

        if api_data:
            # Atualizar palavra com dados da API

            if (not word.word_type) and api_data.get("word_type"):
                word.word_type = api_data["word_type"]
                updated = True

            if (not word.definition_en) and api_data.get("definition_en"):
                word.definition_en = api_data["definition_en"]
                updated = True

            if (not word.synonyms) and api_data.get("synonyms"):
                word.synonyms = api_data["synonyms"]
                updated = True

            if (not word.antonyms) and api_data.get("antonyms"):
                word.antonyms = api_data["antonyms"]
                updated = True

            if api_data.get("ipa") and not word.ipa:
                word.ipa = api_data["ipa"]
                updated = True

            if api_data.get("audio_url") and not word.audio_url:
                word.audio_url = api_data["audio_url"]
                updated = True

            # Exemplos
            if (not word.example_sentences) and api_data.get("example_sentences"):
                examples = api_data["example_sentences"]
                if examples:
                    # Traduzir exemplos (pt-BR) quando possível.
                    # Mantém fallback simples caso não haja chave/configuração.
                    for ex in examples[:3]:
                        if not ex.get("pt"):
                            translated = translate_en_to_pt_br(ex.get("en") or "")
                            if translated:
                                ex["pt"] = translated

                    word.example_sentences = json.dumps(examples)
                    updated = True

                    # Preencher campos simples usados no frontend (fallback do example_sentences)
                    if (not word.example_en) and examples[0].get("en"):
                        word.example_en = examples[0]["en"]
                        updated = True
                    if (not word.example_pt) and examples[0].get("pt"):
                        word.example_pt = examples[0]["pt"]
                        updated = True

            # Colocações
            if (not word.collocations) and api_data.get("collocations"):
                word.collocations = json.dumps(api_data["collocations"])
                updated = True

            # Gerar notas de uso
            if not word.usage_notes and api_data.get("word_type"):
                word.usage_notes = generate_usage_notes(
                    word.english,
                    api_data["word_type"]
                )
                updated = True

        # Fallbacks locais (rodar mesmo quando API falha/não é chamada)

        # Definição em PT (traduz definição EN quando faltar)
        if (not word.definition_pt) and (word.definition_en or "").strip():
            pt = translate_en_to_pt_br(word.definition_en or "")
            if pt:
                word.definition_pt = pt
                updated = True

        # Definição em EN (fallback: traduz PT->EN quando faltar)
        if (not word.definition_en) and (word.definition_pt or "").strip():
            en = translate_pt_br_to_en(word.definition_pt or "")
            if en:
                word.definition_en = en
                updated = True

        # word_type (fallback heurístico)
        if not word.word_type:
            wt = detect_word_type_simple(word.english or "")
            if wt:
                word.word_type = wt
                updated = True

        # Notas de uso (se já tiver word_type)
        if not word.usage_notes and (word.word_type or "").strip():
            word.usage_notes = generate_usage_notes(word.english, word.word_type)
            updated = True

        # Exemplo simples: se existir um lado, tenta traduzir o outro
        if (word.example_en or "").strip() and not (word.example_pt or "").strip():
            pt_ex = translate_en_to_pt_br(word.example_en or "")
            if pt_ex:
                word.example_pt = pt_ex
                updated = True
        if (word.example_pt or "").strip() and not (word.example_en or "").strip():
            en_ex = translate_pt_br_to_en(word.example_pt or "")
            if en_ex:
                word.example_en = en_ex
                updated = True

        # Se tentou API e não achou, marca 404 para não insistir.
        if api_tried and not api_data:
            tags = (word.tags or "").strip()
            if "dict_en_404" not in tags:
                word.tags = (tags + "," if tags else "") + "dict_en_404"
            error_count += 1

        if updated:
            print("✓")
            success_count += 1
        else:
            if api_tried and not api_data:
                print("✗ (não encontrada)")
            else:
                print("⊘ (sem novos dados)")
            skipped_count += 1

        # Commit a cada N palavras
        if commit_every and i % commit_every == 0:
            db.commit()
            print(f"\n💾 Salvando progresso... ({success_count} atualizadas)\n")

        # TTS fallback: gerar áudio local se ainda não tiver audio_url
        if tts_missing_audio and not (word.audio_url or "").strip():
            url = maybe_generate_word_tts_audio_url(db, word, voice=tts_voice)
            if url:
                word.audio_url = url
                tts_generated_count += 1
                if tts_delay:
                    sleep(tts_delay)

        # Rate limiting
        sleep(delay)

    # Commit final
    db.commit()

    print("\n" + "=" * 50)
    print("✅ ENRIQUECIMENTO CONCLUÍDO!\n")
    print(f"✓ Palavras atualizadas: {success_count}")
    print(f"⊘ Palavras sem novos dados: {skipped_count}")
    print(f"✗ Palavras não encontradas: {error_count}")
    print(f"⊘ Entradas inválidas p/ API EN: {invalid_count}")
    print(f"⊘ Registros rotacionados/duplicados: {rotated_count}")
    print(f"🔊 Áudios gerados via TTS: {tts_generated_count}")
    print(f"📊 Total processado: {total}")
    print("=" * 50)


def translate_example(english_example: str, target_word_pt: str) -> str:
    """
    Tradução básica de exemplos.
    Substitui a palavra principal e mantém estrutura simples.
    """
    # Traduções comuns
    common_translations = {
        "I": "Eu",
        "you": "você",
        "he": "ele",
        "she": "ela",
        "we": "nós",
        "they": "eles/elas",
        "am": "sou",
        "is": "é/está",
        "are": "são/estão",
        "was": "era/estava",
        "were": "eram/estavam",
        "have": "tenho",
        "has": "tem",
        "do": "faço",
        "does": "faz",
        "did": "fiz/fez",
        "can": "posso/pode",
        "will": "vou/vai",
        "every day": "todos os dias",
        "today": "hoje",
        "yesterday": "ontem",
        "a": "um/uma",
        "the": "o/a",
        "very": "muito",
    }

    # Tradução palavra por palavra (limitada)
    words = english_example.lower().split()
    translated = []

    for word in words:
        clean_word = word.strip(".,!?")
        if clean_word in common_translations:
            translated.append(common_translations[clean_word])
        else:
            # Manter original entre colchetes
            translated.append(f"[{word}]")

    # Retornar tradução simplificada
    # (Idealmente, usar uma API de tradução real aqui)
    return " ".join(translated)


def generate_usage_notes(word: str, word_type: str) -> str:
    """Gera notas de uso baseadas no tipo da palavra."""
    notes_templates = {
        "verb": f"Verbo em inglês. Verifique se é regular ou irregular.",
        "noun": f"Substantivo em inglês. Pode ser contável ou incontável.",
        "adjective": f"Adjetivo em inglês. Usado para descrever substantivos.",
        "adverb": f"Advérbio em inglês. Modifica verbos, adjetivos ou outros advérbios.",
        "preposition": f"Preposição em inglês. Indica relação entre palavras.",
    }

    return notes_templates.get(word_type, f"Palavra do tipo: {word_type}")


def enrich_specific_words(
    db: Session,
    words_list: list,
    *,
    tts_missing_audio: bool = False,
    tts_voice: str = "nova",
    tts_delay: float = 0.0,
):
    """Enriquece apenas uma lista específica de palavras."""
    print(f"🎯 Enriquecendo {len(words_list)} palavras específicas...\n")

    for word_str in words_list:
        word = db.query(Word).filter(
            func.lower(Word.english) == word_str.lower()
        ).first()

        if not word:
            print(f"⚠️  Palavra '{word_str}' não encontrada no banco")
            continue

        print(f"📖 {word.english}...", end=" ")

        api_data = enrich_word_from_api(word.english.lower())

        updated = False

        if api_data:
            if (not word.definition_en) and api_data.get("definition_en"):
                word.definition_en = api_data["definition_en"]
                updated = True
            if (not word.word_type) and api_data.get("word_type"):
                word.word_type = api_data["word_type"]
                updated = True
            if (not word.synonyms) and api_data.get("synonyms"):
                word.synonyms = api_data["synonyms"]
                updated = True
            if (not word.antonyms) and api_data.get("antonyms"):
                word.antonyms = api_data["antonyms"]
                updated = True
            if (not word.ipa) and api_data.get("ipa"):
                word.ipa = api_data["ipa"]
                updated = True
            if (not word.audio_url) and api_data.get("audio_url"):
                word.audio_url = api_data["audio_url"]
                updated = True
            if (not word.collocations) and api_data.get("collocations"):
                word.collocations = json.dumps(api_data["collocations"])
                updated = True
            if (not word.example_sentences) and api_data.get("example_sentences"):
                examples = api_data["example_sentences"]
                for ex in examples[:3]:
                    if not ex.get("pt"):
                        translated = translate_en_to_pt_br(ex.get("en") or "")
                        if translated:
                            ex["pt"] = translated
                word.example_sentences = json.dumps(examples)
                updated = True
                if (not word.example_en) and examples and examples[0].get("en"):
                    word.example_en = examples[0]["en"]
                    updated = True
                if (not word.example_pt) and examples and examples[0].get("pt"):
                    word.example_pt = examples[0]["pt"]
                    updated = True

        # Fallbacks (mesmo quando API falha)
        if (not word.definition_pt) and (word.definition_en or "").strip():
            pt = translate_en_to_pt_br(word.definition_en or "")
            if pt:
                word.definition_pt = pt
                updated = True

        if (not word.definition_en) and (word.definition_pt or "").strip():
            en = translate_pt_br_to_en(word.definition_pt or "")
            if en:
                word.definition_en = en
                updated = True

        if not word.word_type:
            wt = detect_word_type_simple(word.english or "")
            if wt:
                word.word_type = wt
                updated = True

        if (word.example_en or "").strip() and not (word.example_pt or "").strip():
            pt_ex = translate_en_to_pt_br(word.example_en or "")
            if pt_ex:
                word.example_pt = pt_ex
                updated = True
        if (word.example_pt or "").strip() and not (word.example_en or "").strip():
            en_ex = translate_pt_br_to_en(word.example_pt or "")
            if en_ex:
                word.example_en = en_ex
                updated = True

        # TTS fallback
        if tts_missing_audio and not (word.audio_url or "").strip():
            url = maybe_generate_word_tts_audio_url(db, word, voice=tts_voice)
            if url:
                word.audio_url = url
                updated = True
                if tts_delay:
                    sleep(tts_delay)

        print("✓" if updated else "⊘ (sem novos dados)")

        sleep(0.3)

    db.commit()
    print("\n✅ Palavras específicas enriquecidas!")


def main():
    """Função principal."""
    db = SessionLocal()

    try:
        import argparse

        parser = argparse.ArgumentParser(
            description="Enriquecimento de palavras via API"
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limitar número de palavras a processar"
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.3,
            help="Delay entre requisições (rate limiting). Default: 0.3"
        )
        parser.add_argument(
            "--commit-every",
            type=int,
            default=50,
            help="Commit a cada N palavras. Default: 50"
        )
        parser.add_argument(
            "--min-id",
            type=int,
            help="Processar apenas palavras com id >= min-id"
        )
        parser.add_argument(
            "--max-id",
            type=int,
            help="Processar apenas palavras com id <= max-id"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Processar todas, incluindo já enriquecidas"
        )
        parser.add_argument(
            "--only-audio",
            action="store_true",
            help="Apenas gerar/preencher audio_url (sem chamar dicionário/tradução)"
        )
        parser.add_argument(
            "--include-examples",
            action="store_true",
            help="Também tenta preencher example_sentences via dicionário (padrão: não; use generate_examples.py)"
        )
        parser.add_argument(
            "--words",
            nargs="+",
            help="Processar apenas palavras específicas"
        )

        parser.add_argument(
            "--tts-missing-audio",
            action="store_true",
            help="Gerar áudio via IA (OpenAI TTS) para palavras sem audio_url e salvar em /static/words"
        )
        parser.add_argument(
            "--tts-voice",
            type=str,
            default="nova",
            help="Voz do OpenAI TTS. Default: nova"
        )
        parser.add_argument(
            "--tts-delay",
            type=float,
            default=0.0,
            help="Delay extra (segundos) APÓS gerar TTS. Default: 0"
        )

        args = parser.parse_args()

        if args.words:
            # Modo específico
            enrich_specific_words(
                db,
                args.words,
                tts_missing_audio=args.tts_missing_audio,
                tts_voice=args.tts_voice,
                tts_delay=args.tts_delay,
            )
        else:
            # Modo em massa
            enrich_all_words(
                db,
                limit=args.limit,
                skip_existing=not args.all,
                delay=args.delay,
                commit_every=args.commit_every,
                min_id=args.min_id,
                max_id=args.max_id,
                tts_missing_audio=args.tts_missing_audio,
                tts_voice=args.tts_voice,
                tts_delay=args.tts_delay,
                only_audio=args.only_audio,
                include_examples=args.include_examples,
            )

    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário")
        db.commit()
        print("💾 Progresso salvo")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
