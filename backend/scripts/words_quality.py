import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text


def _get_db_url(db_url_arg: Optional[str]) -> str:
    db_url = db_url_arg or os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "DATABASE_URL não definido. Rode dentro do container do backend, "
            "ou passe --db-url postgresql://user:pass@host:port/db"
        )
    return db_url


def _run_report(engine) -> Dict[str, Any]:
    queries = {
        "total": "SELECT COUNT(*)::int AS n FROM words",
        "english_outer_ws": """
            SELECT COUNT(*)::int AS n
            FROM words
            WHERE english <> btrim(english)
        """,
        "portuguese_outer_ws": """
            SELECT COUNT(*)::int AS n
            FROM words
            WHERE portuguese <> btrim(portuguese)
        """,
        "english_has_space_any": """
            SELECT COUNT(*)::int AS n
            FROM words
            WHERE english ~ '\\s'
        """,
        "english_not_alpha_trimmed": """
            SELECT COUNT(*)::int AS n
            FROM words
            WHERE btrim(english) !~ '^[A-Za-z]+$'
        """,
        "pt_equals_en_trimmed_casefold": """
            SELECT COUNT(*)::int AS n
            FROM words
            WHERE lower(btrim(portuguese)) = lower(btrim(english))
        """,
        "has_nbsp": """
            SELECT COUNT(*)::int AS n
            FROM words
            WHERE position(chr(160) in english) > 0 OR position(chr(160) in portuguese) > 0
        """,
    }

    samples = {
        "english_outer_ws": """
            SELECT id, english, portuguese, level
            FROM words
            WHERE english <> btrim(english)
            ORDER BY id
            LIMIT 30
        """,
        "portuguese_outer_ws": """
            SELECT id, english, portuguese, level
            FROM words
            WHERE portuguese <> btrim(portuguese)
            ORDER BY id
            LIMIT 30
        """,
        "english_not_alpha_trimmed": """
            SELECT id, english, portuguese, level
            FROM words
            WHERE btrim(english) !~ '^[A-Za-z]+$'
            ORDER BY id
            LIMIT 30
        """,
        "english_has_space_any": """
            SELECT id, english, portuguese, level
            FROM words
            WHERE english ~ '\\s'
            ORDER BY id
            LIMIT 30
        """,
        "pt_equals_en_trimmed_casefold": """
            SELECT id, english, portuguese, level
            FROM words
            WHERE lower(btrim(portuguese)) = lower(btrim(english))
            ORDER BY id
            LIMIT 30
        """,
        "has_nbsp": """
            SELECT id, english, portuguese, level
            FROM words
            WHERE position(chr(160) in english) > 0 OR position(chr(160) in portuguese) > 0
            ORDER BY id
            LIMIT 30
        """,
    }

    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {},
        "samples": {},
    }

    with engine.connect() as conn:
        for key, sql in queries.items():
            report["counts"][key] = conn.execute(text(sql)).mappings().one()["n"]

        for key, sql in samples.items():
            rows = conn.execute(text(sql)).mappings().all()
            report["samples"][key] = [dict(r) for r in rows]

    return report


def _trim_whitespace(engine, apply: bool) -> Dict[str, Any]:
    # Limpeza segura: remove whitespace externo e troca NBSP por espaço normal.
    # Não tenta "corrigir" palavras com hífen/apóstrofo/frases.
    update_sql = """
        UPDATE words
        SET
            english = btrim(replace(english, chr(160), ' ')),
            portuguese = btrim(replace(portuguese, chr(160), ' '))
        WHERE
            english <> btrim(replace(english, chr(160), ' '))
            OR portuguese <> btrim(replace(portuguese, chr(160), ' '))
    """

    count_sql = """
        SELECT COUNT(*)::int AS n
        FROM words
        WHERE
            english <> btrim(replace(english, chr(160), ' '))
            OR portuguese <> btrim(replace(portuguese, chr(160), ' '))
    """

    sample_sql = """
        SELECT id, english, portuguese, level
        FROM words
        WHERE
            english <> btrim(replace(english, chr(160), ' '))
            OR portuguese <> btrim(replace(portuguese, chr(160), ' '))
        ORDER BY id
        LIMIT 30
    """

    result: Dict[str, Any] = {
        "apply": apply,
        "would_change": 0,
        "changed": 0,
        "sample": [],
    }

    with engine.begin() as conn:
        result["would_change"] = conn.execute(text(count_sql)).mappings().one()["n"]
        result["sample"] = [dict(r) for r in conn.execute(text(sample_sql)).mappings().all()]

        if apply and result["would_change"] > 0:
            res = conn.execute(text(update_sql))
            # rowcount pode ser -1 dependendo do driver, mas em geral vem ok.
            result["changed"] = int(res.rowcount) if res.rowcount is not None else 0

        if not apply:
            # engine.begin() vai commitar no final; para dry-run, força rollback.
            conn.rollback()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Relatório e limpeza segura de qualidade da tabela words"
    )
    parser.add_argument("--db-url", help="Sobrescreve DATABASE_URL")

    sub = parser.add_subparsers(dest="command", required=True)

    report_p = sub.add_parser("report", help="Gera relatório (contagens + amostras)")
    report_p.add_argument("--out", help="Salva JSON em um arquivo")

    trim_p = sub.add_parser(
        "trim", help="Remove whitespace externo e NBSP (modo seguro)"
    )
    trim_p.add_argument(
        "--apply",
        action="store_true",
        help="Aplica UPDATE no banco (sem isso, é dry-run e faz rollback)",
    )

    cleanup_p = sub.add_parser(
        "cleanup-headers",
        help="Remove registros que parecem cabeçalhos da importação (ex.: 'letra x', 'palavra em')",
    )
    cleanup_p.add_argument(
        "--apply",
        action="store_true",
        help="Aplica DELETE no banco (sem isso, é dry-run e faz rollback)",
    )

    args = parser.parse_args()

    engine = create_engine(_get_db_url(args.db_url), pool_pre_ping=True)

    if args.command == "report":
        report = _run_report(engine)
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(payload)
        else:
            print(payload)
        return

    if args.command == "trim":
        result = _trim_whitespace(engine, apply=bool(args.apply))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "cleanup-headers":
        where_clause = """
            (lower(btrim(english)) = 'palavra em' AND lower(btrim(portuguese)) LIKE '%transcrição ipa%')
            OR (lower(btrim(english)) LIKE 'letra %' AND lower(btrim(portuguese)) LIKE 'pronúncia%')
        """

        count_sql = f"SELECT COUNT(*)::int AS n FROM words WHERE {where_clause}"
        sample_sql = f"""
            SELECT id, english, portuguese, level
            FROM words
            WHERE {where_clause}
            ORDER BY id
            LIMIT 50
        """
        delete_sql = f"DELETE FROM words WHERE {where_clause}"

        result: Dict[str, Any] = {
            "apply": bool(args.apply),
            "would_delete": 0,
            "deleted": 0,
            "sample": [],
        }

        with engine.begin() as conn:
            result["would_delete"] = conn.execute(text(count_sql)).mappings().one()["n"]
            result["sample"] = [
                dict(r) for r in conn.execute(text(sample_sql)).mappings().all()
            ]

            if args.apply and result["would_delete"] > 0:
                res = conn.execute(text(delete_sql))
                result["deleted"] = int(res.rowcount) if res.rowcount is not None else 0

            if not args.apply:
                conn.rollback()

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
