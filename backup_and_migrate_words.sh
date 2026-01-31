#!/usr/bin/env bash
set -euo pipefail

# Backup + migration for words schema (safe: only adds columns)
# You can override defaults by exporting POSTGRES_USER / POSTGRES_DB before running.

POSTGRES_USER="${POSTGRES_USER:-idiomasbr}"
POSTGRES_DB="${POSTGRES_DB:-idiomasbr}"
TS="$(date +%Y%m%d_%H%M%S)"

mkdir -p backups/db

echo "[1/3] Starting postgres container..."
docker compose up -d postgres

echo "[2/3] Creating backup backups/db/${POSTGRES_DB}_backup_${TS}.sql ..."
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "backups/db/${POSTGRES_DB}_backup_${TS}.sql"

echo "[3/3] Applying migration backend/migrations/add_word_details.sql ..."
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backend/migrations/add_word_details.sql

echo
echo "Done. Backup saved to backups/db/${POSTGRES_DB}_backup_${TS}.sql"
