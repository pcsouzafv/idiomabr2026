"""Fix a common import issue where fields are rotated: (pt -> english), (ipa -> portuguese), (en -> ipa).

Observed pattern in DB:
- english column contains Portuguese phrase/translation
- portuguese column contains IPA transcription
- ipa column contains the English headword

Desired fix:
  new_english   = old_ipa
  new_portuguese= old_english
  new_ipa       = old_portuguese

This script is DRY-RUN by default. Use --apply to persist changes.

Usage:
  docker exec -i idiomasbr-backend python scripts/fix_rotated_fields_pt_ipa_en.py
  docker exec -i idiomasbr-backend python scripts/fix_rotated_fields_pt_ipa_en.py --limit 2000
  docker exec -i idiomasbr-backend python scripts/fix_rotated_fields_pt_ipa_en.py --apply

Output:
- CSV report under /app/data by default (backend/data on host)

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

from app.core.database import SessionLocal
from app.models.word import Word


_HEADWORD_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")

# A conservative set of very common IPA symbols / marks.
_IPA_HINT_CHARS = set(
    "əɪʊɛɔɑɜɒθðŋæʃʒʊʌɡɾɲʎɐɨɘɯʔˈˌːˑ̃"
)

_PT_COMMON_WORDS = {
    "de",
    "do",
    "da",
    "dos",
    "das",
    "para",
    "por",
    "com",
    "como",
    "uma",
    "um",
    "antes",
    "depois",
    "passado",
    "enviar",
    "casa",
    "palavra",
    "dicas",
}


def _looks_like_headword(s: str) -> bool:
    t = (s or "").strip()
    if not t or len(t) > 60:
        return False
    # avoid numbers/punctuation-heavy strings
    return bool(_HEADWORD_RE.match(t))


def _looks_like_ipa(s: str) -> bool:
    t = (s or "").strip()
    if not t or len(t) > 80:
        return False
    # explicit slashes/brackets are strong hints
    if "/" in t or "[" in t or "]" in t:
        return True
    # non-ascii often indicates IPA symbols
    if any(ord(ch) > 127 for ch in t):
        return True
    if any(ch in _IPA_HINT_CHARS for ch in t):
        return True
    return False


def _looks_like_portuguese_phrase(s: str) -> bool:
    t = (s or "").strip().lower()
    if not t:
        return False
    if any(ch in t for ch in "ãõáàâéêíóôúç"):  # Portuguese diacritics
        return True
    if " " in t:
        words = set(re.findall(r"[a-zà-ÿ]+", t))
        if len(words & _PT_COMMON_WORDS) >= 1:
            return True
    return False


@dataclass
class FixCandidate:
    word_id: int
    old_english: str
    old_portuguese: str
    old_ipa: str
    new_english: str
    new_portuguese: str
    new_ipa: str
    reason: str


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Fix rotated fields (pt->english, ipa->portuguese, en->ipa)")
    p.add_argument("--limit", type=int, default=None, help="Limit rows scanned")
    p.add_argument("--apply", action="store_true", help="Apply changes to DB")
    p.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow setting english to a value that already exists in another row (may create duplicates)",
    )
    p.add_argument(
        "--report",
        type=str,
        default=None,
        help="CSV output path (default: backend/data/fix_rotated_fields_YYYYMMDD_HHMMSS.csv)",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    out_path: Path
    if args.report:
        out_path = Path(args.report)
    else:
        out_dir = BACKEND_DIR / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"fix_rotated_fields_{ts}.csv"

    db = SessionLocal()
    try:
        q = db.query(Word)
        if args.limit:
            q = q.limit(args.limit)
        rows = q.all()

        # Precompute existing headwords for safe duplicate avoidance.
        existing_headwords: dict[str, int] = {}
        for wid, en in db.query(Word.id, Word.english).all():
            key = (en or "").strip().lower()
            if key and key not in existing_headwords:
                existing_headwords[key] = wid

        candidates: list[FixCandidate] = []
        skipped_duplicates = 0

        for w in rows:
            old_en = w.english or ""
            old_pt = w.portuguese or ""
            old_ipa = w.ipa or ""

            if not (_looks_like_headword(old_ipa) and _looks_like_ipa(old_pt)):
                continue

            # If ipa column looks like an English headword and portuguese column looks like IPA,
            # this is almost certainly the rotated-import pattern. Keep a couple of safety guards.
            if not old_en.strip():
                continue
            if old_en.strip().lower() == old_ipa.strip().lower():
                continue
            if len(old_en) > 200:
                continue
            # Avoid rotating if english itself looks like IPA (very unlikely a translation).
            if _looks_like_ipa(old_en):
                continue

            # If english looks like Portuguese (diacritics/common words), great; otherwise still allow,
            # because many PT words are ASCII-only (e.g. "acima") and would be missed.
            # This is intentionally permissive but still anchored on ipa/portuguese strong signals.

            new_en = old_ipa.strip()
            new_pt = old_en.strip()
            new_ipa = old_pt.strip()

            if not args.allow_duplicates:
                existing_id = existing_headwords.get(new_en.lower())
                if existing_id is not None and existing_id != w.id:
                    skipped_duplicates += 1
                    continue

            if new_en == old_en and new_pt == old_pt and new_ipa == old_ipa:
                continue

            candidates.append(
                FixCandidate(
                    word_id=w.id,
                    old_english=old_en,
                    old_portuguese=old_pt,
                    old_ipa=old_ipa,
                    new_english=new_en,
                    new_portuguese=new_pt,
                    new_ipa=new_ipa,
                    reason="rotate: english(pt), portuguese(ipa), ipa(en)",
                )
            )

            if args.apply:
                w.english = new_en
                w.portuguese = new_pt
                w.ipa = new_ipa

        if args.apply:
            db.commit()

        print(f"📦 Rows scanned: {len(rows)}")
        print(f"✅ Candidates: {len(candidates)}")
        if not args.allow_duplicates:
            print(f"⏭️  Skipped (duplicate headword exists): {skipped_duplicates}")
        print(f"🧪 Mode: {'APPLY' if args.apply else 'DRY-RUN'}")

        # Write report
        with out_path.open("w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(
                [
                    "word_id",
                    "old_english",
                    "old_portuguese",
                    "old_ipa",
                    "new_english",
                    "new_portuguese",
                    "new_ipa",
                    "reason",
                ]
            )
            for c in candidates:
                wr.writerow(
                    [
                        c.word_id,
                        c.old_english,
                        c.old_portuguese,
                        c.old_ipa,
                        c.new_english,
                        c.new_portuguese,
                        c.new_ipa,
                        c.reason,
                    ]
                )

        print(f"📄 Report: {out_path}")

        # Print a small sample
        for c in candidates[:10]:
            print(
                f"- {c.word_id}: '{c.old_english}' | '{c.old_portuguese}' | '{c.old_ipa}'"
                f"  =>  '{c.new_english}' | '{c.new_portuguese}' | '{c.new_ipa}'"
            )

        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
