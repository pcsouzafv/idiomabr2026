"""
Script para popular o banco de dados no Cloud SQL via Cloud Run
"""
import os
import sys
import psycopg2
from psycopg2.extras import execute_values

# Sample words data
sample_words = [
    ("hello", "həˈloʊ", "olá", "A1", "saudação"),
    ("goodbye", "ɡʊdˈbaɪ", "adeus", "A1", "saudação"),
    ("thank you", "θæŋk juː", "obrigado", "A1", "saudação"),
    ("please", "pliːz", "por favor", "A1", "saudação"),
    ("yes", "jɛs", "sim", "A1", "básico"),
    ("no", "noʊ", "não", "A1", "básico"),
    ("water", "ˈwɔːtər", "água", "A1", "comida,bebida"),
    ("food", "fuːd", "comida", "A1", "comida"),
    ("house", "haʊs", "casa", "A1", "moradia"),
    ("car", "kɑːr", "carro", "A1", "transporte"),
    ("work", "wɜːrk", "trabalho", "A1", "trabalho"),
    ("money", "ˈmʌni", "dinheiro", "A1", "finanças"),
    ("time", "taɪm", "tempo", "A1", "tempo"),
    ("day", "deɪ", "dia", "A1", "tempo"),
    ("night", "naɪt", "noite", "A1", "tempo"),
    ("today", "təˈdeɪ", "hoje", "A1", "tempo"),
    ("tomorrow", "təˈmɑːroʊ", "amanhã", "A1", "tempo"),
    ("yesterday", "ˈjestərdeɪ", "ontem", "A1", "tempo"),
    ("love", "lʌv", "amor", "A1", "sentimento"),
    ("friend", "frend", "amigo", "A1", "pessoas"),
]

# Conexão com Cloud SQL
try:
    conn = psycopg2.connect(
        host="/cloudsql/idiomasbr:us-central1:idiomasbr-db",
        database="idiomasbr",
        user="idiomasbr",
        password="idiomasbr123"
    )

    cur = conn.cursor()

    # Inserir palavras (ignorar duplicatas)
    insert_query = """
        INSERT INTO words (english, ipa, portuguese, level, tags, created_at, updated_at)
        VALUES %s
        ON CONFLICT (english) DO NOTHING
    """

    values = [(w[0], w[1], w[2], w[3], w[4], 'NOW()', 'NOW()') for w in sample_words]
    execute_values(cur, insert_query, values)

    conn.commit()
    print(f"Inseridas {cur.rowcount} palavras com sucesso!")

    cur.close()
    conn.close()

except Exception as e:
    print(f"Erro: {e}")
    sys.exit(1)
