#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Erro: arquivo de ambiente não encontrado: $ENV_FILE" >&2
  echo "Crie um .env baseado em .env.example e defina POSTGRES_PASSWORD e SECRET_KEY." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${POSTGRES_USER:=idiomasbr}"
: "${POSTGRES_DB:=idiomasbr}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required in $ENV_FILE}"

mkdir -p "$BACKUP_DIR"

TS="$(date +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/idiomasbr_${POSTGRES_DB}_${TS}.sql.gz"

echo "📦 Backup do Postgres -> $OUT"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$OUT"

echo "🧹 Retenção: removendo backups > ${RETENTION_DAYS} dias"
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete || true

echo "✅ Backup concluído"
