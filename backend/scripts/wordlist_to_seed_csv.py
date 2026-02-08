"""Generate a seed CSV from a plain English wordlist.

Why
- The DB requires `words.portuguese` (NOT NULL), so importing "english-only" lists
  needs a translation step before import.
- This script converts: one word per line -> CSV compatible with `scripts/import_seed_words_csv.py`.

Input
- A text file with one English token per line.
  - Comments starting with # are ignored.
  - Blank lines are ignored.
  - Only single-token headwords are accepted by default (A–Z with apostrophes/hyphen).

Translation
- Uses MyMemory (en|pt-br) by default.
- Maintains a persistent JSON cache so you can resume later.
- Words that can't be translated are skipped by default (keeps output import-safe).

Usage (inside docker container):
  python scripts/wordlist_to_seed_csv.py --in data/wordlist_20k.txt --out data/seed_20k.csv --tag pack:20k

Then import:
  python scripts/import_seed_words_csv.py --file data/seed_20k.csv --apply

Notes
- This script does NOT store course text or phrases (only tokens).
- For large runs (20k), expect hours due to polite rate limiting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

import requests


_HEADWORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")


def _normalize_token(token: str) -> str:
    return (
        (token or "")
        .strip()
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )


def _looks_like_headword(token: str, *, max_len: int = 60) -> bool:
    t = _normalize_token(token)
    if not t or len(t) > max_len:
        return False
    return bool(_HEADWORD_TOKEN_RE.match(t))


def _iter_wordlist_lines(path: Path) -> Iterator[str]:
    # Try UTF-8; fall back to latin-1.
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1", errors="replace")

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        # Allow inline comments: word # comment
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        yield line


def _load_cache(path: Path) -> Dict[str, Optional[str]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out: Dict[str, Optional[str]] = {}
            for k, v in data.items():
                if isinstance(k, str):
                    out[k] = v if isinstance(v, str) or v is None else None
            return out
    except Exception:
        pass
    return {}


def _save_cache(path: Path, cache: Dict[str, Optional[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _clean_translation_output(text: str) -> str:
    if not text:
        return ""
    out = str(text).strip()
    # Keep only first line.
    if "\n" in out:
        out = out.split("\n", 1)[0].strip()
    # Trim surrounding quotes.
    if (out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'")):
        out = out[1:-1].strip()
    # Remove trailing punctuation that models sometimes add.
    out = out.strip().strip(".").strip()
    return out


def _llm_client_for_provider(provider: str):
    """Returns an OpenAI-compatible client for the given provider.

    Uses the same configuration style as backend/app/services/ai_teacher.py.
    Import is local to avoid requiring the package when using MyMemory.
    """

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "OpenAI Python package not available. Install 'openai' or use --provider mymemory."
        ) from e

    p = provider.lower().strip()
    if p == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        return OpenAI(api_key=api_key)

    if p == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    raise ValueError(f"Unsupported LLM provider: {provider}")


def _translate_en_to_pt_llm(
    client,
    provider: str,
    word: str,
    *,
    model: str,
    timeout: float = 30.0,
) -> Optional[str]:
    """Translate a single English headword to pt-BR via an LLM provider."""

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a translation engine. Translate single English words to Brazilian Portuguese. "
                    "Return ONLY the translation (no quotes, no punctuation, no explanations)."
                ),
            },
            {"role": "user", "content": f"English word: {word}\nPortuguese (pt-BR):"},
        ]

        # OpenAI-compatible API (OpenAI + DeepSeek) via python SDK
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            max_tokens=30,
            timeout=timeout,
        )
        content = (resp.choices[0].message.content or "").strip()
        translated = _clean_translation_output(content)
        if not translated:
            return None
        # Filter obviously bad outputs
        if translated.lower() == word.lower():
            return None
        if len(translated) > 80:
            return None
        return translated
    except Exception:
        return None


def _translate_en_to_pt_mymemory(word: str, timeout: float = 10.0) -> Optional[str]:
    try:
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": word, "langpair": "en|pt-br"},
            timeout=timeout,
        )
        data = resp.json()
        if data.get("responseStatus") != 200:
            return None
        translated = (data.get("responseData", {}) or {}).get("translatedText")
        if not translated:
            return None
        translated = _clean_translation_output(str(translated))
        # MyMemory may return the same token.
        if translated.lower() == word.lower():
            return None
        # Filter long outputs (look like phrases).
        if len(translated) > 80:
            return None
        return translated
    except Exception:
        return None


def _choose_level_by_rank(rank: int, total: int) -> str:
    # Same heuristic used in ingest_course_material.
    if total <= 0:
        return "A1"
    ratio = rank / total
    if ratio < 0.2:
        return "A1"
    if ratio < 0.4:
        return "A2"
    if ratio < 0.6:
        return "B1"
    if ratio < 0.8:
        return "B2"
    if ratio < 0.95:
        return "C1"
    return "C2"


@dataclass
class Row:
    english: str
    ipa: str
    portuguese: str
    level: str
    tags: str


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Generate seed CSV from a wordlist (with EN->PT translation)")
    p.add_argument("--in", dest="in_path", required=True, help="Input wordlist txt (1 token per line)")
    p.add_argument("--out", dest="out_path", required=True, help="Output CSV path (semicolon-delimited)")
    p.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Extra tag to add (repeatable). Example: --tag pack:20k",
    )
    p.add_argument(
        "--translate",
        action="store_true",
        help="Translate portuguese via MyMemory (recommended; otherwise output will be empty and not importable)",
    )
    p.add_argument(
        "--provider",
        type=str,
        default="mymemory",
        choices=["mymemory", "openai", "deepseek", "auto"],
        help="Translation provider to use (default: mymemory). 'auto' prefers OpenAI, then DeepSeek, then MyMemory.",
    )
    p.add_argument(
        "--model",
        type=str,
        default="",
        help="Model override for LLM providers (default depends on provider)",
    )
    p.add_argument("--translate-delay", type=float, default=0.4, help="Delay between translations (seconds)")
    p.add_argument(
        "--cache",
        type=str,
        default="",
        help="JSON cache path (default depends on provider)",
    )
    p.add_argument(
        "--cache-save-every",
        type=int,
        default=200,
        help="Persist cache every N processed tokens",
    )
    p.add_argument(
        "--retry-cache-misses",
        action="store_true",
        help="If a token is cached as null/None, retry translating it (useful after transient API failures)",
    )
    p.add_argument(
        "--skip-untranslated",
        action="store_true",
        help="Skip words that fail translation (default behavior when --translate is set)",
    )
    p.add_argument(
        "--allow-non-headwords",
        action="store_true",
        help="Allow lines that aren't strict single-token headwords",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N accepted tokens (0 = all)",
    )
    p.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip first N accepted tokens before processing (0 = none)",
    )

    args = p.parse_args(list(argv) if argv is not None else None)

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    provider = (args.provider or "mymemory").lower().strip()

    if provider == "auto":
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("DEEPSEEK_API_KEY"):
            provider = "deepseek"
        else:
            provider = "mymemory"

    # Back-compat: --translate used to imply MyMemory.
    # Now, --translate enables translation using the chosen provider.
    translate_enabled = bool(args.translate)

    cache_default = f"backend/data/translation_cache_{provider}.json"
    cache_path = Path(args.cache or cache_default)

    llm_client = None
    llm_model = ""
    if translate_enabled and provider in {"openai", "deepseek"}:
        llm_client = _llm_client_for_provider(provider)
        if args.model and str(args.model).strip():
            llm_model = str(args.model).strip()
        else:
            llm_model = "gpt-4o-mini" if provider == "openai" else "deepseek-chat"

    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    # Default: when translating, keep output import-safe by skipping untranslated.
    skip_untranslated = bool(args.skip_untranslated) or bool(translate_enabled)

    raw_lines = list(_iter_wordlist_lines(in_path))

    # Normalize + validate + dedupe (case-insensitive)
    seen_lower: Set[str] = set()
    tokens: List[str] = []
    rejected = 0
    accepted_total = 0
    selected_total = 0
    for raw in raw_lines:
        tok = _normalize_token(raw)
        if not tok:
            continue
        if not args.allow_non_headwords and not _looks_like_headword(tok):
            rejected += 1
            continue
        key = tok.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        accepted_total += 1
        if args.offset and accepted_total <= int(args.offset):
            continue

        tokens.append(tok)
        selected_total += 1
        if args.limit and selected_total >= int(args.limit):
            break

    cache = _load_cache(cache_path) if translate_enabled else {}

    rows: List[Row] = []
    translated_ok = 0
    untranslated = 0

    total = len(tokens)
    for idx, token in enumerate(tokens, start=1):
        level = _choose_level_by_rank(idx - 1, total)
        tags = sorted({t.strip() for t in (args.tag or []) if t and t.strip()})
        tags_str = ",".join(tags) if tags else ""

        pt = ""
        if translate_enabled:
            cache_key = token.lower()
            if cache_key in cache:
                cached = cache.get(cache_key)
                if isinstance(cached, str) and cached.strip():
                    pt = cached.strip()
                elif cached is None and args.retry_cache_misses:
                    if provider == "mymemory":
                        pt_val = _translate_en_to_pt_mymemory(token)
                    else:
                        pt_val = _translate_en_to_pt_llm(llm_client, provider, token, model=llm_model)
                    cache[cache_key] = pt_val
                    if pt_val:
                        pt = pt_val
                    time.sleep(max(0.0, float(args.translate_delay)))
            else:
                if provider == "mymemory":
                    pt_val = _translate_en_to_pt_mymemory(token)
                else:
                    pt_val = _translate_en_to_pt_llm(llm_client, provider, token, model=llm_model)
                cache[cache_key] = pt_val
                if pt_val:
                    pt = pt_val
                time.sleep(max(0.0, float(args.translate_delay)))

            if not pt:
                untranslated += 1
                if skip_untranslated:
                    continue
            else:
                translated_ok += 1

            if args.cache_save_every and idx % int(args.cache_save_every) == 0:
                _save_cache(cache_path, cache)

        rows.append(Row(english=token, ipa="", portuguese=pt, level=level, tags=tags_str))

    if translate_enabled:
        _save_cache(cache_path, cache)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        # Semicolon delimiter to match existing seed tooling.
        f.write("english;ipa;portuguese;level;tags\n")
        for r in rows:
            # Minimal CSV escaping: fields may include ';' or '"'.
            def esc(v: str) -> str:
                v = v or ""
                if any(ch in v for ch in [';','\n','\r','"']):
                    v = '"' + v.replace('"', '""') + '"'
                return v

            f.write(";".join([esc(r.english), esc(r.ipa), esc(r.portuguese), esc(r.level), esc(r.tags)]) + "\n")

    print(f"📥 Input lines: {len(raw_lines)}")
    print(f"✅ Accepted tokens: {len(tokens)}")
    print(f"❌ Rejected lines: {rejected}")
    print(f"🧾 Output rows: {len(rows)}")
    if translate_enabled:
        print(f"🌐 Translated OK: {translated_ok}")
        print(f"⚠️  Untranslated: {untranslated} (skipped={skip_untranslated})")
        print(f"🤖 Provider: {provider}{' (' + llm_model + ')' if llm_model else ''}")
        print(f"🧠 Cache: {cache_path}")
    print(f"📄 CSV: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
