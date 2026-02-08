"""Clean word list text files and extract English headwords.

Why
- Files like not_found_words.txt / missing_definition_en.txt currently mix:
  - English headwords (good)
  - Portuguese translations/notes (bad for English dictionary lookup)
  - multi-word phrases (often unsupported by dictionary endpoints)
  - truncated items (e.g. trailing '-')
  - patterns like afterward(s) or airplane/plane

What this script does
- Reads one or more input .txt files (one entry per line)
- Produces, for each input:
  - <name>.cleaned_en.txt   : unique, normalized English headwords (one per line)
  - <name>.removed.txt      : original lines that were not kept
  - <name>.report.csv       : line-by-line decision with reason

Notes
- By default it keeps ONLY single-token headwords suitable for dictionary APIs.
- It expands common shorthand patterns:
  - afterward(s) => afterward, afterwards
  - airplane/plane => airplane, plane

Usage
  python backend/scripts/clean_word_lists.py not_found_words.txt missing_definition_en.txt

"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


_SINGLE_WORD_RE = re.compile(r"^[A-Za-z](?:[A-Za-z'\-]{0,48}[A-Za-z])?$")


@dataclass
class Decision:
    source_line: str
    kept: List[str]
    reason: str


def normalize_token(token: str) -> str:
    token = token.strip()
    # strip common trailing punctuation
    token = token.strip("\t \r\n,;:!?")
    # collapse dots in common abbreviations: mrs. -> mrs
    if token.endswith("."):
        token = token[:-1]
    return token


def expand_shorthand(text: str) -> List[str]:
    """Expand a line into candidate tokens."""
    t = text.strip()
    if not t:
        return []

    # Discard comments/obvious notes
    if t.startswith("#"):
        return []

    # If contains spaces -> multi-word phrase; not suitable for dictionary headword endpoint
    # Keep it for removed list.
    if re.search(r"\s", t):
        return []

    t = normalize_token(t)
    if not t:
        return []

    # Expand word(s) pattern at end or in middle: afterward(s)
    m = re.fullmatch(r"([A-Za-z'\-]+)\(([^)]+)\)([A-Za-z'\-]*)", t)
    if m:
        base = (m.group(1) + m.group(3)).strip()
        opt = m.group(2).strip()
        # only expand simple optional suffix like (s) or (es)
        if base and opt and re.fullmatch(r"[A-Za-z]{1,4}", opt):
            return [base, base + opt]
        return []

    # Expand a/b pattern: airplane/plane
    if "/" in t:
        parts = [p for p in t.split("/") if p.strip()]
        if len(parts) == 2:
            return [normalize_token(parts[0]), normalize_token(parts[1])]
        return []

    return [t]


def is_good_headword(token: str) -> bool:
    if not token:
        return False

    # Reject trailing hyphen (truncated)
    if token.endswith("-"):
        return False

    # Reject tokens with non-ascii letters (diacritics)
    try:
        token.encode("ascii")
    except UnicodeEncodeError:
        return False

    return bool(_SINGLE_WORD_RE.fullmatch(token))


def decide_line(line: str) -> Decision:
    raw = line.rstrip("\r\n")
    stripped = raw.strip()

    if not stripped:
        return Decision(source_line=raw, kept=[], reason="empty")

    # Lines that look like notes/definitions
    if "(" in stripped and ")" in stripped and re.search(r"\b(et cetera|ante meridian|post)\b", stripped, re.I):
        return Decision(source_line=raw, kept=[], reason="note/abbrev")

    # Any obvious Portuguese markers: keep out
    if re.search(r"[áàâãéêíóôõúç]", stripped, re.I):
        return Decision(source_line=raw, kept=[], reason="non-ascii (likely PT)")

    # Multi-word phrases are not supported as a single headword
    if re.search(r"\s", stripped):
        return Decision(source_line=raw, kept=[], reason="multi-word phrase")

    candidates = expand_shorthand(stripped)
    if not candidates:
        # Try a last normalization pass
        token = normalize_token(stripped)
        if is_good_headword(token):
            return Decision(source_line=raw, kept=[token.lower()], reason="kept")
        return Decision(source_line=raw, kept=[], reason="no candidates")

    good: List[str] = []
    bad_any = False
    for c in candidates:
        c2 = normalize_token(c)
        if is_good_headword(c2):
            good.append(c2.lower())
        else:
            bad_any = True

    if good:
        reason = "kept"
        if bad_any:
            reason = "partial kept (some candidates rejected)"
        return Decision(source_line=raw, kept=good, reason=reason)

    return Decision(source_line=raw, kept=[], reason="rejected")


def process_file(path: Path) -> Tuple[List[str], List[Decision]]:
    lines = path.read_text(encoding="utf-8").splitlines()

    kept: List[str] = []
    decisions: List[Decision] = []

    for line in lines:
        d = decide_line(line)
        decisions.append(d)
        kept.extend(d.kept)

    # unique + stable sort for deterministic output
    kept_unique = sorted(set(kept))
    return kept_unique, decisions


def write_outputs(input_path: Path, kept: Sequence[str], decisions: Sequence[Decision]) -> None:
    cleaned_path = input_path.with_suffix(input_path.suffix + ".cleaned_en.txt")
    removed_path = input_path.with_suffix(input_path.suffix + ".removed.txt")
    report_path = input_path.with_suffix(input_path.suffix + ".report.csv")

    cleaned_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")

    removed_lines: List[str] = []
    for d in decisions:
        if not d.kept and d.source_line.strip():
            removed_lines.append(d.source_line)
    removed_path.write_text("\n".join(removed_lines) + ("\n" if removed_lines else ""), encoding="utf-8")

    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_line", "kept_tokens", "reason"])
        for d in decisions:
            writer.writerow([d.source_line, "|".join(d.kept), d.reason])


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean word list files and extract English headwords")
    parser.add_argument("files", nargs="+", help="Input .txt files")
    args = parser.parse_args(list(argv) if argv is not None else None)

    for file_str in args.files:
        p = Path(file_str)
        if not p.exists():
            print(f"❌ Not found: {p}")
            return 2

        kept, decisions = process_file(p)
        write_outputs(p, kept, decisions)

        removed_count = sum(1 for d in decisions if (not d.kept and d.source_line.strip()))
        print(f"✅ {p}: kept {len(kept)} headwords; removed {removed_count} lines")
        print(f"   -> {p.name}.cleaned_en.txt")
        print(f"   -> {p.name}.removed.txt")
        print(f"   -> {p.name}.report.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
