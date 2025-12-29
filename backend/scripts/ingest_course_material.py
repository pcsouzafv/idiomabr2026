"""backend/scripts/ingest_course_material.py

Ingestão de material de curso (PDF + transcrições) para gerar VOCABULÁRIO.

Objetivo
- Extrair apenas uma lista de palavras (tokens) do material.
- Evitar armazenar trechos/frases do conteúdo original (copyright).
- Gerar um CSV compatível com `backend/import_words.py`.

Fontes suportadas
- PDF: tenta PyMuPDF (fitz). Se não disponível, tenta pypdf.
- Transcrições: .txt, .srt, .vtt (lendo arquivos de texto).

Tradução (opcional)
- Pode preencher `portuguese` via MyMemory (en|pt-br), para facilitar a importação.

Exemplos
- Gerar CSV de um PDF:
    python backend/scripts/ingest_course_material.py --pdf "C:/Users/.../curso.pdf" --out "backend/data/curso_vocab.csv" --translate

- Gerar CSV a partir de transcrições:
    python backend/scripts/ingest_course_material.py --transcripts-dir "C:/Users/.../transcricoes" --out "backend/data/curso_vocab.csv" --translate

- Importar no banco depois:
    python backend/import_words.py backend/data/curso_vocab.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

import requests


_WORD_RE = re.compile(r"\b[A-Za-z](?:[A-Za-z'\-]{0,48}[A-Za-z])?\b")


_STOPWORDS: Set[str] = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "to",
    "of",
    "in",
    "on",
    "at",
    "for",
    "from",
    "with",
    "without",
    "into",
    "over",
    "under",
    "about",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
}


def _normalize_text(text: str) -> str:
    # Normaliza apóstrofos “inteligentes” e hífens unicode.
    return (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("–", "-")
        .replace("—", "-")
    )


def _iter_pdf_text(pdf_path: Path, max_pages: Optional[int] = None) -> Iterator[str]:
    """Extrai texto de um PDF.

    Tenta, em ordem:
    - PyMuPDF (fitz)
    - pypdf

    Não falha silenciosamente: se nenhum backend estiver disponível, encerra com instrução.
    """

    try:
        import fitz  # type: ignore

        doc = fitz.open(str(pdf_path))  # type: ignore[no-any-return]
        total = len(doc)
        limit = total if max_pages is None else min(total, max_pages)
        for i in range(limit):
            yield doc[i].get_text("text")  # type: ignore[attr-defined]
        doc.close()
        return
    except ImportError:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        pages = reader.pages
        limit = len(pages) if max_pages is None else min(len(pages), max_pages)
        for i in range(limit):
            yield pages[i].extract_text() or ""
        return
    except ImportError:
        raise SystemExit(
            "Nenhuma lib de PDF encontrada. Instale uma destas no ambiente do backend:\n"
            "- PyMuPDF (fitz)  OR\n"
            "- pypdf\n"
            "Dica: se você roda via Docker, instale no container do backend."
        )


def _read_text_file(path: Path) -> str:
    # Tenta utf-8; se falhar, cai para latin-1.
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


def _iter_transcript_texts(transcripts_dir: Path) -> Iterator[Tuple[Path, str]]:
    exts = {".txt", ".srt", ".vtt"}
    for file_path in transcripts_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in exts:
            continue
        yield file_path, _read_text_file(file_path)


def _strip_srt_vtt_markers(text: str) -> str:
    # Remove timestamps e índices comuns de SRT/VTT.
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        lines.append(line)
    return " ".join(lines)


def _extract_words_from_text(
    text: str,
    *,
    min_len: int,
    exclude_stopwords: bool,
) -> List[str]:
    text = _normalize_text(text)
    words: List[str] = []
    for match in _WORD_RE.finditer(text):
        token = match.group(0).lower()
        if len(token) < min_len:
            continue
        if exclude_stopwords and token in _STOPWORDS:
            continue
        # evita tokens só com hífen/apóstrofo no meio
        token = token.strip("'-")
        if len(token) < min_len:
            continue
        words.append(token)
    return words


def _merge_sources(
    token_to_sources: Dict[str, Set[str]],
    token_counts: Counter,
    tokens: Iterable[str],
    source_tag: str,
) -> None:
    for t in tokens:
        token_counts[t] += 1
        token_to_sources.setdefault(t, set()).add(source_tag)


def _translate_en_to_pt_mymemory(word: str, timeout: float = 10.0) -> Optional[str]:
    """Traduz uma palavra (inglês -> pt-br) via MyMemory.

    Observação: é um serviço gratuito e pode variar. Essa função tenta ser conservadora
    e retorna None quando a resposta é suspeita.
    """

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
        translated = str(translated).strip()
        # MyMemory às vezes devolve o próprio termo.
        if translated.lower() == word.lower():
            return None
        # Filtra saídas muito longas (parecem frase).
        if len(translated) > 80:
            return None
        return translated
    except Exception:
        return None


def _choose_level_from_rank(rank: int, total: int) -> str:
    """Reaproveita uma heurística simples: palavras mais frequentes -> níveis mais baixos."""
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


def _write_csv(
    out_path: Path,
    rows: Sequence[Dict[str, str]],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["english", "portuguese", "level", "tags"],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai VOCABULÁRIO de PDF e/ou transcrições e gera CSV para importação. "
            "Não armazena trechos do material (somente tokens)."
        )
    )
    parser.add_argument("--pdf", help="Caminho do PDF (opcional)")
    parser.add_argument(
        "--transcripts-dir",
        help="Pasta com transcrições .txt/.srt/.vtt (opcional)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Arquivo CSV de saída (ex.: backend/data/curso_vocab.csv)",
    )
    parser.add_argument(
        "--course-tag",
        default="curso:importado",
        help="Tag base para identificar o curso (ex.: curso:ingles-rapido)",
    )
    parser.add_argument(
        "--min-len",
        type=int,
        default=2,
        help="Tamanho mínimo do token (default: 2)",
    )
    parser.add_argument(
        "--exclude-stopwords",
        action="store_true",
        help="Remove stopwords comuns (default: desativado)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Máximo de páginas do PDF para processar (debug)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Limita para as TOP N palavras por frequência (0 = todas)",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Preenche portuguese via MyMemory (recomendado para importar)",
    )
    parser.add_argument(
        "--translate-delay",
        type=float,
        default=0.4,
        help="Delay entre traduções (segundos)",
    )

    args = parser.parse_args(argv)

    if not args.pdf and not args.transcripts_dir:
        parser.error("Você precisa informar --pdf e/ou --transcripts-dir")

    out_path = Path(args.out)

    token_to_sources: Dict[str, Set[str]] = {}
    token_counts: Counter[str] = Counter()

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            raise SystemExit(f"PDF não encontrado: {pdf_path}")

        for page_text in _iter_pdf_text(pdf_path, max_pages=args.max_pages):
            tokens = _extract_words_from_text(
                page_text,
                min_len=int(args.min_len),
                exclude_stopwords=bool(args.exclude_stopwords),
            )
            _merge_sources(token_to_sources, token_counts, tokens, "origem:pdf")

    if args.transcripts_dir:
        transcripts_path = Path(args.transcripts_dir)
        if not transcripts_path.exists():
            raise SystemExit(f"Pasta de transcrições não encontrada: {transcripts_path}")

        for file_path, content in _iter_transcript_texts(transcripts_path):
            cleaned = _strip_srt_vtt_markers(content)
            tokens = _extract_words_from_text(
                cleaned,
                min_len=int(args.min_len),
                exclude_stopwords=bool(args.exclude_stopwords),
            )
            _merge_sources(
                token_to_sources, token_counts, tokens, "origem:transcricao"
            )

    # Ordena por frequência (desc) e, em empate, por ordem alfabética.
    tokens_sorted = sorted(
        token_to_sources.keys(),
        key=lambda w: (-int(token_counts.get(w, 0)), w),
    )

    if args.top and args.top > 0:
        tokens_sorted = tokens_sorted[: int(args.top)]

    rows: List[Dict[str, str]] = []
    translation_cache: Dict[str, Optional[str]] = {}

    total = len(tokens_sorted)
    for idx, token in enumerate(tokens_sorted, start=1):
        tags = {args.course_tag}
        tags.update(token_to_sources.get(token, set()))
        level = _choose_level_from_rank(idx - 1, total)

        pt = ""
        if args.translate:
            if token in translation_cache:
                pt_val = translation_cache[token]
            else:
                pt_val = _translate_en_to_pt_mymemory(token)
                translation_cache[token] = pt_val
                time.sleep(max(0.0, float(args.translate_delay)))

            if pt_val:
                pt = pt_val

        rows.append(
            {
                "english": token,
                "portuguese": pt,
                "level": level,
                "tags": ",".join(sorted(tags)),
            }
        )

    _write_csv(out_path, rows)

    missing_pt = sum(1 for r in rows if not r.get("portuguese"))
    print(f"OK: CSV gerado em {out_path}")
    print(f"Total de palavras: {len(rows)}")
    if args.translate:
        print(f"Sem tradução (portuguese vazio): {missing_pt}")
        if missing_pt:
            print(
                "Dica: você pode filtrar as linhas sem tradução antes de importar, "
                "ou rodar novamente aumentando delay / tentando outra fonte."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
