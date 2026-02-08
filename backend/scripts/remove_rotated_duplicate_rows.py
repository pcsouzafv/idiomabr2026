"""Remove bad rows created by rotated-import duplicates.

Pattern (bad row):
- english: Portuguese translation (often ASCII-only or phrase)
- portuguese: IPA transcription (often non-ascii)
- ipa: English headword token

Safe removal condition:
- There exists a target row where Word.english == bad_row.ipa (case-insensitive)
- Target row appears "good" (has definition_en or word_type)

Default is DRY-RUN (no DB changes). Use --apply to delete.

Usage:
  docker exec -i idiomasbr-backend python scripts/remove_rotated_duplicate_rows.py
  docker exec -i idiomasbr-backend python scripts/remove_rotated_duplicate_rows.py --limit 2000
  docker exec -i idiomasbr-backend python scripts/remove_rotated_duplicate_rows.py --apply

Outputs a CSV report under /app/data (host: backend/data).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, literal, select, update
from sqlalchemy.sql import exists as sql_exists

from app.core.database import SessionLocal
from app.models.progress import UserProgress
from app.models.review import Review
from app.models.word import Word


_HEADWORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")
_HAS_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def _looks_like_headword(s: str) -> bool:
    t = (s or "").strip()
    if not t or len(t) > 60:
        return False
    return bool(_HEADWORD_TOKEN_RE.match(t))


def _looks_like_ipa(s: str) -> bool:
    t = (s or "").strip()
    if not t or len(t) > 120:
        return False
    if _HAS_NON_ASCII_RE.search(t):
        return True
    if "/" in t or "[" in t or "]" in t:
        return True
    return False


def _is_target_good(target: Word) -> bool:
    # Conservative: at least one of these indicates the row is already enriched / valid.
    if target.definition_en and target.definition_en.strip():
        return True
    if target.word_type and target.word_type.strip():
        return True
    return False


@dataclass
class Candidate:
    bad_id: int
    bad_english: str
    bad_portuguese: str
    bad_ipa: str
    target_id: int
    target_english: str
    target_portuguese: str
    target_ipa: str
    action: str


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Remove rotated-import duplicate rows safely")
    p.add_argument("--limit", type=int, default=None, help="Limit rows scanned")
    p.add_argument("--apply", action="store_true", help="Delete safe candidates")
    p.add_argument(
        "--commit-every",
        type=int,
        default=200,
        help="Commit every N deletions when using --apply",
    )
    p.add_argument(
        "--report",
        type=str,
        default=None,
        help="CSV output path (default: backend/data/remove_rotated_duplicates_YYYYMMDD_HHMMSS.csv)",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    out_path: Path
    if args.report:
        out_path = Path(args.report)
    else:
        out_dir = BACKEND_DIR / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"remove_rotated_duplicates_{ts}.csv"

    db = SessionLocal()
    try:
        q = db.query(Word)
        if args.limit:
            q = q.limit(args.limit)
        rows = q.all()

        candidates: list[Candidate] = []
        deletions = 0
        skipped_target_incomplete = 0

        # Pre-index targets by lower(english)
        targets: dict[str, Word] = {}
        for w in rows:
            key = (w.english or "").strip().lower()
            if key and key not in targets:
                targets[key] = w

        for w in rows:
            bad_ipa = (w.ipa or "").strip()
            bad_pt = (w.portuguese or "").strip()
            bad_en = (w.english or "").strip()

            if not (_looks_like_headword(bad_ipa) and _looks_like_ipa(bad_pt)):
                continue

            target = targets.get(bad_ipa.lower())
            if not target or target.id == w.id:
                continue

            if not _is_target_good(target):
                skipped_target_incomplete += 1
                action = "skip_target_incomplete"
            else:
                action = "delete_bad_row"

            candidates.append(
                Candidate(
                    bad_id=w.id,
                    bad_english=bad_en,
                    bad_portuguese=bad_pt,
                    bad_ipa=bad_ipa,
                    target_id=target.id,
                    target_english=(target.english or ""),
                    target_portuguese=(target.portuguese or ""),
                    target_ipa=(target.ipa or ""),
                    action=action,
                )
            )

        if args.apply:
            try:
                for c in candidates:
                    if c.action != "delete_bad_row":
                        continue

                    # 1) Dedupe progress rows: if user already has progress for target word,
                    # delete the progress row that points to the bad word.
                    up = UserProgress.__table__
                    up2 = up.alias("up2")

                    target_progress_exists = (
                        sql_exists(
                            select(literal(1))
                            .select_from(up2)
                            .where(up2.c.user_id == up.c.user_id)
                            .where(up2.c.word_id == c.target_id)
                        )
                    )

                    dup_progress_delete = delete(up).where(up.c.word_id == c.bad_id).where(target_progress_exists)
                    db.execute(dup_progress_delete)

                    # 2) Move remaining progress to the target word.
                    db.execute(update(up).where(up.c.word_id == c.bad_id).values(word_id=c.target_id))

                    # 3) Move reviews to the target word (FK must not reference deleted word).
                    rv = Review.__table__
                    db.execute(update(rv).where(rv.c.word_id == c.bad_id).values(word_id=c.target_id))

                    # 4) Delete the bad word row (core delete avoids ORM nullification behavior).
                    db.execute(delete(Word.__table__).where(Word.__table__.c.id == c.bad_id))
                    deletions += 1

                    if args.commit_every and deletions % args.commit_every == 0:
                        db.commit()

                db.commit()
            except Exception:
                db.rollback()
                raise

        with out_path.open("w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(
                [
                    "bad_id",
                    "bad_english",
                    "bad_portuguese",
                    "bad_ipa",
                    "target_id",
                    "target_english",
                    "target_portuguese",
                    "target_ipa",
                    "action",
                ]
            )
            for c in candidates:
                wr.writerow(
                    [
                        c.bad_id,
                        c.bad_english,
                        c.bad_portuguese,
                        c.bad_ipa,
                        c.target_id,
                        c.target_english,
                        c.target_portuguese,
                        c.target_ipa,
                        c.action,
                    ]
                )

        print(f"📦 Rows scanned: {len(rows)}")
        print(f"🔎 Candidates: {len(candidates)}")
        print(f"⏭️  Skipped (target incomplete): {skipped_target_incomplete}")
        print(f"🧪 Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
        if args.apply:
            print(f"🗑️  Deleted: {deletions}")
        print(f"📄 Report: {out_path}")

        for c in candidates[:10]:
            print(f"- bad#{c.bad_id} '{c.bad_english}' / '{c.bad_portuguese}' / '{c.bad_ipa}' -> target#{c.target_id} '{c.target_english}' ({c.action})")

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
