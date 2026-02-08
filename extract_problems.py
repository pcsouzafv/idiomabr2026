"""
Extrair dados corrompidos do banco PostgreSQL
Mostra: examples vazios, definitions vazios, dados com formato errado
"""
import subprocess
import sys

def run_sql(sql):
    """Executar SQL e retornar resultado em CSV"""
    try:
        result = subprocess.run(
            ['docker', 'exec', '-i', 'idiomasbr-postgres', 'psql',
             '-U', 'postgres', '-d', 'idiomasbr', '-F,'],
            input=sql,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"ERRO: {str(e)}"

print("🔍 EXTRAÇÃO DE DADOS CORROMPIDOS")
print("=" * 80)

# 1. Contar problemas
count_sql = """
SELECT 
    (SELECT COUNT(*) FROM words) as total,
    (SELECT COUNT(*) FROM words WHERE example_en IS NULL OR example_en = '') as empty_en,
    (SELECT COUNT(*) FROM words WHERE example_pt IS NULL OR example_pt = '') as empty_pt,
    (SELECT COUNT(*) FROM words WHERE definition_en IS NULL OR definition_en = '') as empty_def_en,
    (SELECT COUNT(*) FROM words WHERE definition_pt IS NULL OR definition_pt = '') as empty_def_pt,
    (SELECT COUNT(*) FROM words WHERE LENGTH(COALESCE(level,'')) > 10) as bad_level;
"""

print("\n1️⃣  CONTAGEM DE PROBLEMAS:")
counts = run_sql(count_sql)
print(counts)

# 2. Amostra de registros com examples vazios
sample_sql = """
SELECT id, english, portuguese, level,
       COALESCE(example_en, '[VAZIO]')::text as example_en,
       COALESCE(example_pt, '[VAZIO]')::text as example_pt,
       COALESCE(definition_en, '[VAZIO]')::text as definition_en
FROM words 
WHERE example_en IS NULL OR example_en = '' OR example_pt IS NULL OR example_pt = ''
ORDER BY id 
LIMIT 50;
"""

print("\n2️⃣  AMOSTRA DE REGISTROS COM EXAMPLES VAZIOS (primeiros 50):")
sample = run_sql(sample_sql)
lines = sample.split('\n')
for i, line in enumerate(lines[:52]):
    print(line)

# 3. Registros com level inválido
level_sql = """
SELECT id, english, level, LENGTH(level) as level_length
FROM words 
WHERE LENGTH(COALESCE(level,'')) > 10
ORDER BY id
LIMIT 30;
"""

print("\n3️⃣  REGISTROS COM LEVEL INVÁLIDO (> 10 chars):")
bad_levels = run_sql(level_sql)
print(bad_levels)

# 4. Salvar resultado completo em arquivo
with open('database_problems.txt', 'w', encoding='utf-8') as f:
    f.write("=== RELATÓRIO DE PROBLEMAS NO BANCO ===\n\n")
    f.write("1. CONTAGEM:\n")
    f.write(counts + "\n\n")
    f.write("2. AMOSTRA DE EXAMPLES VAZIOS:\n")
    f.write(sample + "\n\n")
    f.write("3. LEVELS INVÁLIDOS:\n")
    f.write(bad_levels + "\n")

print("\n✅ Relatório completo salvo em: database_problems.txt")
