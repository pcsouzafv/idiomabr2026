"""
Corrige registros corrompidos no banco usando um CSV fonte confiável.

Uso:
  python scripts/fix_corrupted_from_csv.py \
    --source-csv /app/words_export_3.csv \
    --ids-csv /app/corrupted_data.csv \
    --apply

Sem --apply roda em modo DRY-RUN.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.database import SessionLocal
from app.models.word import Word


@dataclass
class WordData:
    id: int
    english: str
    ipa: Optional[str]
    portuguese: str
    level: str
    word_type: Optional[str]
    definition_en: Optional[str]
    definition_pt: Optional[str]
    example_en: Optional[str]
    example_pt: Optional[str]
    tags: Optional[str]


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def read_words(csv_path: Path) -> dict[int, WordData]:
    data: dict[int, WordData] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("id"):
                continue
            try:
                word_id = int(row["id"])
            except ValueError:
                continue

            data[word_id] = WordData(
                id=word_id,
                english=_clean(row.get("english")) or "",
                ipa=_clean(row.get("ipa")),
                portuguese=_clean(row.get("portuguese")) or "",
                level=_clean(row.get("level")) or "A1",
                word_type=_clean(row.get("word_type")),
                definition_en=_clean(row.get("definition_en")),
                definition_pt=_clean(row.get("definition_pt")),
                example_en=_clean(row.get("example_en")),
                example_pt=_clean(row.get("example_pt")),
                tags=_clean(row.get("tags")),
            )
    return data


def read_ids(csv_path: Path) -> set[int]:
    ids: set[int] = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("id"):
                continue
            try:
                ids.add(int(row["id"]))
            except ValueError:
                continue
    return ids


def apply_updates(source: dict[int, WordData], ids: set[int], apply: bool) -> tuple[int, int]:
    db = SessionLocal()
    updated = 0
    skipped = 0

    try:
        for word_id in ids:
            src = source.get(word_id)
            if not src:
                skipped += 1
                continue

            word: Word | None = db.query(Word).filter(Word.id == word_id).first()
            if not word:
                skipped += 1
                continue

            changed = False

            def set_if_value(attr: str, value: Optional[str]):
                nonlocal changed
                if value is None:
                    return
                if getattr(word, attr) != value:
                    setattr(word, attr, value)
                    changed = True

            set_if_value("english", src.english)
            set_if_value("ipa", src.ipa)
            set_if_value("portuguese", src.portuguese)
            set_if_value("level", src.level)
            set_if_value("word_type", src.word_type)
            set_if_value("definition_en", src.definition_en)
            set_if_value("definition_pt", src.definition_pt)
            set_if_value("example_en", src.example_en)
            set_if_value("example_pt", src.example_pt)
            set_if_value("tags", src.tags)

            if changed:
                updated += 1

        if apply:
            db.commit()
        else:
            db.rollback()

        return updated, skipped

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Corrigir dados corrompidos via CSV fonte")
    parser.add_argument("--source-csv", required=True, help="CSV fonte confiável")
    parser.add_argument("--ids-csv", required=True, help="CSV com IDs problemáticos")
    parser.add_argument("--apply", action="store_true", help="Aplicar no banco")
    args = parser.parse_args()

    source_csv = Path(args.source_csv)
    ids_csv = Path(args.ids_csv)

    if not source_csv.exists():
        raise SystemExit(f"CSV fonte não encontrado: {source_csv}")
    if not ids_csv.exists():
        raise SystemExit(f"CSV de IDs não encontrado: {ids_csv}")

    print("\n========================================")
    print("🔧 CORRIGINDO DADOS CORROMPIDOS")
    print("========================================")
    print(f"Fonte: {source_csv}")
    print(f"IDs:   {ids_csv}")

    source = read_words(source_csv)
    ids = read_ids(ids_csv)

    print(f"Total IDs problemáticos: {len(ids)}")
    print(f"Registros disponíveis na fonte: {len(source)}")

    updated, skipped = apply_updates(source, ids, args.apply)

    print("\n========================================")
    if args.apply:
        print("✅ Atualizações aplicadas!")
    else:
        print("🧪 DRY-RUN (nada aplicado)")
    print(f"Atualizados: {updated}")
    print(f"Ignorados:   {skipped}")
    print("========================================")


if __name__ == "__main__":
    main()
