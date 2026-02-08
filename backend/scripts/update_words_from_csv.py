"""
Script para atualizar palavras do banco de dados a partir do CSV words_export.csv

ANÁLISE DO PROBLEMA:
====================
O arquivo words_export.csv contém 10.067 palavras, mas muitas estão com campos vazios:
- definition_en: 2.971 vazias (29.5%)
- definition_pt: 4.612 vazias (45.8%)
- example_en: 6.757 vazias (67.1%)
- example_pt: 7.677 vazias (76.3%)

Esses campos são essenciais para o sistema funcionar corretamente:
1. definition_en/pt: Necessários para explicar o significado das palavras
2. example_en/pt: Necessários para exemplos práticos e contexto de uso
3. Sem essas informações, os jogos de aprendizado ficam limitados

ESTRUTURA DO CSV:
=================
Colunas: id,english,ipa,portuguese,level,word_type,definition_en,definition_pt,example_en,example_pt,tags

SOLUÇÕES PROPOSTAS:
==================
1. ATUALIZAÇÃO DIRETA: Importar os dados do CSV para o banco (o que já existe)
2. ENRIQUECIMENTO: Usar APIs para preencher campos vazios
3. ANÁLISE: Identificar palavras que precisam de atenção manual

USO:
====
# Análise completa (sem modificar banco)
python backend/scripts/update_words_from_csv.py --analyze

# Importar dados do CSV
python backend/scripts/update_words_from_csv.py --import --csv-path words_export.csv

# Marcar palavras que precisam enriquecimento
python backend/scripts/update_words_from_csv.py --mark-for-enrichment

# Aplicar tudo
python backend/scripts/update_words_from_csv.py --import --mark-for-enrichment --apply

Docker:
# Análise
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze

# Importar e marcar (DRY-RUN)
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment

# Aplicar mudanças
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Adicionar backend ao path
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, or_

from app.core.database import SessionLocal
from app.models.word import Word


@dataclass
class WordData:
    """Dados de uma palavra do CSV"""
    id: int
    english: str
    ipa: Optional[str]
    portuguese: str
    level: str
    word_type: Optional[str]
    definition_en: Optional[str]
    definition_pt: Optional[str]
    example_en: Optional[str]
    example_pt: Optional[str]
    tags: Optional[str]


def read_csv_words(csv_path: Path) -> list[WordData]:
    """Lê palavras do CSV"""
    words = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                words.append(WordData(
                    id=int(row['id']) if row.get('id') else 0,
                    english=row['english'].strip(),
                    ipa=row['ipa'].strip() if row.get('ipa') else None,
                    portuguese=row['portuguese'].strip(),
                    level=row['level'].strip() if row.get('level') else 'A1',
                    word_type=row['word_type'].strip() if row.get('word_type') else None,
                    definition_en=row['definition_en'].strip() if row.get('definition_en') else None,
                    definition_pt=row['definition_pt'].strip() if row.get('definition_pt') else None,
                    example_en=row['example_en'].strip() if row.get('example_en') else None,
                    example_pt=row['example_pt'].strip() if row.get('example_pt') else None,
                    tags=row['tags'].strip() if row.get('tags') else None,
                ))
            except Exception as e:
                print(f"⚠️  Erro ao processar linha: {e}")
                continue
    
    return words


def analyze_csv(csv_path: Path) -> dict:
    """Analisa o CSV e retorna estatísticas"""
    words = read_csv_words(csv_path)
    
    stats = {
        'total': len(words),
        'empty_ipa': 0,
        'empty_word_type': 0,
        'empty_definition_en': 0,
        'empty_definition_pt': 0,
        'empty_example_en': 0,
        'empty_example_pt': 0,
        'empty_tags': 0,
        'complete': 0,
        'needs_enrichment': 0,
    }
    
    for word in words:
        if not word.ipa:
            stats['empty_ipa'] += 1
        if not word.word_type:
            stats['empty_word_type'] += 1
        if not word.definition_en:
            stats['empty_definition_en'] += 1
        if not word.definition_pt:
            stats['empty_definition_pt'] += 1
        if not word.example_en:
            stats['empty_example_en'] += 1
        if not word.example_pt:
            stats['empty_example_pt'] += 1
        if not word.tags:
            stats['empty_tags'] += 1
        
        # Palavra completa = tem todos os campos essenciais
        if (word.ipa and word.word_type and word.definition_en and 
            word.definition_pt and word.example_en and word.example_pt):
            stats['complete'] += 1
        else:
            stats['needs_enrichment'] += 1
    
    return stats


def analyze_database() -> dict:
    """Analisa o estado atual do banco de dados"""
    db = SessionLocal()
    
    try:
        stats = {
            'total': db.query(func.count(Word.id)).scalar(),
            'empty_ipa': db.query(func.count(Word.id)).filter(
                or_(Word.ipa == None, Word.ipa == '')
            ).scalar(),
            'empty_word_type': db.query(func.count(Word.id)).filter(
                or_(Word.word_type == None, Word.word_type == '')
            ).scalar(),
            'empty_definition_en': db.query(func.count(Word.id)).filter(
                or_(Word.definition_en == None, Word.definition_en == '')
            ).scalar(),
            'empty_definition_pt': db.query(func.count(Word.id)).filter(
                or_(Word.definition_pt == None, Word.definition_pt == '')
            ).scalar(),
            'empty_example_en': db.query(func.count(Word.id)).filter(
                or_(Word.example_en == None, Word.example_en == '')
            ).scalar(),
            'empty_example_pt': db.query(func.count(Word.id)).filter(
                or_(Word.example_pt == None, Word.example_pt == '')
            ).scalar(),
            'empty_tags': db.query(func.count(Word.id)).filter(
                or_(Word.tags == None, Word.tags == '')
            ).scalar(),
        }
        
        # Calcular palavras completas
        complete = db.query(func.count(Word.id)).filter(
            Word.ipa != None,
            Word.ipa != '',
            Word.word_type != None,
            Word.word_type != '',
            Word.definition_en != None,
            Word.definition_en != '',
            Word.definition_pt != None,
            Word.definition_pt != '',
            Word.example_en != None,
            Word.example_en != '',
            Word.example_pt != None,
            Word.example_pt != ''
        ).scalar()
        
        stats['complete'] = complete
        stats['needs_enrichment'] = stats['total'] - complete
        
        return stats
        
    finally:
        db.close()


def print_stats(title: str, stats: dict):
    """Imprime estatísticas formatadas"""
    total = stats['total']
    
    print(f"\n{'='*70}")
    print(f"{title:^70}")
    print(f"{'='*70}")
    print(f"\n📊 ESTATÍSTICAS GERAIS:")
    print(f"   Total de palavras: {total:,}")
    print(f"   Palavras completas: {stats['complete']:,} ({stats['complete']/total*100:.1f}%)")
    print(f"   Precisam enriquecimento: {stats['needs_enrichment']:,} ({stats['needs_enrichment']/total*100:.1f}%)")
    
    print(f"\n📝 CAMPOS VAZIOS:")
    print(f"   IPA: {stats['empty_ipa']:,} ({stats['empty_ipa']/total*100:.1f}%)")
    print(f"   Tipo (word_type): {stats['empty_word_type']:,} ({stats['empty_word_type']/total*100:.1f}%)")
    print(f"   Definição EN: {stats['empty_definition_en']:,} ({stats['empty_definition_en']/total*100:.1f}%)")
    print(f"   Definição PT: {stats['empty_definition_pt']:,} ({stats['empty_definition_pt']/total*100:.1f}%)")
    print(f"   Exemplo EN: {stats['empty_example_en']:,} ({stats['empty_example_en']/total*100:.1f}%)")
    print(f"   Exemplo PT: {stats['empty_example_pt']:,} ({stats['empty_example_pt']/total*100:.1f}%)")
    print(f"   Tags: {stats['empty_tags']:,} ({stats['empty_tags']/total*100:.1f}%)")


def import_from_csv(csv_path: Path, apply: bool = False) -> tuple[int, int, int]:
    """
    Importa dados do CSV para o banco
    
    Returns:
        (created, updated, skipped)
    """
    db = SessionLocal()
    words_data = read_csv_words(csv_path)
    
    created = 0
    updated = 0
    skipped = 0
    
    try:
        for word_data in words_data:
            # Buscar palavra existente por english (case-insensitive)
            existing = db.query(Word).filter(
                func.lower(Word.english) == word_data.english.lower()
            ).first()
            
            if existing:
                # Atualizar apenas se tiver dados novos
                has_updates = False
                
                if word_data.ipa and not existing.ipa:
                    existing.ipa = word_data.ipa
                    has_updates = True
                
                if word_data.word_type and not existing.word_type:
                    existing.word_type = word_data.word_type
                    has_updates = True
                
                if word_data.definition_en and not existing.definition_en:
                    existing.definition_en = word_data.definition_en
                    has_updates = True
                
                if word_data.definition_pt and not existing.definition_pt:
                    existing.definition_pt = word_data.definition_pt
                    has_updates = True
                
                if word_data.example_en and not existing.example_en:
                    existing.example_en = word_data.example_en
                    has_updates = True
                
                if word_data.example_pt and not existing.example_pt:
                    existing.example_pt = word_data.example_pt
                    has_updates = True
                
                if word_data.tags and not existing.tags:
                    existing.tags = word_data.tags
                    has_updates = True
                
                if has_updates:
                    updated += 1
                    if not apply:
                        print(f"  📝 [DRY-RUN] Atualizaria: {existing.english}")
                else:
                    skipped += 1
            else:
                # Criar nova palavra
                new_word = Word(
                    english=word_data.english,
                    ipa=word_data.ipa,
                    portuguese=word_data.portuguese,
                    level=word_data.level,
                    word_type=word_data.word_type,
                    definition_en=word_data.definition_en,
                    definition_pt=word_data.definition_pt,
                    example_en=word_data.example_en,
                    example_pt=word_data.example_pt,
                    tags=word_data.tags
                )
                db.add(new_word)
                created += 1
                if not apply:
                    print(f"  ✨ [DRY-RUN] Criaria: {new_word.english}")
        
        if apply:
            db.commit()
            print(f"\n✅ Mudanças aplicadas ao banco de dados!")
        else:
            print(f"\n💡 Este foi um DRY-RUN. Use --apply para aplicar mudanças.")
        
        return created, updated, skipped
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro durante importação: {e}")
        raise
    finally:
        db.close()


def mark_for_enrichment(apply: bool = False) -> int:
    """
    Marca palavras que precisam de enriquecimento adicionando tag especial
    
    Returns:
        Número de palavras marcadas
    """
    db = SessionLocal()
    
    try:
        # Buscar palavras incompletas
        words = db.query(Word).filter(
            or_(
                Word.ipa == None,
                Word.ipa == '',
                Word.word_type == None,
                Word.word_type == '',
                Word.definition_en == None,
                Word.definition_en == '',
                Word.definition_pt == None,
                Word.definition_pt == '',
                Word.example_en == None,
                Word.example_en == '',
                Word.example_pt == None,
                Word.example_pt == ''
            )
        ).all()
        
        marked = 0
        for word in words:
            # Adicionar tag de enriquecimento se não existir
            current_tags = word.tags or ''
            if 'needs_enrichment' not in current_tags:
                if current_tags:
                    word.tags = f"{current_tags},needs_enrichment"
                else:
                    word.tags = "needs_enrichment"
                marked += 1
                
                if not apply:
                    print(f"  🏷️  [DRY-RUN] Marcaria: {word.english}")
        
        if apply:
            db.commit()
            print(f"\n✅ {marked} palavras marcadas para enriquecimento!")
        else:
            print(f"\n💡 [DRY-RUN] {marked} palavras seriam marcadas. Use --apply para aplicar.")
        
        return marked
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro ao marcar palavras: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Atualiza palavras do banco a partir do CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Analisar CSV e banco de dados'
    )
    
    parser.add_argument(
        '--import',
        dest='import_csv',
        action='store_true',
        help='Importar dados do CSV'
    )
    
    parser.add_argument(
        '--mark-for-enrichment',
        action='store_true',
        help='Marcar palavras incompletas para enriquecimento'
    )
    
    parser.add_argument(
        '--csv-path',
        type=Path,
        default=PROJECT_ROOT / 'words_export.csv',
        help='Caminho do arquivo CSV (padrão: words_export.csv)'
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Aplicar mudanças (sem isso, apenas DRY-RUN)'
    )
    
    args = parser.parse_args()
    
    # Verificar se CSV existe
    if not args.csv_path.exists():
        print(f"❌ Arquivo CSV não encontrado: {args.csv_path}")
        return 1
    
    # Se nenhuma ação especificada, fazer análise
    if not (args.analyze or args.import_csv or args.mark_for_enrichment):
        args.analyze = True
    
    # ANÁLISE
    if args.analyze:
        print("\n🔍 ANALISANDO DADOS...\n")
        
        # Análise do CSV
        csv_stats = analyze_csv(args.csv_path)
        print_stats("ANÁLISE DO CSV", csv_stats)
        
        # Análise do banco
        print("\n")
        db_stats = analyze_database()
        print_stats("ANÁLISE DO BANCO DE DADOS", db_stats)
        
        # Recomendações
        print(f"\n{'='*70}")
        print("💡 RECOMENDAÇÕES")
        print(f"{'='*70}")
        
        if csv_stats['needs_enrichment'] > 0:
            print(f"\n1. 📥 IMPORTAR dados do CSV:")
            print(f"   python backend/scripts/update_words_from_csv.py --import --apply")
            print(f"   Isso atualizará campos vazios no banco com dados do CSV.")
        
        if db_stats['needs_enrichment'] > 0:
            print(f"\n2. 🏷️  MARCAR palavras incompletas:")
            print(f"   python backend/scripts/update_words_from_csv.py --mark-for-enrichment --apply")
            print(f"   Isso adiciona a tag 'needs_enrichment' para processamento posterior.")
        
        print(f"\n3. 🔧 ENRIQUECER palavras marcadas:")
        print(f"   docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment")
        print(f"   Usa APIs (Free Dictionary, Datamuse) para preencher campos vazios.")
        
        print(f"\n4. 📊 VERIFICAR progresso:")
        print(f"   python backend/scripts/update_words_from_csv.py --analyze")
        print(f"\n")
    
    # IMPORTAÇÃO
    if args.import_csv:
        print(f"\n{'='*70}")
        print("📥 IMPORTANDO DADOS DO CSV")
        print(f"{'='*70}\n")
        
        created, updated, skipped = import_from_csv(args.csv_path, args.apply)
        
        print(f"\n📊 RESUMO DA IMPORTAÇÃO:")
        print(f"   Criadas: {created}")
        print(f"   Atualizadas: {updated}")
        print(f"   Ignoradas: {skipped}")
    
    # MARCAÇÃO
    if args.mark_for_enrichment:
        print(f"\n{'='*70}")
        print("🏷️  MARCANDO PALAVRAS PARA ENRIQUECIMENTO")
        print(f"{'='*70}\n")
        
        marked = mark_for_enrichment(args.apply)
        
        print(f"\n📊 RESUMO:")
        print(f"   Palavras marcadas: {marked}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
