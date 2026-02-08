#!/usr/bin/env python3
"""Fill missing example_en/example_pt using AI and output a CSV safe to import.

This script is designed to work with the CSV extracts we generated from the XLSX
(`missing_examples__*.csv`). It produces a new CSV with the *full* column set
expected by `backend/scripts/update_words_from_csv.py`, so you can import updates
without overwriting existing non-empty DB fields.

Providers
- auto: prefer OpenAI, then DeepSeek, then Ollama
- openai/deepseek: uses OpenAI-compatible chat completions via python SDK
- ollama: uses local Ollama /api/generate

Typical usage (generate a small sample first):
  python backend/scripts/fill_missing_examples_ai.py \
    --in-csv "missing_examples__words_export (1).csv" \
    --out-csv "words_export_examples_filled.csv" \
    --provider auto --limit 20

Then import into DB (inside backend container):
  python scripts/update_words_from_csv.py --import --csv-path /app/words_export_examples_filled.csv --apply
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import requests


_EMPTY_MARKERS = {"", "nan", "none", "null"}


def _is_blank(value: Optional[str]) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    return s.lower() in _EMPTY_MARKERS


def _clean_one_line(text: str) -> str:
    out = (text or "").strip()
    if "\n" in out:
        out = out.split("\n", 1)[0].strip()
    # Remove surrounding quotes.
    if (out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'")):
        out = out[1:-1].strip()
    return out


def _word_in_sentence(word: str, sentence: str) -> bool:
    w = (word or "").strip()
    if not w:
        return False
    # Conservative boundary match for headwords; allow apostrophes/hyphens.
    pattern = re.compile(rf"(?i)(?<![A-Za-z'\-]){re.escape(w)}(?![A-Za-z'\-])")
    return bool(pattern.search(sentence or ""))


@dataclass
class Row:
    id: str
    english: str
    portuguese: str
    level: str
    word_type: str
    example_en: str
    example_pt: str


class LLM:
    def generate_example_en(self, *, english: str, portuguese: str, level: str, word_type: str) -> Optional[str]:
        raise NotImplementedError

    def translate_en_to_pt(self, *, english_sentence: str, level: str) -> Optional[str]:
        raise NotImplementedError


class OllamaLLM(LLM):
    def __init__(self, *, url: str, model: str, timeout: float = 60.0):
        self.url = (url or "").rstrip("/")
        self.model = model
        self.timeout = timeout

        # quick connectivity check
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=5)
            if r.status_code != 200:
                raise RuntimeError(f"Ollama status {r.status_code}")
        except Exception as e:
            raise RuntimeError(
                f"Não foi possível conectar ao Ollama em {self.url}. "
                "Verifique se o serviço está rodando e OLLAMA_URL está correto."
            ) from e

    def _call(self, prompt: str, *, temperature: float) -> Optional[str]:
        try:
            r = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt, "temperature": temperature, "stream": False},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                return None
            data = r.json() or {}
            return (data.get("response") or "").strip() or None
        except Exception:
            return None

    def generate_example_en(self, *, english: str, portuguese: str, level: str, word_type: str) -> Optional[str]:
        prompt = f"""Create ONE natural English example sentence that uses the EXACT word: {english}

Context:
- Learner level: {level}
- Portuguese meaning (pt-BR): {portuguese}
- Part of speech / word_type (if any): {word_type or 'unknown'}

Requirements:
- Use the EXACT token "{english}" in the sentence (do not replace with synonym).
- Keep vocabulary appropriate for {level} learners.
- Practical, everyday context.
- One sentence only.
- Return ONLY the sentence, no quotes, no extra text."""
        return self._call(prompt, temperature=0.6)

    def translate_en_to_pt(self, *, english_sentence: str, level: str) -> Optional[str]:
        prompt = f"""Traduza para português brasileiro (pt-BR) de forma natural:

{english_sentence}

Requisitos:
- Mantenha o significado.
- Uma frase só.
- Sem aspas, sem explicações.
- Linguagem adequada para nível {level}.

