#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir traduções usando APIs de dicionário
"""
import psycopg2
import requests
import time
import json
from typing import Optional, Dict, List
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configurações do banco de dados
import os
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),  # 'postgres' é o nome do serviço no Docker Compose
    'port': os.getenv('DB_PORT', 5432),        # Porta interna do Docker
    'database': os.getenv('DB_NAME', 'idiomasbr'),
    'user': os.getenv('DB_USER', 'idiomasbr'),
    'password': os.getenv('DB_PASSWORD', 'idiomasbr123')
}

# APIs de tradução (gratuitas)
MYMEMORY_API = "https://api.mymemory.translated.net/get"
FREE_DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

def get_translation_mymemory(word: str) -> Optional[str]:
    """Busca tradução usando MyMemory API"""
    try:
        params = {
            'q': word,
            'langpair': 'en|pt-br'
        }
        response = requests.get(MYMEMORY_API, params=params, timeout=10)
        data = response.json()

        if data.get('responseStatus') == 200:
            translation = data['responseData']['translatedText']
            return translation if translation.lower() != word.lower() else None
        return None
    except Exception as e:
        print(f"  [WARN] Erro MyMemory para '{word}': {e}")
        return None

def get_definition_freedict(word: str) -> Optional[Dict]:
    """Busca definição usando Free Dictionary API"""
    try:
        url = FREE_DICT_API.format(word=word)
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                meanings = []
                for entry in data[0].get('meanings', []):
                    part_of_speech = entry.get('partOfSpeech', '')
                    for definition in entry.get('definitions', [])[:2]:  # Primeiras 2 definições
                        meanings.append(definition.get('definition', ''))

                return {
                    'word': word,
                    'phonetic': data[0].get('phonetic', ''),
                    'meanings': meanings
                }
        return None
    except Exception as e:
        print(f"  [WARN] Erro FreeDictionary para '{word}': {e}")
        return None

def get_best_translation(word: str, current_translation: str) -> Optional[str]:
    """
    Tenta obter a melhor tradução de múltiplas fontes
    """
    print(f"\n[SEARCH] Buscando traducao para: '{word}' (atual: '{current_translation}')")

    # 1. Tenta MyMemory primeiro (tradução direta)
    translation = get_translation_mymemory(word)
    if translation and len(translation) > 0:
        print(f"  [OK] MyMemory: {translation}")
        time.sleep(0.5)  # Rate limiting
        return translation

    # 2. Tenta Free Dictionary (definição em inglês - não traduz)
    # dict_data = get_definition_freedict(word)
    # if dict_data:
    #     print(f"  [INFO] FreeDictionary: {dict_data['meanings'][0][:100]}...")
    #     # Não retorna definição em inglês, apenas para referência

    time.sleep(0.5)  # Rate limiting
    return None

def fix_translations():
    """Corrige traduções no banco de dados"""
    conn = None
    try:
        # Conecta ao banco
        print("[CONNECT] Conectando ao banco de dados...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Busca entradas problemáticas (traduções suspeitas)
        print("\n[SEARCH] Buscando entradas com traducoes problematicas...")
        cursor.execute("""
            SELECT id, english, ipa, portuguese
            FROM words
            WHERE portuguese ~ '^[a-z]{2,}$'
                AND portuguese NOT LIKE '%,%'
                AND LENGTH(portuguese) < 30
                AND english ~ '^[a-z]+$'
            ORDER BY id
            LIMIT 200
        """)

        entries = cursor.fetchall()
        print(f"[OK] Encontradas {len(entries)} entradas para corrigir\n")

        # Estatísticas
        updated = 0
        failed = 0
        skipped = 0

        # Processa cada entrada
        for idx, (word_id, english, ipa, portuguese) in enumerate(entries, 1):
            print(f"\n[{idx}/{len(entries)}] ID {word_id}: {english}")

            # Busca tradução correta
            new_translation = get_best_translation(english, portuguese)

            if new_translation and new_translation != portuguese:
                # Atualiza no banco
                cursor.execute("""
                    UPDATE words
                    SET portuguese = %s
                    WHERE id = %s
                """, (new_translation, word_id))
                conn.commit()

                print(f"  [UPDATE] ATUALIZADO: '{portuguese}' -> '{new_translation}'")
                updated += 1
            elif new_translation == portuguese:
                print(f"  [SKIP] MANTIDO: '{portuguese}' (ja esta correto)")
                skipped += 1
            else:
                print(f"  [FAIL] FALHOU: Nao encontrou traducao para '{english}'")
                failed += 1

            # Rate limiting (máximo 10 requisições/segundo)
            time.sleep(0.2)

            # Checkpoint a cada 20 palavras
            if idx % 20 == 0:
                print(f"\n[CHECKPOINT] {updated} atualizadas, {failed} falhas, {skipped} mantidas")

        # Resumo final
        print("\n" + "="*60)
        print("[SUMMARY] RESUMO FINAL:")
        print(f"  [OK] Atualizadas: {updated}")
        print(f"  [SKIP] Mantidas: {skipped}")
        print(f"  [FAIL] Falhas: {failed}")
        print(f"  [INFO] Total processadas: {len(entries)}")
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
    print("CORRETOR DE TRADUCOES - IdiomasBR")
    print("="*60)
    fix_translations()
