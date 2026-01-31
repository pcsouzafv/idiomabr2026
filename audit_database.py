"""Auditoria completa do banco - Identificar dados corrompidos"""
import subprocess
import json

def run_query(query):
    """Executar query no PostgreSQL"""
    result = subprocess.run(
        ['docker', 'exec', 'idiomasbr-postgres', 'psql',
         '-U', 'postgres', '-d', 'idiomasbr', '-c', query, '-t'],
        capture_output=True, text=True, timeout=60
    )
    return result.stdout.strip() if result.returncode == 0 else f"ERROR: {result.stderr}"

print("=" * 80)
print("AUDITORIA DO BANCO DE DADOS")
print("=" * 80)

# 1. Total de registros
total = run_query("SELECT COUNT(*) FROM words;")
print(f"\n1️⃣  TOTAL DE REGISTROS: {total}")

# 2. Registros com example_en vazio
empty_en = run_query("SELECT COUNT(*) FROM words WHERE example_en IS NULL OR example_en = '';")
print(f"2️⃣  example_en VAZIO: {empty_en}")

# 3. Registros com example_pt vazio
empty_pt = run_query("SELECT COUNT(*) FROM words WHERE example_pt IS NULL OR example_pt = '';")
print(f"3️⃣  example_pt VAZIO: {empty_pt}")

# 4. Level com valor inválido (> 10 chars)
bad_level = run_query("SELECT COUNT(*) FROM words WHERE LENGTH(COALESCE(level, '')) > 10;")
print(f"4️⃣  level INVÁLIDO (>10 chars): {bad_level}")

# 5. Definition_en vazio
empty_def_en = run_query("SELECT COUNT(*) FROM words WHERE definition_en IS NULL OR definition_en = '';")
print(f"5️⃣  definition_en VAZIO: {empty_def_en}")

# 6. Definition_pt vazio
empty_def_pt = run_query("SELECT COUNT(*) FROM words WHERE definition_pt IS NULL OR definition_pt = '';")
print(f"6️⃣  definition_pt VAZIO: {empty_def_pt}")

# 7. Amostra de registros com problemas
print("\n" + "=" * 80)
print("AMOSTRA DE REGISTROS PROBLEMÁTICOS")
print("=" * 80)

bad_query = """
SELECT id, english, level, 
       CASE WHEN example_en IS NULL THEN 'NULL' WHEN example_en = '' THEN 'EMPTY' ELSE 'OK' END as en_status,
       CASE WHEN example_pt IS NULL THEN 'NULL' WHEN example_pt = '' THEN 'EMPTY' ELSE 'OK' END as pt_status,
       LENGTH(COALESCE(level, '')) as level_len
FROM words 
WHERE example_en IS NULL OR example_en = '' OR example_pt IS NULL OR example_pt = ''
   OR LENGTH(COALESCE(level, '')) > 10
LIMIT 30;
"""

sample = run_query(bad_query)
print(sample)

print("\n" + "=" * 80)
print("ESTATÍSTICAS FINAIS")
print("=" * 80)

stats = {
    'total_records': int(total) if total.isdigit() else 0,
    'empty_example_en': int(empty_en) if empty_en.isdigit() else 0,
    'empty_example_pt': int(empty_pt) if empty_pt.isdigit() else 0,
    'bad_level_format': int(bad_level) if bad_level.isdigit() else 0,
    'empty_def_en': int(empty_def_en) if empty_def_en.isdigit() else 0,
    'empty_def_pt': int(empty_def_pt) if empty_def_pt.isdigit() else 0,
}

with open('audit_results.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, indent=2)

print(f"\n✅ Auditoria salva em: audit_results.json")
print(json.dumps(stats, indent=2))