Retorne APENAS a tradução."""
        return self._call(prompt, temperature=0.2)


class OpenAICompatLLM(LLM):
    def __init__(self, *, provider: str, api_key: str, base_url: Optional[str], model: str, timeout: float = 60.0):
        self.provider = provider
        self.model = model
        self.timeout = timeout

        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Pacote 'openai' não está disponível. Instale com `pip install openai` ou use --provider ollama."
            ) from e

        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

    def _chat(self, *, system: str, user: str, temperature: float, max_tokens: int = 120) -> Optional[str]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            content = (resp.choices[0].message.content or "").strip()
            return content or None
        except Exception:
            return None

    def generate_example_en(self, *, english: str, portuguese: str, level: str, word_type: str) -> Optional[str]:
        system = "You generate language-learning example sentences. Return only the sentence."
        user = (
            "Create ONE natural English example sentence for language learners.\n"
            f"Word (must appear EXACTLY): {english}\n"
            f"Meaning (pt-BR): {portuguese}\n"
            f"Level: {level}\n"
            f"word_type: {word_type or 'unknown'}\n\n"
            "Constraints:\n"
            f"- The sentence MUST include the exact token '{english}' (no synonym).\n"
            f"- Vocabulary must fit {level} learners.\n"
            "- Practical everyday context.\n"
            "- One sentence only.\n"
            "Return ONLY the sentence."
        )
        return self._chat(system=system, user=user, temperature=0.6, max_tokens=80)

    def translate_en_to_pt(self, *, english_sentence: str, level: str) -> Optional[str]:
        system = "You translate English to Brazilian Portuguese (pt-BR). Return only the translation."
        user = (
            f"Translate to Brazilian Portuguese (pt-BR), natural and fluent.\n"
            f"Level: {level}\n\n"
            f"English: {english_sentence}\n\n"
            "Return ONLY the translation, one sentence."
        )
        return self._chat(system=system, user=user, temperature=0.2, max_tokens=120)


def _pick_llm(provider: str, *, model: Optional[str], ollama_model: str, ollama_url: str) -> LLM:
    p = (provider or "auto").strip().lower()

    def _try_ollama(url: str) -> Optional[LLM]:
        try:
            return OllamaLLM(url=url, model=ollama_model)
        except Exception:
            return None

    if p in {"openai", "auto"}:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return OpenAICompatLLM(provider="openai", api_key=api_key, base_url=None, model=model or "gpt-4o-mini")
        if p == "openai":
            raise RuntimeError("OPENAI_API_KEY não configurada")

    if p in {"deepseek", "auto"}:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            return OpenAICompatLLM(
                provider="deepseek",
                api_key=api_key,
                base_url="https://api.deepseek.com",
                model=model or "deepseek-chat",
            )
        if p == "deepseek":
            raise RuntimeError("DEEPSEEK_API_KEY não configurada")

    if p in {"ollama", "auto"}:
        url = os.getenv("OLLAMA_URL") or ollama_url
        llm = _try_ollama(url)
        if llm is not None:
            return llm
        if p == "ollama":
            raise RuntimeError(
                f"Não foi possível conectar ao Ollama em {url}. "
                "Dica: fora do Docker use --ollama-url http://localhost:11434; "
                "no Docker use OLLAMA_URL=http://ollama:11434."
            )

    raise RuntimeError(
        "Nenhum provider disponível. Configure OPENAI_API_KEY ou DEEPSEEK_API_KEY, "
        "ou rode Ollama e informe --ollama-url (ex.: http://localhost:11434)."
    )



def _read_rows(path: Path) -> List[Row]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Row] = []
        for raw in reader:
            rows.append(
                Row(
                    id=str(raw.get("id", "")).strip(),
                    english=str(raw.get("english", "")).strip(),
                    portuguese=str(raw.get("portuguese", "")).strip(),
                    level=str(raw.get("level", "A1")).strip() or "A1",
                    word_type=str(raw.get("word_type", "")).strip(),
                    example_en=str(raw.get("example_en", "")).strip(),
                    example_pt=str(raw.get("example_pt", "")).strip(),
                )
            )
        return rows


def _write_update_csv(path: Path, rows: Iterable[Dict[str, str]]) -> None:
    fieldnames = [
        "id",
        "english",
        "ipa",
        "portuguese",
        "level",
        "word_type",
        "definition_en",
        "definition_pt",
        "example_en",
        "example_pt",
        "tags",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _load_existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            out: set[str] = set()
            for row in reader:
                rid = str(row.get("id", "")).strip()
                if rid:
                    out.add(rid)
            return out
    except Exception:
        return set()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fill missing example_en/example_pt using AI")
    parser.add_argument("--in-csv", required=True, help="Input CSV (e.g. missing_examples__words_export (1).csv)")
    parser.add_argument("--out-csv", required=True, help="Output CSV compatible with update_words_from_csv.py")
    parser.add_argument("--provider", default="auto", choices=["auto", "openai", "deepseek", "ollama"])
    parser.add_argument("--model", default=None, help="LLM model for openai/deepseek (optional)")
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"))
    parser.add_argument("--limit", type=int, default=0, help="Process only N rows (0 = all)")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between calls")
    parser.add_argument("--resume", action="store_true", help="Resume if out-csv exists (skip already-written ids)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write output file")

    args = parser.parse_args(list(argv) if argv is not None else None)

    in_path = Path(args.in_csv)
    out_path = Path(args.out_csv)
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    llm = _pick_llm(args.provider, model=args.model, ollama_model=args.ollama_model, ollama_url=args.ollama_url)
    print(f"Provider OK: {llm.__class__.__name__}")

    rows = _read_rows(in_path)
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    existing_ids: set[str] = set()
    if args.resume and out_path.exists():
        existing_ids = _load_existing_ids(out_path)
        if existing_ids:
            print(f"Resume: found {len(existing_ids)} ids already written in {out_path}")

    fieldnames = [
        "id",
        "english",
        "ipa",
        "portuguese",
        "level",
        "word_type",
        "definition_en",
        "definition_pt",
        "example_en",
        "example_pt",
        "tags",
    ]

    out_file = None
    writer = None
    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if (args.resume and out_path.exists()) else "w"
        out_file = open(out_path, mode, encoding="utf-8-sig", newline="")
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
    filled_en = 0
    filled_pt = 0
    skipped = 0

    try:
        for idx, row in enumerate(rows, start=1):
            if row.id and row.id in existing_ids:
                skipped += 1
                continue

            need_en = _is_blank(row.example_en)
            need_pt = _is_blank(row.example_pt)
            if not need_en and not need_pt:
                skipped += 1
                continue

            english_example = row.example_en
            pt_example = row.example_pt

            # Generate missing EN
            if need_en:
                for _attempt in range(1, 4):
                    candidate = llm.generate_example_en(
                        english=row.english,
                        portuguese=row.portuguese,
                        level=row.level,
                        word_type=row.word_type,
                    )
                    candidate = _clean_one_line(candidate or "")
                    if candidate and _word_in_sentence(row.english, candidate):
                        english_example = candidate
                        filled_en += 1
                        break
                    time.sleep(max(args.delay, 0.2))

            # Generate missing PT (prefer translating the EN sentence)
            if need_pt and not _is_blank(english_example):
                for _ in range(1, 3):
                    candidate = llm.translate_en_to_pt(english_sentence=english_example, level=row.level)
                    candidate = _clean_one_line(candidate or "")
                    if candidate and candidate.lower() != (english_example or "").lower():
                        pt_example = candidate
                        filled_pt += 1
                        break
                    time.sleep(max(args.delay, 0.2))

            out_row = {
                "id": row.id,
                "english": row.english,
                "ipa": "",
                "portuguese": row.portuguese,
                "level": row.level,
                "word_type": row.word_type,
                "definition_en": "",
                "definition_pt": "",
                "example_en": _clean_one_line(english_example or ""),
                "example_pt": _clean_one_line(pt_example or ""),
                "tags": "",
            }

            if not args.dry_run and writer and out_file:
                writer.writerow(out_row)
                out_file.flush()

            if idx % 20 == 0:
                print(
                    f"[{idx}/{len(rows)}] filled_en={filled_en} filled_pt={filled_pt} skipped={skipped} last={row.english}"
                )

            time.sleep(max(args.delay, 0.0))
    except KeyboardInterrupt:
        print("\nInterrupted. Partial output preserved; re-run with --resume to continue.")

    updates_written = (filled_en + filled_pt)  # approximation; not exact rows
    print(f"Done. rows={len(rows)} filled_en={filled_en} filled_pt={filled_pt} skipped={skipped}")

    if out_file:
        out_file.close()

    if args.dry_run:
        print("DRY-RUN: output not written")
        return 0

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
