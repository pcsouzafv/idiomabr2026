"""
Script de enriquecimento em massa usando APIs de dicionário.

Este script busca automaticamente definições, sinônimos, exemplos e outras
informações para todas as palavras do banco de dados.

Usa:
- Free Dictionary API (gratuita, sem limite)
- Datamuse API (gratuita, para sinônimos e colocações)
"""

import json
import os
import sys
from time import sleep
from sqlalchemy.orm import Session
from sqlalchemy import func

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.word import Word
from services.dictionary_api import enrich_word_from_api


def enrich_all_words(
    db: Session,
    limit: int = None,
    skip_existing: bool = True,
    delay: float = 0.3
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

    if skip_existing:
        # Pular palavras que já têm definição
        query = query.filter(
            (Word.definition_en == None) | (Word.definition_en == "")
        )

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

    for i, word in enumerate(words, 1):
        print(f"[{i}/{total}] {word.english}...", end=" ")

        # Buscar dados da API
        api_data = enrich_word_from_api(word.english.lower())

        if api_data:
            # Atualizar palavra com dados da API
            updated = False

            if api_data.get("word_type"):
                word.word_type = api_data["word_type"]
                updated = True

            if api_data.get("definition_en"):
                word.definition_en = api_data["definition_en"]
                updated = True

            if api_data.get("synonyms"):
                word.synonyms = api_data["synonyms"]
                updated = True

            if api_data.get("antonyms"):
                word.antonyms = api_data["antonyms"]
                updated = True

            if api_data.get("ipa") and not word.ipa:
                word.ipa = api_data["ipa"]
                updated = True

            # Exemplos
            if api_data.get("example_sentences"):
                examples = api_data["example_sentences"]
                if examples:
                    # Traduzir exemplos (básico)
                    for ex in examples:
                        if not ex.get("pt"):
                            ex["pt"] = translate_example(ex["en"], word.portuguese)

                    word.example_sentences = json.dumps(examples)
                    updated = True

            # Colocações
            if api_data.get("collocations"):
                word.collocations = json.dumps(api_data["collocations"])
                updated = True

            # Gerar notas de uso
            if not word.usage_notes and api_data.get("word_type"):
                word.usage_notes = generate_usage_notes(
                    word.english,
                    api_data["word_type"]
                )
                updated = True

            if updated:
                print("✓")
                success_count += 1
            else:
                print("⊘ (sem novos dados)")
                skipped_count += 1

            # Commit a cada 50 palavras
            if i % 50 == 0:
                db.commit()
                print(f"\n💾 Salvando progresso... ({success_count} atualizadas)\n")

        else:
            print("✗ (não encontrada)")
            error_count += 1

        # Rate limiting
        sleep(delay)

    # Commit final
    db.commit()

    print("\n" + "=" * 50)
    print("✅ ENRIQUECIMENTO CONCLUÍDO!\n")
    print(f"✓ Palavras atualizadas: {success_count}")
    print(f"⊘ Palavras sem novos dados: {skipped_count}")
    print(f"✗ Palavras não encontradas: {error_count}")
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


def enrich_specific_words(db: Session, words_list: list):
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

        if api_data:
            # Atualizar
            if api_data.get("definition_en"):
                word.definition_en = api_data["definition_en"]
            if api_data.get("word_type"):
                word.word_type = api_data["word_type"]
            if api_data.get("synonyms"):
                word.synonyms = api_data["synonyms"]
            if api_data.get("example_sentences"):
                word.example_sentences = json.dumps(api_data["example_sentences"])

            print("✓")
        else:
            print("✗")

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
            "--all",
            action="store_true",
            help="Processar todas, incluindo já enriquecidas"
        )
        parser.add_argument(
            "--words",
            nargs="+",
            help="Processar apenas palavras específicas"
        )

        args = parser.parse_args()

        if args.words:
            # Modo específico
            enrich_specific_words(db, args.words)
        else:
            # Modo em massa
            enrich_all_words(
                db,
                limit=args.limit,
                skip_existing=not args.all,
                delay=0.3
            )

    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário")
        db.commit()
        print("💾 Progresso salvo")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
