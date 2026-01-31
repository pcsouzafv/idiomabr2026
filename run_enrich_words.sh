#!/usr/bin/env bash
set -euo pipefail

# Runs bulk word enrichment inside the backend container.
# Avoids copy/paste issues in terminals.

DELAY="${DELAY:-0.3}"
COMMIT_EVERY="${COMMIT_EVERY:-50}"
LIMIT="${LIMIT:-}"

echo "Starting required containers..."
docker compose up -d postgres backend

LIMIT_ARG=()
if [[ -n "$LIMIT" ]]; then
  LIMIT_ARG=(--limit "$LIMIT")
fi

echo
echo "Running enrichment:"
echo "  python enrich_words_api.py ${LIMIT:+--limit $LIMIT} --delay $DELAY --commit-every $COMMIT_EVERY"
echo

docker compose exec backend python enrich_words_api.py "${LIMIT_ARG[@]}" --delay "$DELAY" --commit-every "$COMMIT_EVERY"

echo
echo "Done."
