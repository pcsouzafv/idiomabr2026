"""
Script para analisar a distribuição de palavras por nível no banco de dados.
"""
import sys
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.word import Word

def analyze_words_by_level():
    """Analisa e exibe a distribuição de palavras por nível."""

    # Conectar ao banco de dados
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Contar total de palavras
        total_words = db.query(func.count(Word.id)).scalar()
        print(f"\n{'='*60}")
        print(f"ANÁLISE DE PALAVRAS POR NÍVEL")
        print(f"{'='*60}")
        print(f"\nTotal de palavras no banco: {total_words}")

        # Contar palavras por nível
        level_counts = db.query(
            Word.level,
            func.count(Word.id).label('count')
        ).group_by(Word.level).order_by(Word.level).all()

        print(f"\n{'Nível':<10} {'Quantidade':<15} {'Porcentagem':<15} {'Barra'}")
        print(f"{'-'*60}")

        for level, count in level_counts:
            percentage = (count / total_words * 100) if total_words > 0 else 0
            bar = '█' * int(percentage / 2)  # Escala de 0-50 caracteres
            print(f"{level:<10} {count:<15} {percentage:>6.2f}%        {bar}")

        # Verificar se há palavras sem nível
        null_level_count = db.query(func.count(Word.id)).filter(
            Word.level == None  # type: ignore
        ).scalar()

        if null_level_count > 0:
            print(f"\n⚠️  Atenção: {null_level_count} palavras sem nível definido")

        # Estatísticas adicionais
        print(f"\n{'='*60}")
        print(f"ESTATÍSTICAS ADICIONAIS")
        print(f"{'='*60}")

        # Palavras com IPA
        words_with_ipa = db.query(func.count(Word.id)).filter(
            Word.ipa != None  # type: ignore
        ).scalar()
        ipa_percentage = (words_with_ipa / total_words * 100) if total_words > 0 else 0
        print(f"Palavras com IPA: {words_with_ipa} ({ipa_percentage:.1f}%)")

        # Palavras com exemplos
        words_with_examples = db.query(func.count(Word.id)).filter(
            Word.example_en != None  # type: ignore
        ).scalar()
        examples_percentage = (words_with_examples / total_words * 100) if total_words > 0 else 0
        print(f"Palavras com exemplos: {words_with_examples} ({examples_percentage:.1f}%)")

        # Palavras com tags
        words_with_tags = db.query(func.count(Word.id)).filter(
            Word.tags != None  # type: ignore
        ).scalar()
        tags_percentage = (words_with_tags / total_words * 100) if total_words > 0 else 0
        print(f"Palavras com tags: {words_with_tags} ({tags_percentage:.1f}%)")

        # Amostras por nível
        print(f"\n{'='*60}")
        print(f"AMOSTRAS DE PALAVRAS POR NÍVEL (5 primeiras de cada)")
        print(f"{'='*60}")

        for level, _ in level_counts:
            print(f"\n📚 Nível {level}:")
            sample_words = db.query(Word).filter(
                Word.level == level
            ).limit(5).all()

            for word in sample_words:
                ipa_str = f"/{word.ipa}/" if word.ipa else ""
                print(f"  • {word.english:<20} {ipa_str:<15} → {word.portuguese}")

        print(f"\n{'='*60}\n")

    except Exception as e:
        print(f"❌ Erro ao analisar banco de dados: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    analyze_words_by_level()
