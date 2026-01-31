"""Verify whether tokens exist in Free Dictionary API (English).

Purpose
- When a list mixes English + Portuguese tokens, we can keep only words that
  actually exist as English headwords in Free Dictionary API.

Input
- One or more .txt files, one token per line.

Output (per input file)
- <file>.verified_en.txt          : tokens that exist in dictionary API
- <file>.not_in_dictionary.txt    : tokens that do not exist (or errored)
- <file>.verify_report.csv        : token-by-token result and HTTP status

Usage
  python backend/scripts/verify_word_list_with_dictionary_api.py not_found_words.txt.cleaned_en.txt
  python backend/scripts/verify_word_list_with_dictionary_api.py not_found_words.txt.cleaned_en.txt --workers 12

"""

from __future__ import annotations

import argparse
import csv
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import requests


FREE_DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"


@dataclass(frozen=True)
class CheckResult:
    token: str
    ok: bool
    status_code: Optional[int]
    error: str


def load_tokens(path: Path) -> List[str]:
    tokens: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        t = raw.strip()
        if not t or t.startswith("#"):
            continue
        tokens.append(t)
    # unique + stable
    seen = set()
    uniq: List[str] = []
    for t in tokens:
        tl = t.lower()
        if tl in seen:
            continue
        seen.add(tl)
        uniq.append(tl)
    return uniq


def _sleep_backoff(attempt: int, *, base_s: float, max_s: float, retry_after_s: Optional[float] = None) -> None:
    if retry_after_s is not None and retry_after_s > 0:
        time.sleep(min(retry_after_s, max_s))
        return
    exp = min(max_s, base_s * (2 ** max(0, attempt - 1)))
    jitter = random.uniform(0, min(0.25, exp))
    time.sleep(min(max_s, exp + jitter))


def check_token(
    session: requests.Session,
    token: str,
    *,
    timeout_s: float,
    max_retries: int,
    backoff_base_s: float,
    backoff_max_s: float,
    min_delay_s: float,
) -> CheckResult:
    last_error: str = ""
    status_code: Optional[int] = None

    for attempt in range(1, max_retries + 1):
        if min_delay_s > 0:
            time.sleep(min_delay_s)

        try:
            resp = session.get(f"{FREE_DICT_URL}{token}", timeout=timeout_s)
            status_code = resp.status_code

            if resp.status_code == 200:
                return CheckResult(token=token, ok=True, status_code=resp.status_code, error="")

            # Não encontrado: não adianta retry
            if resp.status_code == 404:
                return CheckResult(token=token, ok=False, status_code=resp.status_code, error="")

            # Rate limit / erros transitórios
            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after_hdr = resp.headers.get("Retry-After")
                retry_after_s: Optional[float] = None
                if retry_after_hdr:
                    try:
                        retry_after_s = float(retry_after_hdr)
                    except ValueError:
                        retry_after_s = None

                if attempt < max_retries:
                    _sleep_backoff(attempt, base_s=backoff_base_s, max_s=backoff_max_s, retry_after_s=retry_after_s)
                    continue
                return CheckResult(token=token, ok=False, status_code=resp.status_code, error="")

            # Outros 4xx
            return CheckResult(token=token, ok=False, status_code=resp.status_code, error="")

        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                _sleep_backoff(attempt, base_s=backoff_base_s, max_s=backoff_max_s)
                continue
            break

    return CheckResult(token=token, ok=False, status_code=status_code, error=last_error)


def verify_tokens(
    tokens: Sequence[str],
    *,
    workers: int,
    timeout_s: float,
    max_retries: int,
    backoff_base_s: float,
    backoff_max_s: float,
    min_delay_s: float,
) -> List[CheckResult]:
    # Session por thread via thread-local (evita criar Session por token)
    local = threading.local()

    def get_session() -> requests.Session:
        s = getattr(local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"Accept": "application/json", "User-Agent": "idiomasbr2026/verify-list"})
            local.session = s
        return s

    def worker(token: str) -> CheckResult:
        s = get_session()
        return check_token(
            s,
            token,
            timeout_s=timeout_s,
            max_retries=max_retries,
            backoff_base_s=backoff_base_s,
            backoff_max_s=backoff_max_s,
            min_delay_s=min_delay_s,
        )

    results: List[CheckResult] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker, t) for t in tokens]
        for f in as_completed(futures):
            results.append(f.result())

    # deterministic order
    results.sort(key=lambda r: r.token)
    return results


def write_outputs(input_path: Path, results: Sequence[CheckResult]) -> None:
    verified_path = input_path.with_suffix(input_path.suffix + ".verified_en.txt")
    not_found_path = input_path.with_suffix(input_path.suffix + ".not_in_dictionary.txt")
    report_path = input_path.with_suffix(input_path.suffix + ".verify_report.csv")

    verified = [r.token for r in results if r.ok]
    not_found = [r.token for r in results if not r.ok]

    verified_path.write_text("\n".join(verified) + ("\n" if verified else ""), encoding="utf-8")
    not_found_path.write_text("\n".join(not_found) + ("\n" if not_found else ""), encoding="utf-8")

    with report_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["token", "ok", "status_code", "error"])
        for r in results:
            w.writerow([r.token, "yes" if r.ok else "no", r.status_code if r.status_code is not None else "", r.error])

    print(f"✅ {input_path}: verified {len(verified)} / {len(results)}")
    print(f"   -> {verified_path.name}")
    print(f"   -> {not_found_path.name}")
    print(f"   -> {report_path.name}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Verify word list tokens in Free Dictionary API")
    p.add_argument("files", nargs="+", help="Input .txt files")
    p.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    p.add_argument("--timeout", type=float, default=6.0, help="HTTP timeout seconds (default: 6.0)")
    p.add_argument("--max-retries", type=int, default=4, help="Retries on 429/5xx/network (default: 4)")
    p.add_argument("--backoff-base", type=float, default=0.6, help="Backoff base seconds (default: 0.6)")
    p.add_argument("--backoff-max", type=float, default=8.0, help="Backoff max seconds (default: 8.0)")
    p.add_argument(
        "--min-delay",
        type=float,
        default=0.0,
        help="Optional minimum delay per request per worker (seconds). Use e.g. 0.05 to be gentler.",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    for fp in args.files:
        path = Path(fp)
        if not path.exists():
            print(f"❌ Not found: {path}")
            return 2

        tokens = load_tokens(path)
        if not tokens:
            print(f"⚠️  No tokens in {path}")
            continue

        results = verify_tokens(
            tokens,
            workers=max(1, args.workers),
            timeout_s=max(1.0, args.timeout),
            max_retries=max(1, args.max_retries),
            backoff_base_s=max(0.05, args.backoff_base),
            backoff_max_s=max(0.5, args.backoff_max),
            min_delay_s=max(0.0, args.min_delay),
        )
        write_outputs(path, results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
