"""Consulta rápida ao banco via Docker."""
import os
import subprocess


def load_env(path: str) -> dict:
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


env = load_env(".env")
pg_user = env.get("POSTGRES_USER", "idiomasbr")
pg_password = env.get("POSTGRES_PASSWORD", "idiomasbr123")
pg_db = env.get("POSTGRES_DB", "idiomasbr")

count_sql = """
SELECT 
  COUNT(*) AS total,
  SUM(CASE WHEN example_en IS NULL OR example_en = '' THEN 1 ELSE 0 END) AS empty_example_en,
  SUM(CASE WHEN example_pt IS NULL OR example_pt = '' THEN 1 ELSE 0 END) AS empty_example_pt,
  SUM(CASE WHEN definition_en IS NULL OR definition_en = '' THEN 1 ELSE 0 END) AS empty_definition_en,
  SUM(CASE WHEN definition_pt IS NULL OR definition_pt = '' THEN 1 ELSE 0 END) AS empty_definition_pt,
  SUM(CASE WHEN LENGTH(COALESCE(level,'')) > 10 THEN 1 ELSE 0 END) AS bad_level
FROM words;
"""

sample_sql = """
SELECT id, english, portuguese, level,
       COALESCE(example_en, '[VAZIO]') AS example_en,
       COALESCE(example_pt, '[VAZIO]') AS example_pt
FROM words
WHERE example_en IS NULL OR example_en = '' OR example_pt IS NULL OR example_pt = ''
ORDER BY id
LIMIT 20;
"""


def run_sql(sql: str) -> str:
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
            sql,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout + ("\nERRO:\n" + result.stderr if result.stderr else "")


with open("db_query_output.txt", "w", encoding="utf-8") as f:
    f.write("=== CONTAGEM ===\n")
    f.write(run_sql(count_sql))
    f.write("\n=== AMOSTRA ===\n")
    f.write(run_sql(sample_sql))

print("OK")
