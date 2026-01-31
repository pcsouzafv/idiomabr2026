"""Audit word rows for common inconsistencies.

Goals
- Surface likely data issues that break enrichment (dictionary APIs rely on Word.english)
- Provide a safe "apply" mode for low-risk normalization (whitespace cleanup)

What it checks
- english suspicious patterns: empty, has spaces, non-ascii, too long
- portuguese suspicious patterns: empty, leading/trailing whitespace
- duplicates by lower(english)

Usage
  python backend/scripts/audit_words_db.py
  python backend/scripts/audit_words_db.py --limit 500
  python backend/scripts/audit_words_db.py --apply-normalize

Notes
- This script does NOT delete or merge duplicates (only reports them).
- For swapped english/portuguese, prefer:
    python backend/scripts/fix_words_language_fields.py --apply

"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

# Ensure backend imports resolve
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.models.word import Word


_HAS_NON_ASCII_RE = re.compile(r"[^\x00-\x7F]")


def _normalize_space(text: str) -> str:
    # collapse internal whitespace to a single space
    return " ".join(text.split())


def _is_suspicious_english(en: str) -> list[str]:
    reasons: list[str] = []
    t = (en or "").strip()
    if not t:
        reasons.append("empty")
        return reasons

    if t != en:
        reasons.append("leading/trailing whitespace")

    if _HAS_NON_ASCII_RE.search(t):
        reasons.append("non-ascii")

    if re.search(r"\s", t):
        reasons.append("has spaces")

    if len(t) > 60:
        reasons.append("too long")

    return reasons


def _is_suspicious_portuguese(pt: str) -> list[str]:
    reasons: list[str] = []
    t = (pt or "").strip()
    if not t:
        reasons.append("empty")
        return reasons

    if t != pt:
        reasons.append("leading/trailing whitespace")

    return reasons


@dataclass
class RowIssue:
    word_id: int
    english: str
    portuguese: str
    reasons: str


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Audit words table for common inconsistencies")
    p.add_argument("--limit", type=int, default=None, help="Limit rows scanned")
    p.add_argument(
        "--apply-normalize",
        action="store_true",
        help="Apply low-risk normalization (trim + collapse spaces) to english/portuguese",
    )
    p.add_argument(
        "--report",
        type=str,
        default=None,
        help="CSV output path (default: backend/data/audit_words_YYYYMMDD_HHMMSS.csv)",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    out_path: Path
    if args.report:
        out_path = Path(args.report)
    else:
        out_dir = BACKEND_DIR / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"audit_words_{ts}.csv"

    db = SessionLocal()
    try:
        q = db.query(Word)
        if args.limit:
            q = q.limit(args.limit)

        rows = q.all()
        total = len(rows)
        print(f"📦 Rows scanned: {total}")

        issues: list[RowIssue] = []
        suspicious_counts = Counter()

        for w in rows:
            en = w.english or ""
            pt = w.portuguese or ""
            reasons = []
            reasons.extend([f"english:{r}" for r in _is_suspicious_english(en)])
            reasons.extend([f"portuguese:{r}" for r in _is_suspicious_portuguese(pt)])
            if reasons:
                for r in reasons:
                    suspicious_counts[r] += 1
                issues.append(RowIssue(word_id=w.id, english=en, portuguese=pt, reasons="; ".join(reasons)))

            if args.apply_normalize:
                new_en = _normalize_space(en.strip())
                new_pt = _normalize_space(pt.strip())
                if new_en != en:
                    w.english = new_en
                if new_pt != pt:
                    w.portuguese = new_pt

        # Duplicates by lower(english)
        dup_map: dict[str, list[int]] = defaultdict(list)
        for w in rows:
            key = (w.english or "").strip().lower()
            if key:
                dup_map[key].append(w.id)
        dup_groups = {k: v for (k, v) in dup_map.items() if len(v) > 1}

        if args.apply_normalize:
            db.commit()
            print("💾 Normalização aplicada (trim + collapse spaces)")

        print("\n=== Suspicious counts ===")
        if suspicious_counts:
            for k, v in suspicious_counts.most_common():
                print(f"- {k}: {v}")
        else:
            print("- (none)")

        print("\n=== Duplicates (lower(english)) ===")
        print(f"- groups: {len(dup_groups)}")
        if len(dup_groups) > 0:
            sample = list(dup_groups.items())[:10]
            for k, ids in sample:
                print(f"  - {k}: {ids}")
            if len(dup_groups) > 10:
                print("  (showing first 10 groups)")

        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["word_id", "english", "portuguese", "reasons"]) 
            for it in issues:
                w.writerow([it.word_id, it.english, it.portuguese, it.reasons])

        print(f"\n📄 Report: {out_path}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
