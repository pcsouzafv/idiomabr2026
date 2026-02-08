"""Extrair e corrigir dados corrompidos do banco"""
import os
import subprocess
import pandas as pd
import sys


def load_env(path: str) -> dict:
    """Carregar variáveis simples de um arquivo .env"""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def run_sql(sql: str, pg_user: str, pg_db: str, pg_password: str | None = None):
    """Executar SQL no PostgreSQL via Docker"""
    try:
        cmd = [
            "docker",
            "exec",
            "-e",
            f"PGPASSWORD={pg_password or ''}",
            "idiomasbr-postgres",
            "psql",
            "-U",
            pg_user,
            "-d",
            pg_db,
            "-c",
            sql,
            "-t",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, str(e), -1

print("=" * 80)
print("🔍 EXTRAINDO E CORRIGINDO DADOS CORROMPIDOS")
print("=" * 80)

# Carregar credenciais do .env
env = load_env(".env")
pg_user = env.get("POSTGRES_USER", "idiomasbr")
pg_password = env.get("POSTGRES_PASSWORD", "idiomasbr123")
pg_db = env.get("POSTGRES_DB", "idiomasbr")

# 1. Verificar acesso ao banco
print("\n1️⃣  Testando acesso ao banco...")
stdout, stderr, code = run_sql("SELECT COUNT(*) FROM words;", pg_user, pg_db, pg_password)

if code != 0:
    print(f"❌ Erro na conexão: {stderr}")
    print("\nVerifique o usuário/senha em .env")

if code == 0 and stdout:
    total = stdout.strip()
    print(f"✅ Banco acessível. Total de registros: {total}")
else:
    print(f"⚠️  Não foi possível conectar: {stderr}")
    print("\nAbortando...")
    sys.exit(1)

# 2. Extrair registros com problemas
print("\n2️⃣  Extraindo registros com dados corrompidos...")

export_sql = """
COPY (
    SELECT 
        id, english, portuguese, level, word_type,
        definition_en, definition_pt,
        COALESCE(example_en, '') as example_en,
        COALESCE(example_pt, '') as example_pt,
        tags
    FROM words 
    WHERE 
        (example_en IS NULL OR example_en = '' OR LENGTH(example_en) > 500)
        OR (example_pt IS NULL OR example_pt = '' OR LENGTH(example_pt) > 500)
        OR (definition_en IS NULL OR definition_en = '')
        OR (definition_pt IS NULL OR definition_pt = '')
        OR LENGTH(COALESCE(level, '')) > 10
    ORDER BY id
) TO STDOUT WITH CSV HEADER;
"""

result = subprocess.run(
    [
        "docker",
        "exec",
        "-e",
        f"PGPASSWORD={pg_password}",
        "idiomasbr-postgres",
        "psql",
        "-U",
        pg_user,
        "-d",
        pg_db,
        "-c",
        export_sql,
    ],
    capture_output=True,
    text=False,
    timeout=120,
)

stdout_text = result.stdout.decode("utf-8", errors="replace") if result.stdout else ""
stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

if result.returncode == 0 and stdout_text:
    # Salvar CSV
    with open('corrupted_data.csv', 'w', encoding='utf-8-sig') as f:
        f.write(stdout_text)
    
    # Contar linhas
    lines = stdout_text.strip().split('\n')
    print(f"✅ Extraídos {len(lines) - 1} registros com problemas")
    print(f"   Arquivo: corrupted_data.csv")
    
    # Mostrar amostra
    print("\n📋 Amostra dos primeiros 10 registros problemáticos:")
    df = pd.read_csv('corrupted_data.csv', encoding='utf-8-sig')
    print(df[['id', 'english', 'portuguese', 'example_en', 'example_pt']].head(10).to_string())
    
else:
    print(f"⚠️  Erro ao exportar: {stderr_text}")

print("\n" + "=" * 80)
print("✅ Processo concluído!")
print("=" * 80)
