"""Conectar ao PostgreSQL e extrair dados"""
import os
import subprocess
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

# Testar conexão com Docker
print("🔍 Testando conexão com Docker...")

# Listar containers
result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
print("Containers ativos:")
print(result.stdout)

# Carregar credenciais
env = load_env(".env")
pg_user = env.get("POSTGRES_USER", "idiomasbr")
pg_password = env.get("POSTGRES_PASSWORD", "idiomasbr123")
pg_db = env.get("POSTGRES_DB", "idiomasbr")

# Tentar conexão
print("\n📡 Tentando conexão ao banco...")

sql = """
SELECT COUNT(*) as total,
       SUM(CASE WHEN example_en IS NULL OR example_en = '' THEN 1 ELSE 0 END) as empty_en,
       SUM(CASE WHEN example_pt IS NULL OR example_pt = '' THEN 1 ELSE 0 END) as empty_pt
FROM words;
"""

result = subprocess.run(
    ['docker', 'exec', '-e', f'PGPASSWORD={pg_password}', 'idiomasbr-postgres', 'psql', 
     '-U', pg_user, '-d', pg_db, 
     '-c', sql],
    capture_output=True,
    text=True,
    timeout=30
)

print("Resultado da query:")
print(result.stdout)
if result.stderr:
    print("Erro:", result.stderr)

# Alternativa: usar arquivo SQL
print("\n💾 Criando arquivo SQL para execução...")

with open('check_db.sql', 'w') as f:
    f.write("""
-- Verificar tabela words
SELECT COUNT(*) as total_words FROM words;

-- Verificar example_en e example_pt vazios  
SELECT 
    (SELECT COUNT(*) FROM words WHERE example_en IS NULL OR example_en = '') as empty_example_en,
    (SELECT COUNT(*) FROM words WHERE example_pt IS NULL OR example_pt = '') as empty_example_pt;

-- Mostrar alguns registros com problemas
SELECT id, english, portuguese, 
       example_en, example_pt,
       LENGTH(COALESCE(level, '')) as level_len
FROM words 
WHERE example_en IS NULL OR example_en = '' OR example_pt IS NULL OR example_pt = ''
LIMIT 20;
""")

print("✅ Arquivo check_db.sql criado")
print("\nExecutando...")

result = subprocess.run(
    ['docker', 'exec', '-e', f'PGPASSWORD={pg_password}', 'idiomasbr-postgres', 'psql',
     '-U', pg_user, '-d', pg_db, 
     '-f', '/check_db.sql'],
    capture_output=True,
    text=True,
    timeout=30
)

with open('db_check_result.txt', 'w') as f:
    f.write(result.stdout)
    if result.stderr:
        f.write("\nERROS:\n" + result.stderr)

print(result.stdout)
if result.stderr:
    print("ERROS:", result.stderr)
