"""Generate a new (inedita) English wordlist excluding existing DB words.

Goal
- Create a clean, single-token headword list suitable for the seed pipeline:
  wordlist -> scripts/wordlist_to_seed_csv.py -> scripts/import_seed_words_csv.py

Notes
- Excludes anything already present in a provided export CSV (case-insensitive).
- Produces single-token headwords only (letters + apostrophe/hyphen).
- Keeps output deterministic (no randomness) so batches can be repeated.

Usage (inside docker container):
    python scripts/generate_inedita_wordlist.py --out data/wordlist_inedita_20251231.txt --limit 3000

Then:
    python scripts/wordlist_to_seed_csv.py --in data/wordlist_inedita_20251231.txt --out data/seed_inedita_20251231_batch1.csv --translate --tag pack:inedita-20251231 --limit 500 --offset 0
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import requests

_HEADWORD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z'’\-]*$")


def _norm(s: str | None) -> str:
    return (s or "").strip()


def _looks_like_headword(token: str) -> bool:
    t = _norm(token)
    if not t or len(t) > 60:
        return False
    return bool(_HEADWORD_TOKEN_RE.match(t))


def _load_existing_from_db() -> set[str]:
    import sys

    BACKEND_DIR = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(BACKEND_DIR))

    from app.core.database import SessionLocal
    from app.models.word import Word

    db = SessionLocal()
    try:
        out: set[str] = set()
        for w in db.query(Word.english).all():
            e = _norm(getattr(w, "english", None)).lower()  # row may be tuple-like depending on dialect
            if not e and isinstance(w, tuple) and w:
                e = _norm(w[0]).lower()
            if e:
                out.add(e)
        return out
    finally:
        db.close()


def _parse_freq_from_tags(tags: object) -> float | None:
    if not isinstance(tags, list):
        return None
    for t in tags:
        if isinstance(t, str) and t.startswith("f:"):
            try:
                return float(t[2:])
            except Exception:
                return None
    return None


def _iter_datamuse_candidates(*, per_letter: int, delay: float, min_freq: float) -> Iterable[str]:
    letters = [chr(c) for c in range(ord("a"), ord("z") + 1)]
    for ch in letters:
        try:
            resp = requests.get(
                "https://api.datamuse.com/words",
                # md=f -> frequency tag; md=p -> parts of speech (helps debugging/filtering in future)
                params={"sp": f"{ch}*", "max": int(per_letter), "md": "fp"},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    w = item.get("word")
                    if not isinstance(w, str) or not w:
                        continue

                    # Prefer plain lowercase words; drop likely proper nouns.
                    if w != w.lower():
                        continue

                    freq = _parse_freq_from_tags(item.get("tags"))
                    if freq is None or freq < float(min_freq):
                        continue

                    yield w
        except Exception:
            # Best-effort; continue other letters.
            continue
        if delay:
            import time

            time.sleep(max(0.0, float(delay)))


def _iter_curated_candidates() -> Iterable[str]:
    # Curated, general-purpose tokens (single words only).
    # Intentionally avoids phrases ("credit card"), slashes ("airplane/plane"), etc.
    raw = """
    myself yourself himself herself itself ourselves yourselves themselves
    mine yours his hers ours theirs
    someone somebody anyone anybody everyone everybody noone nobody
    something anything everything nothing
    somewhere anywhere everywhere nowhere

    another other others else each every either neither both all any some none
    several various certain enough plenty little few many much more most less least
    own same different such

    maybe perhaps surely certainly probably possibly
    always never often sometimes rarely seldom
    already still yet soon later early
    again once twice
    almost nearly exactly

    although though however therefore moreover nevertheless otherwise meanwhile
    unless since while whereas

    can could may might must shall should would

    become begin believe belong bring build burn buy call carry catch change choose
    clean climb collect compare complain consider continue cook copy create decide
    deliver describe design destroy develop discover discuss divide draw drive drop
    earn encourage enjoy enter escape explain fail fall feed feel fight fill find
    finish fit fix fly follow forget forgive freeze get give go grow guess happen
    hate hear help hide hit hold hope hurry imagine improve include increase invite
    join jump keep kick kill kiss laugh learn leave lend let lie lift like listen
    live look lose love make manage marry mean meet mind miss move need notice
    offer open order pass pay pick plan play please prefer prepare press prevent
    promise protect prove pull push put raise reach read realize receive reduce
    refuse relax remember remove repair repeat replace reply report require rest
    return ride ring rise risk run save say search see select sell send serve set
    share shine shoot show shut sing sit sleep smell smile solve speak spend stand
    start stay steal stick stop study succeed suggest suppose swim take talk teach
    tell think throw touch travel try turn understand use visit wait wake walk want
    watch wear win work worry write

    angry afraid anxious ashamed bored brave calm careful clever curious eager
    easy empty fair famous fast final friendly funny general gentle glad grateful
    great guilty happy helpful honest hungry important impossible incredible
    interested jealous kind lazy lonely lucky nervous noisy normal obvious
    patient perfect pleasant polite powerful proud quiet ready real rich rude
    safe scared serious shy silent simple smart sorry special strong sure sweet
    tired true upset weak well

    quickly slowly quietly loudly carefully easily

    today tomorrow yesterday tonight
    morning afternoon evening midnight
    Monday Tuesday Wednesday Thursday Friday Saturday Sunday
    January February March April May June July August September October November December

    one two three four five six seven eight nine ten
    eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty
    thirty forty fifty sixty seventy eighty ninety hundred thousand

    zero

    color colour red blue green yellow orange purple pink brown black white gray grey

    family friend people person child children parent mother father sister brother
    husband wife partner

    head face eye eyes ear ears nose mouth lip tooth teeth tongue
    hair neck shoulder arm hand finger thumb nail chest back stomach belly
    leg knee foot feet toe

    home house room kitchen bathroom bedroom garden yard
    door window wall floor roof

    water coffee tea milk juice bread rice pasta meat fish chicken egg fruit
    apple banana orange grape lemon sugar salt pepper

    school class lesson teacher student book notebook pencil pen paper

    city town village street road avenue bridge
    airport station hotel restaurant cafe market store shop bank hospital

    car bus train plane boat ship bicycle motorcycle truck taxi

    dog cat bird horse cow pig sheep goat

    sun moon star sky cloud rain snow wind storm

    money price cost salary budget tax bill coin

    time hour minute second day week month year

    question answer idea problem solution reason result

    computer phone tablet screen keyboard mouse internet website email password

    music song movie game picture photo video

    """

    for tok in raw.split():
        t = tok.strip()
        if t:
            yield t


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate an inedita wordlist excluding existing DB words")
    ap.add_argument("--out", required=True, help="Output wordlist txt (one token per line)")
    ap.add_argument("--limit", type=int, default=3000, help="Max tokens to output")
    ap.add_argument(
        "--source",
        choices=["datamuse", "curated"],
        default="datamuse",
        help="Where to fetch candidate tokens from",
    )
    ap.add_argument("--per-letter", type=int, default=1000, help="Datamuse: max results per letter")
    ap.add_argument("--delay", type=float, default=0.2, help="Datamuse: delay between letter requests")
    ap.add_argument(
        "--min-freq",
        type=float,
        default=3.0,
        help="Datamuse: minimum frequency tag (f:...) to accept (higher = more common)",
    )
    args = ap.parse_args()

    out_path = Path(args.out)

    existing = _load_existing_from_db()

    out: list[str] = []
    seen: set[str] = set()
    rejected = 0
    skipped_existing = 0

    if args.source == "curated":
        candidate_iter: Iterable[str] = _iter_curated_candidates()
    else:
        candidate_iter = _iter_datamuse_candidates(
            per_letter=int(args.per_letter),
            delay=float(args.delay),
            min_freq=float(args.min_freq),
        )

    for c in candidate_iter:
        c_norm = _norm(c)
        c_key = c_norm.lower()
        if c_key in seen:
            continue
        seen.add(c_key)

        if not _looks_like_headword(c_norm):
            rejected += 1
            continue
        if c_key in existing:
            skipped_existing += 1
            continue

        out.append(c_norm)
        if args.limit and len(out) >= args.limit:
            break

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"existing english (unique): {len(existing)}")
    print(f"candidates seen: {len(seen)}")
    print(f"rejected (non-headword): {rejected}")
    print(f"skipped (already existing): {skipped_existing}")
    print(f"written: {len(out)}")
    print(f"out: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
