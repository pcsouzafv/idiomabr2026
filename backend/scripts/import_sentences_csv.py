"""
Importa sentenças em massa a partir de CSV.
Formato: english,portuguese,level,category,grammar_points
"""
import argparse
import csv
import sys
from typing import Dict, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, '.')

from app.core.config import get_settings
from app.models.sentence import Sentence

LEVEL_DIFFICULTY = {
    "A1": 1.5,
    "A2": 3.0,
    "B1": 5.0,
    "B2": 7.0,
    "C1": 8.5,
    "C2": 9.5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importar sentenças via CSV")
    parser.add_argument("--csv", dest="csv_path", default="sentences_enrichment_us_daily_2000.csv")
    parser.add_argument("--skip-existing", action="store_true", help="Ignora sentenças já existentes")
    return parser.parse_args()


def load_existing_pairs(db) -> set[Tuple[str, str]]:
    pairs = set()
    for english, portuguese in db.query(Sentence.english, Sentence.portuguese).all():
        pairs.add((english, portuguese))
    return pairs


def main() -> None:
    args = parse_args()
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    created = 0
    skipped = 0
    errors = 0

    try:
        existing_pairs = load_existing_pairs(db) if args.skip_existing else set()

        with open(args.csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                english = (row.get("english") or "").strip()
                portuguese = (row.get("portuguese") or "").strip()
                level = (row.get("level") or "A1").strip() or "A1"
                category = (row.get("category") or "").strip() or None
                grammar_points = (row.get("grammar_points") or "").strip() or None

                if not english or not portuguese:
                    errors += 1
                    continue

                key = (english, portuguese)
                if key in existing_pairs:
                    skipped += 1
                    continue

                sentence = Sentence(
                    english=english,
                    portuguese=portuguese,
                    level=level,
                    category=category,
                    grammar_points=grammar_points,
                    difficulty_score=LEVEL_DIFFICULTY.get(level, 0.0),
                )
                db.add(sentence)
                created += 1

        db.commit()
        print(f"✅ Importadas: {created}")
        if args.skip_existing:
            print(f"⏭️  Ignoradas (já existentes): {skipped}")
        if errors:
            print(f"⚠️  Linhas inválidas ignoradas: {errors}")

    except Exception as exc:
        db.rollback()
        print(f"❌ Erro ao importar: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
