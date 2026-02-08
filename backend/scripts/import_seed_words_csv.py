"""Importa palavras de um CSV (seed list) para a tabela words.

Objetivo:
- Permitir crescimento do vocabulário (10k/20k/...) via listas-semente.
- As APIs de dicionário enriquecem palavras existentes, mas não enumeram palavras.

Formato esperado (compatível com generate_seed_words_extra.py):
- CSV delimitado por ';'
- Cabeçalho: english;ipa;portuguese;level;tags

Modo padrão é DRY-RUN. Use --apply para gravar.

Exemplos:
  docker exec -i idiomasbr-backend python scripts/import_seed_words_csv.py --file data/seed_words_extra_unique_v2.csv
  docker exec -i idiomasbr-backend python scripts/import_seed_words_csv.py --file data/seed_words_extra_unique_v2.csv --apply
  docker exec -i idiomasbr-backend python scripts/import_seed_words_csv.py --file data/seed_words_extra_unique_v2.csv --apply --update-existing

Notas:
- Dedupe por lower(english).
- Não altera IDs existentes (seguro para FKs).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.models.word import Word

_HEADWORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _looks_like_headword(s: str) -> bool:
    t = _norm(s)
    if not t or len(t) > 80:
        return False
    return bool(_HEADWORD_TOKEN_RE.match(t))


def _merge_tags(existing: str | None, new_tags: str | None) -> str:
    ex = [t.strip() for t in (existing or "").split(",") if t.strip()]
    nw = [t.strip() for t in (new_tags or "").split(",") if t.strip()]
    seen: set[str] = set()
    merged: list[str] = []
    for t in ex + nw:
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        merged.append(t)
    return ", ".join(merged)


@dataclass(frozen=True)
class SeedRow:
    english: str
    ipa: str
    portuguese: str
    level: str
    tags: str


def _read_csv(path: Path) -> list[SeedRow]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        required = {"english", "ipa", "portuguese", "level", "tags"}
        if not reader.fieldnames:
            raise SystemExit("CSV sem cabeçalho")
        missing = required.difference({h.strip() for h in reader.fieldnames if h})
        if missing:
            raise SystemExit(f"CSV inválido: faltando colunas {sorted(missing)}")

        rows: list[SeedRow] = []
        for raw in reader:
            english = _norm(raw.get("english"))
            ipa = _norm(raw.get("ipa"))
            portuguese = _norm(raw.get("portuguese"))
            level = _norm(raw.get("level"))
            tags = _norm(raw.get("tags"))
            if not english:
                continue
            rows.append(SeedRow(english=english, ipa=ipa, portuguese=portuguese, level=level, tags=tags))
        return rows


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Importa CSV de palavras (seed list) para o banco")
    p.add_argument(
        "--file",
        required=True,
        help="Caminho do CSV dentro do container (ex: data/seed_words_extra_unique_v2.csv)",
    )
    p.add_argument("--apply", action="store_true", help="Grava alterações no banco")
    p.add_argument(
        "--update-existing",
        action="store_true",
        help="Atualiza campos vazios e faz merge de tags em palavras já existentes",
    )
    p.add_argument(
        "--commit-every",
        type=int,
        default=500,
        help="Commit a cada N inserts/updates quando usar --apply (0 = commit só no final)",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    csv_path = Path(args.file)
    if not csv_path.is_absolute():
        # Dentro do container, scripts rodam em /app. data/ fica em /app/data.
        csv_path = Path("/app") / csv_path

    if not csv_path.exists():
        raise SystemExit(f"Arquivo não encontrado: {csv_path}")

    seed_rows = _read_csv(csv_path)

    # Normaliza e valida headwords
    valid_rows: list[SeedRow] = []
    skipped_invalid = 0
    for r in seed_rows:
        if not _looks_like_headword(r.english):
            skipped_invalid += 1
            continue
        valid_rows.append(r)

    db = SessionLocal()
    try:
        # Índice: english_lower -> Word
        existing_words: dict[str, Word] = {}
        for w in db.query(Word).all():
            key = _norm(w.english).lower()
            if key and key not in existing_words:
                existing_words[key] = w

        inserted = 0
        updated = 0
        unchanged_existing = 0
        total_changes = 0

        for r in valid_rows:
            key = r.english.lower()
            w = existing_words.get(key)

            if w is None:
                w = Word(
                    english=r.english,
                    ipa=r.ipa,
                    portuguese=r.portuguese,
                    level=r.level or None,
                    tags=r.tags or None,
                )
                db.add(w)
                inserted += 1
                total_changes += 1
            else:
                if not args.update_existing:
                    unchanged_existing += 1
                    continue

                changed = False

                # Só preenche campos vazios (não sobrescreve conteúdo existente)
                if r.portuguese and not _norm(w.portuguese):
                    w.portuguese = r.portuguese
                    changed = True
                if r.ipa and not _norm(w.ipa):
                    w.ipa = r.ipa
                    changed = True
                if r.level and not _norm(w.level):
                    w.level = r.level or None  # type: ignore[assignment]
                    changed = True

                merged = _merge_tags(w.tags, r.tags)
                if merged != _norm(w.tags):
                    w.tags = merged or None
                    changed = True

                if changed:
                    updated += 1
                    total_changes += 1
                else:
                    unchanged_existing += 1

            if args.apply and args.commit_every and total_changes % args.commit_every == 0:
                db.commit()

        if args.apply:
            db.commit()
        else:
            db.rollback()

        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"📥 CSV rows: {len(seed_rows)}")
        print(f"✅ Valid headwords: {len(valid_rows)}")
        if skipped_invalid:
            print(f"⏭️  Skipped invalid headwords: {skipped_invalid}")
        print(f"🧪 Mode: {mode}")
        print(f"➕ Inserted: {inserted}")
        print(f"✏️  Updated existing: {updated}" if args.update_existing else "✏️  Updated existing: 0 (disabled)")
        print(f"➖ Existing unchanged/skipped: {unchanged_existing}")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
