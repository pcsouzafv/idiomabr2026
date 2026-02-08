"""Fix likely swapped Word.english/Word.portuguese fields.

Context
- The enrichment pipeline (dictionary APIs) uses Word.english.
- If some rows were imported with portuguese text in Word.english (and the english word
  ended up in Word.portuguese), the dictionary lookup fails.

What this script does
- Dry-run by default: prints what it *would* change.
- With --apply: swaps english <-> portuguese for high-confidence candidates.
- Always writes a CSV report with: action, reason, before/after.

Safety
- Only performs swaps when confidence is high.
- Does NOT attempt to translate content.

Usage (local)
  python backend/scripts/fix_words_language_fields.py --limit 200
  python backend/scripts/fix_words_language_fields.py --apply

Optional: restrict to a word list file (one entry per line)
  python backend/scripts/fix_words_language_fields.py --only-from-file not_found_words.txt

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

# Ensure backend imports resolve
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.word import Word


_ALLOWED_EN_CHARS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '\-./()]{0,254}$")

# Common Portuguese function words / markers that often appear in notes or phrases.
_PT_MARKERS = {
    "de",
    "do",
    "da",
    "dos",
    "das",
    "para",
    "por",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "um",
    "uma",
    "e",
    "ou",
    "com",
    "sem",
    "que",
    "como",
    "dicas",
    "palavra",
    "letra",
    "verbo",
    "passado",
}


def _has_non_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def _tokenize_lower(text: str) -> set[str]:
    return {t for t in re.split(r"\s+", text.strip().lower()) if t}


def looks_like_english(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.strip()
    if not t:
        return False
    if _has_non_ascii(t):
        return False

    # Must contain at least one A-Z letter
    if not re.search(r"[A-Za-z]", t):
        return False

    # Avoid obvious Portuguese notes/phrases (still imperfect, but helps)
    tokens = _tokenize_lower(t)
    if tokens & _PT_MARKERS:
        return False

    # Allow single words and short phrases; reject very long notes
    if len(t) > 60:
        return False

    return bool(_ALLOWED_EN_CHARS_RE.match(t))


def looks_like_portuguese(text: Optional[str]) -> bool:
    if not text:
        return False
    t = text.strip()
    if not t:
        return False

    # Any diacritics is a strong signal
    if _has_non_ascii(t):
        return True

    tokens = _tokenize_lower(t)
    if tokens & _PT_MARKERS:
        return True

    # Common Portuguese suffixes (weak signal)
    if re.search(r"(cao|coes|mente|nh|lh|ao|oes)$", t.lower()):
        return True

    return False


@dataclass
class Candidate:
    word_id: int
    english_before: str
    portuguese_before: str
    english_after: str
    portuguese_after: str
    reason: str


def load_only_set(path: Path) -> set[str]:
    items: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.add(line.lower())
    return items


def iter_candidates(words: Iterable[Word]) -> list[Candidate]:
    candidates: list[Candidate] = []

    for w in words:
        en = (w.english or "").strip()
        pt = (w.portuguese or "").strip()

        if not en or not pt:
            continue

        # High confidence swap: english looks Portuguese AND portuguese looks English
        if looks_like_portuguese(en) and looks_like_english(pt):
            candidates.append(
                Candidate(
                    word_id=w.id,
                    english_before=en,
                    portuguese_before=pt,
                    english_after=pt,
                    portuguese_after=en,
                    reason="swap: english looks PT, portuguese looks EN",
                )
            )
            continue

        # Also catch common import mistake: english has diacritics and portuguese has none.
        if _has_non_ascii(en) and not _has_non_ascii(pt) and looks_like_english(pt):
            candidates.append(
                Candidate(
                    word_id=w.id,
                    english_before=en,
                    portuguese_before=pt,
                    english_after=pt,
                    portuguese_after=en,
                    reason="swap: english has diacritics; portuguese looks EN",
                )
            )

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix swapped Word.english/Word.portuguese fields")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to scan")
    parser.add_argument(
        "--only-from-file",
        type=str,
        default=None,
        help="Optional: only consider rows whose english matches any line in this file (case-insensitive)",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path to write CSV report (default: backend/data/fix_words_language_fields_YYYYMMDD_HHMMSS.csv)",
    )

    args = parser.parse_args()

    only_set: Optional[set[str]] = None
    if args.only_from_file:
        p = Path(args.only_from_file)
        if not p.exists():
            print(f"❌ File not found: {p}")
            return 2
        only_set = load_only_set(p)
        print(f"🔎 Restricting to {len(only_set)} entries from {p}")

    report_path = Path(args.report) if args.report else None
    if report_path is None:
        out_dir = BACKEND_DIR / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = out_dir / f"fix_words_language_fields_{ts}.csv"

    db = SessionLocal()
    try:
        query = db.query(Word)
        if only_set is not None:
            # SQL lower() match against provided set; for large sets this is not ideal,
            # but it's OK for a few hundred lines.
            query = query.filter(func.lower(Word.english).in_(list(only_set)))

        if args.limit:
            query = query.limit(args.limit)

        words = query.all()
        print(f"📦 Rows scanned: {len(words)}")

        candidates = iter_candidates(words)
        print(f"✅ Swap candidates (high confidence): {len(candidates)}")

        with report_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "word_id",
                    "action",
                    "reason",
                    "english_before",
                    "portuguese_before",
                    "english_after",
                    "portuguese_after",
                ]
            )

            for c in candidates:
                writer.writerow(
                    [
                        c.word_id,
                        "swap",
                        c.reason,
                        c.english_before,
                        c.portuguese_before,
                        c.english_after,
                        c.portuguese_after,
                    ]
                )

        if not candidates:
            print(f"📝 Report written: {report_path}")
            print("Nada para fazer (nenhum caso de swap com alta confiança).")
            return 0

        # Print a small preview
        print("\nPreview (first 20):")
        for c in candidates[:20]:
            print(f"- id={c.word_id}: '{c.english_before}' ↔ '{c.portuguese_before}'")

        if not args.apply:
            print("\nℹ️  Dry-run (no changes applied).")
            print(f"📝 Report written: {report_path}")
            print("Para aplicar os swaps: use --apply")
            return 0

        # Apply changes
        for c in candidates:
            w = db.query(Word).filter(Word.id == c.word_id).first()
            if not w:
                continue
            w.english = c.english_after
            w.portuguese = c.portuguese_after

        db.commit()
        print("\n💾 Changes committed.")
        print(f"📝 Report written: {report_path}")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
