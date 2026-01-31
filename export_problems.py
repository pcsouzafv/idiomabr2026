"""Exportar dados problemáticos do banco para análise"""
import subprocess
import csv
import sys

# Query para extrair dados com problemas
query = """
SELECT 
    id, 
    english, 
    portuguese, 
    level, 
    word_type,
    example_en,
    example_pt,
    definition_en,
    definition_pt
FROM words 
WHERE 
    (example_en IS NULL OR example_en = '') 
    OR (example_pt IS NULL OR example_pt = '')
    OR LENGTH(COALESCE(level, '')) > 10
    OR definition_en IS NULL OR definition_en = ''
ORDER BY id LIMIT 200;
"""

try:
    # Executar query no PostgreSQL
    result = subprocess.run(
        [
            'docker', 'exec', 'idiomasbr-postgres', 'psql',
            '-U', 'postgres',
            '-d', 'idiomasbr',
            '-c', query,
            '-t'  # tuples only
        ],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode != 0:
        print(f"Erro na query: {result.stderr}")
        sys.exit(1)
    
    # Salvar resultado
    with open('problematic_words.csv', 'w', encoding='utf-8-sig') as f:
        f.write("id,english,portuguese,level,word_type,example_en,example_pt,definition_en,definition_pt\n")
        f.write(result.stdout)
    
    # Mostrar amostra
    lines = result.stdout.strip().split('\n')
    print(f"✅ Encontrados {len(lines)} registros problemáticos (mostrando primeiros 20):")
    print("\n".join(lines[:20]))
    print(f"\nArquivo salvo: problematic_words.csv ({len(lines)} linhas)")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)
