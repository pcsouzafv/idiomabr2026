#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gerar exemplos de frases em contexto usando APIs
"""
import psycopg2
import requests
import time
import json
from typing import Optional, Dict, Tuple
import sys
import io
import argparse

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configurações do banco de dados
import os
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'idiomasbr'),
    'user': os.getenv('DB_USER', 'idiomasbr'),
    'password': os.getenv('DB_PASSWORD', 'idiomasbr123')
}

# API gratuita para exemplos de frases
FREE_DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
TATOEBA_API = "https://tatoeba.org/en/api_v0/search?from=eng&to=por&query={word}"

def get_example_from_freedict(word: str) -> Optional[Tuple[str, str]]:
    """
    Busca exemplo de frase do Free Dictionary API
    Returns: (example_en, definition) ou None
    """
    try:
        url = FREE_DICT_API.format(word=word)
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # Procura primeira definição com exemplo
                for entry in data[0].get('meanings', []):
                    for definition in entry.get('definitions', []):
                        example = definition.get('example')
                        if example and len(example) > 10:
                            # Retorna exemplo e definição
                            return (example, definition.get('definition', ''))
        return None
    except Exception as e:
        print(f"  [WARN] Erro FreeDictionary para '{word}': {e}")
        return None

def translate_sentence(text: str) -> Optional[str]:
    """
    Traduz frase usando MyMemory Translation API
    """
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': text,
            'langpair': 'en|pt-br'
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('responseStatus') == 200:
            translation = data['responseData']['translatedText']
            # Verifica se não é tradução literal da palavra
            if translation and translation.lower() != text.lower():
                return translation
        return None
    except Exception as e:
        print(f"  [WARN] Erro tradução: {e}")
        return None

def generate_smart_example(word: str, word_type: str = 'unknown') -> Tuple[Optional[str], Optional[str]]:
    """
    Gera exemplo inteligente baseado no tipo de palavra
    Returns: (example_en, example_pt)
    """
    # Templates por tipo de palavra
    templates = {
        'verb': [
            f"I {word} every morning.",
            f"She {word}s when she is happy.",
            f"They will {word} tomorrow.",
            f"We should {word} more often.",
        ],
        'noun': [
            f"The {word} is very important.",
            f"I saw a beautiful {word} yesterday.",
            f"This {word} belongs to me.",
            f"That {word} is amazing!",
        ],
        'adjective': [
            f"She is very {word}.",
            f"The weather is {word} today.",
            f"It looks {word} from here.",
            f"This seems quite {word}.",
        ],
        'adverb': [
            f"He speaks {word}.",
            f"She smiled {word}.",
            f"They work {word}.",
        ],
        'unknown': [
            f"This is an example with {word}.",
            f"The word '{word}' is useful.",
        ]
    }

    template_list = templates.get(word_type, templates['unknown'])
    example_en = template_list[0]

    # Traduz (pode falhar; ainda assim mantém example_en)
    example_pt = translate_sentence(example_en)

    return (example_en, example_pt)

def detect_word_type(word: str, definition: str = '') -> str:
    """
    Detecta tipo de palavra baseado em padrões comuns
    """
    word_lower = word.lower()
    definition_lower = definition.lower()

    # Verbos comuns terminam em específicos padrões
    verb_patterns = ['ing', 'ed', 'ate', 'ize', 'ify']
    if any(word_lower.endswith(p) for p in verb_patterns):
        return 'verb'

    # Adjetivos comuns
    adj_patterns = ['ful', 'less', 'ous', 'ive', 'able', 'ible']
    if any(word_lower.endswith(p) for p in adj_patterns):
        return 'adjective'

    # Advérbios
    if word_lower.endswith('ly'):
        return 'adverb'

    # Substantivos (padrão)
    noun_patterns = ['tion', 'ness', 'ment', 'ity', 'er', 'or', 'ism']
    if any(word_lower.endswith(p) for p in noun_patterns):
        return 'noun'

    # Baseado na definição
    if definition_lower:
        if 'verb' in definition_lower or 'to ' in definition_lower[:10]:
            return 'verb'
        elif 'adjective' in definition_lower or 'describing' in definition_lower:
            return 'adjective'
        elif 'adverb' in definition_lower:
            return 'adverb'
        elif 'noun' in definition_lower:
            return 'noun'

    return 'unknown'

def populate_examples(*, limit: int = 100, min_id: int | None = None, max_id: int | None = None, delay_s: float = 0.5):
    """
    Popula exemplos no banco de dados
    """
    conn = None
    try:
        print("[CONNECT] Conectando ao banco de dados...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Busca palavras sem exemplos
        print("\n[SEARCH] Buscando palavras sem exemplos...")
        where_parts = [
            "((example_en IS NULL OR example_en = '') OR (example_sentences IS NULL OR example_sentences = ''))",
            "LENGTH(english) < 20",
            "english ~* '^[a-z]+$'",
        ]
        params = []
        if min_id is not None:
            where_parts.append("id >= %s")
            params.append(min_id)
        if max_id is not None:
            where_parts.append("id <= %s")
            params.append(max_id)

        sql = (
            "SELECT id, english, example_en, example_pt, example_sentences "
            "FROM words "
            f"WHERE {' AND '.join(where_parts)} "
            "ORDER BY id "
            f"LIMIT {int(limit)}"
        )
        cursor.execute(sql, tuple(params))

        words = cursor.fetchall()
        print(f"[OK] Encontradas {len(words)} palavras para processar\n")

        updated = 0
        failed = 0

        for idx, (word_id, english, existing_example_en, existing_example_pt, existing_example_sentences) in enumerate(words, 1):
            print(f"\n[{idx}/{len(words)}] Processando: {english}")

            # Caso simples: já tem example_en, mas falta o JSON example_sentences
            if (existing_example_en or "").strip() and not (existing_example_sentences or "").strip():
                example_en = (existing_example_en or "").strip()
                example_pt = (existing_example_pt or "").strip() if existing_example_pt else ""
                example_sentences = json.dumps([
                    {"en": example_en, "pt": example_pt}
                ])
                cursor.execute(
                    "UPDATE words SET example_sentences = %s WHERE id = %s",
                    (example_sentences, word_id),
                )
                conn.commit()
                print("  [UPDATE] Preenchido example_sentences a partir do exemplo existente")
                updated += 1
                time.sleep(float(delay_s))
                continue

            # Tenta buscar exemplo real primeiro
            result = get_example_from_freedict(english)

            if result:
                example_en, definition = result
                word_type = detect_word_type(english, definition)
                print(f"  [INFO] Tipo detectado: {word_type}")
                print(f"  [OK] Exemplo encontrado: {example_en[:60]}...")

                # Traduz exemplo
                example_pt = translate_sentence(example_en)

                if example_pt:
                    print(f"  [OK] Traducao: {example_pt[:60]}...")
                else:
                    print(f"  [WARN] Falha na traducao, gerando exemplo simples...")
                    example_en, example_pt = generate_smart_example(english, word_type)
            else:
                # Gera exemplo inteligente
                print(f"  [INFO] Nao encontrou exemplo real, gerando...")
                word_type = detect_word_type(english)
                example_en, example_pt = generate_smart_example(english, word_type)
                print(f"  [OK] Exemplo gerado: {example_en}")

            # Atualiza banco (salva EN mesmo se PT falhar)
            if example_en:
                example_sentences = json.dumps([
                    {"en": example_en, "pt": example_pt or ""}
                ])
                cursor.execute("""
                    UPDATE words
                    SET example_en = %s,
                        example_pt = %s,
                        example_sentences = CASE
                            WHEN (example_sentences IS NULL OR example_sentences = '') THEN %s
                            ELSE example_sentences
                        END
                    WHERE id = %s
                """, (example_en, example_pt or "", example_sentences, word_id))
                conn.commit()
                print(f"  [UPDATE] Atualizado no banco de dados!")
                updated += 1
            else:
                print(f"  [FAIL] Nao conseguiu gerar exemplo")
                failed += 1

            # Rate limiting
            time.sleep(float(delay_s))

            # Checkpoint
            if idx % 20 == 0:
                print(f"\n[CHECKPOINT] {updated} atualizadas, {failed} falhas")

        # Resumo final
        print("\n" + "="*60)
        print("[SUMMARY] RESUMO FINAL:")
        print(f"  [OK] Atualizadas: {updated}")
        print(f"  [FAIL] Falhas: {failed}")
        print(f"  [INFO] Total processadas: {len(words)}")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] ERRO: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\n[CLOSE] Conexao fechada")

if __name__ == "__main__":
    print("="*60)
    print("GERADOR DE EXEMPLOS - IdiomasBR")
    print("="*60)
    parser = argparse.ArgumentParser(description="Gera example_en/example_pt para palavras sem exemplo")
    parser.add_argument("--limit", type=int, default=100, help="Quantas palavras processar (default: 100)")
    parser.add_argument("--min-id", type=int, help="Processar apenas id >= min-id")
    parser.add_argument("--max-id", type=int, help="Processar apenas id <= max-id")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay entre palavras (default: 0.5)")
    args = parser.parse_args()

    populate_examples(limit=args.limit, min_id=args.min_id, max_id=args.max_id, delay_s=args.delay)
