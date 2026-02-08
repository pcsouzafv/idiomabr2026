"""
Script para importar palavras do CSV para o banco de dados.
Uso: python import_words.py caminho/para/palavras.csv
"""

import csv
import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.word import Word
from app.utils.text_sanitize import sanitize_unmatched_brackets

# Criar tabelas se não existirem
Base.metadata.create_all(bind=engine)


def import_words_from_csv(csv_path: str):
    """
    Importa palavras de um arquivo CSV.
    O CSV deve ter as colunas: english, ipa, portuguese
    Opcionalmente: level, example_en, example_pt, tags
    """
    db: Session = SessionLocal()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            # Detectar delimitador
            sample = file.read(1024)
            file.seek(0)
            
            if ';' in sample:
                delimiter = ';'
            elif '\t' in sample:
                delimiter = '\t'
            else:
                delimiter = ','
            
            reader = csv.DictReader(file, delimiter=delimiter)
            
            created = 0
            skipped = 0
            errors = 0
            
            for row in reader:
                try:
                    # Tentar diferentes nomes de colunas
                    english = row.get('english') or row.get('English') or row.get('ENGLISH') or row.get('word') or row.get('Word')
                    ipa = row.get('ipa') or row.get('IPA') or row.get('phonetic') or row.get('Phonetic')
                    portuguese = row.get('portuguese') or row.get('Portuguese') or row.get('PORTUGUESE') or row.get('translation') or row.get('Translation') or row.get('traducao')
                    
                    if not english or not portuguese:
                        print(f"Linha ignorada (campos obrigatórios vazios): {row}")
                        errors += 1
                        continue
                    
                    # Limpar strings
                    english = sanitize_unmatched_brackets(english)
                    portuguese = sanitize_unmatched_brackets(portuguese)
                    ipa = ipa.strip() if ipa else None
                    
                    # Verificar se já existe
                    existing = db.query(Word).filter(Word.english.ilike(english)).first()
                    if existing:
                        skipped += 1
                        continue
                    
                    # Criar palavra
                    word = Word(
                        english=english,
                        ipa=ipa,
                        portuguese=portuguese,
                        level=row.get('level', 'A1'),
                        example_en=row.get('example_en'),
                        example_pt=row.get('example_pt'),
                        tags=row.get('tags'),
                    )
                    db.add(word)
                    created += 1
                    
                    # Commit a cada 100 palavras
                    if created % 100 == 0:
                        db.commit()
                        print(f"Importadas {created} palavras...")
                
                except Exception as e:
                    print(f"Erro ao processar linha: {row}")
                    print(f"Erro: {e}")
                    errors += 1
            
            db.commit()
            
            print("\n" + "="*50)
            print("IMPORTAÇÃO CONCLUÍDA")
            print("="*50)
            print(f"Criadas: {created}")
            print(f"Ignoradas (já existentes): {skipped}")
            print(f"Erros: {errors}")
            print("="*50)
            
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Erro durante importação: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def create_sample_words():
    """
    Cria algumas palavras de exemplo para teste.
    """
    db: Session = SessionLocal()
    
    sample_words = [
        {"english": "hello", "ipa": "həˈloʊ", "portuguese": "olá", "level": "A1", "tags": "saudação"},
        {"english": "goodbye", "ipa": "ɡʊdˈbaɪ", "portuguese": "adeus", "level": "A1", "tags": "saudação"},
        {"english": "thank you", "ipa": "θæŋk juː", "portuguese": "obrigado", "level": "A1", "tags": "saudação"},
        {"english": "please", "ipa": "pliːz", "portuguese": "por favor", "level": "A1", "tags": "saudação"},
        {"english": "yes", "ipa": "jɛs", "portuguese": "sim", "level": "A1", "tags": "básico"},
        {"english": "no", "ipa": "noʊ", "portuguese": "não", "level": "A1", "tags": "básico"},
        {"english": "water", "ipa": "ˈwɔːtər", "portuguese": "água", "level": "A1", "tags": "comida,bebida"},
        {"english": "food", "ipa": "fuːd", "portuguese": "comida", "level": "A1", "tags": "comida"},
        {"english": "house", "ipa": "haʊs", "portuguese": "casa", "level": "A1", "tags": "moradia"},
        {"english": "car", "ipa": "kɑːr", "portuguese": "carro", "level": "A1", "tags": "transporte"},
        {"english": "work", "ipa": "wɜːrk", "portuguese": "trabalho", "level": "A1", "tags": "trabalho"},
        {"english": "money", "ipa": "ˈmʌni", "portuguese": "dinheiro", "level": "A1", "tags": "finanças"},
        {"english": "time", "ipa": "taɪm", "portuguese": "tempo", "level": "A1", "tags": "tempo"},
        {"english": "day", "ipa": "deɪ", "portuguese": "dia", "level": "A1", "tags": "tempo"},
        {"english": "night", "ipa": "naɪt", "portuguese": "noite", "level": "A1", "tags": "tempo"},
        {"english": "today", "ipa": "təˈdeɪ", "portuguese": "hoje", "level": "A1", "tags": "tempo"},
        {"english": "tomorrow", "ipa": "təˈmɑːroʊ", "portuguese": "amanhã", "level": "A1", "tags": "tempo"},
        {"english": "yesterday", "ipa": "ˈjestərdeɪ", "portuguese": "ontem", "level": "A1", "tags": "tempo"},
        {"english": "love", "ipa": "lʌv", "portuguese": "amor", "level": "A1", "tags": "sentimento"},
        {"english": "friend", "ipa": "frend", "portuguese": "amigo", "level": "A1", "tags": "pessoas"},
        {"english": "family", "ipa": "ˈfæməli", "portuguese": "família", "level": "A1", "tags": "pessoas"},
        {"english": "mother", "ipa": "ˈmʌðər", "portuguese": "mãe", "level": "A1", "tags": "pessoas,família"},
        {"english": "father", "ipa": "ˈfɑːðər", "portuguese": "pai", "level": "A1", "tags": "pessoas,família"},
        {"english": "child", "ipa": "tʃaɪld", "portuguese": "criança", "level": "A1", "tags": "pessoas"},
        {"english": "book", "ipa": "bʊk", "portuguese": "livro", "level": "A1", "tags": "educação"},
        {"english": "school", "ipa": "skuːl", "portuguese": "escola", "level": "A1", "tags": "educação"},
        {"english": "student", "ipa": "ˈstuːdnt", "portuguese": "estudante", "level": "A1", "tags": "educação,pessoas"},
        {"english": "teacher", "ipa": "ˈtiːtʃər", "portuguese": "professor", "level": "A1", "tags": "educação,pessoas"},
        {"english": "good", "ipa": "ɡʊd", "portuguese": "bom", "level": "A1", "tags": "adjetivo"},
        {"english": "bad", "ipa": "bæd", "portuguese": "mau", "level": "A1", "tags": "adjetivo"},
        {"english": "big", "ipa": "bɪɡ", "portuguese": "grande", "level": "A1", "tags": "adjetivo"},
        {"english": "small", "ipa": "smɔːl", "portuguese": "pequeno", "level": "A1", "tags": "adjetivo"},
        {"english": "new", "ipa": "nuː", "portuguese": "novo", "level": "A1", "tags": "adjetivo"},
        {"english": "old", "ipa": "oʊld", "portuguese": "velho", "level": "A1", "tags": "adjetivo"},
        {"english": "happy", "ipa": "ˈhæpi", "portuguese": "feliz", "level": "A1", "tags": "sentimento,adjetivo"},
        {"english": "sad", "ipa": "sæd", "portuguese": "triste", "level": "A1", "tags": "sentimento,adjetivo"},
        {"english": "beautiful", "ipa": "ˈbjuːtɪfl", "portuguese": "bonito", "level": "A2", "tags": "adjetivo"},
        {"english": "important", "ipa": "ɪmˈpɔːrtnt", "portuguese": "importante", "level": "A2", "tags": "adjetivo"},
        {"english": "different", "ipa": "ˈdɪfrənt", "portuguese": "diferente", "level": "A2", "tags": "adjetivo"},
        {"english": "same", "ipa": "seɪm", "portuguese": "mesmo", "level": "A2", "tags": "adjetivo"},
    ]
    
    try:
        created = 0
        for word_data in sample_words:
            existing = db.query(Word).filter(Word.english == word_data["english"]).first()
            if not existing:
                word = Word(**word_data)
                db.add(word)
                created += 1
        
        db.commit()
        print(f"Criadas {created} palavras de exemplo.")
        
    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        print(f"Importando palavras de: {csv_path}")
        import_words_from_csv(csv_path)
    else:
        print("Nenhum arquivo CSV fornecido. Criando palavras de exemplo...")
        create_sample_words()
        print("\nPara importar um CSV, use: python import_words.py caminho/para/arquivo.csv")
