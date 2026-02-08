"""
Script para extrair palavras do PDF e importar no banco de dados.
PDF: "Mais de 5 mil palavras em inglês traduzidas para português.pdf"

O PDF tem formato de tabela:
Palavra em Inglês | Transcrição IPA | Tradução em Português
"""

import re
import sys
import fitz  # PyMuPDF
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.word import Word
from app.core.database import Base

# Conexão com banco
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classificação de nível baseada na frequência/posição
def get_level(index: int, total: int) -> str:
    """Determina o nível CEFR baseado na posição da palavra."""
    ratio = index / total
    if ratio < 0.2:
        return "A1"  # Primeiras 20% - mais comuns
    elif ratio < 0.4:
        return "A2"
    elif ratio < 0.6:
        return "B1"
    elif ratio < 0.8:
        return "B2"
    elif ratio < 0.95:
        return "C1"
    else:
        return "C2"


def is_header_line(line: str) -> bool:
    """Verifica se a linha é um cabeçalho da tabela."""
    headers = ['Palavra em Inglês', 'Transcrição IPA', 'Tradução em Português', 
               'Som Explicado', 'Exemplo de', 'Pronúncia no', 'Símbolo']
    return any(h.lower() in line.lower() for h in headers)


def is_valid_english_word(word: str) -> bool:
    """Verifica se é uma palavra inglesa válida."""
    if len(word) < 1 or len(word) > 50:
        return False
    # Deve começar com letra
    if not word[0].isalpha():
        return False
    # Não deve ser apenas números
    if word.isdigit():
        return False
    # Caracteres permitidos: letras, hífen, apóstrofo, espaço (para phrasal verbs)
    if not re.match(r'^[a-zA-Z][a-zA-Z\s\-\'\.\/\(\)]*$', word):
        return False
    return True


def is_ipa_transcription(text: str) -> bool:
    """Verifica se o texto parece uma transcrição IPA."""
    # IPA contém caracteres especiais como ə, ɪ, ʃ, ː, etc.
    ipa_chars = 'əɪʃːɛæʊɑɔʌŋðθʒɝɚaɑeioubdfghjklmnprstvwz'
    text_lower = text.lower()
    # Deve ter pelo menos 50% de caracteres que parecem IPA
    ipa_count = sum(1 for c in text_lower if c in ipa_chars)
    return len(text) > 0 and ipa_count / len(text) > 0.3


def extract_words_from_pdf_v2(pdf_path: str) -> list[dict]:
    """
    Extrai palavras do PDF com formato de tabela:
    Palavra em Inglês | Transcrição IPA | Tradução em Português
    """
    print(f"Abrindo PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    words = []
    seen = set()
    
    print(f"Total de páginas: {len(doc)}")
    
    # Começar da página 6 (índice 5), onde começam as palavras
    start_page = 5
    
    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Pular linhas vazias ou muito curtas
            if len(line) < 2:
                i += 1
                continue
            
            # Pular cabeçalhos
            if is_header_line(line):
                i += 1
                continue
            
            # Verificar se a linha pode ser uma palavra em inglês
            # Formato: palavra, depois IPA na mesma linha ou próxima, depois tradução
            
            # Tentar extrair da linha atual
            parts = re.split(r'\s{2,}|\t', line)
            
            if len(parts) >= 3:
                # Formato ideal: 3 partes na mesma linha
                english = parts[0].strip()
                ipa = parts[1].strip()
                portuguese = ' '.join(parts[2:]).strip()
                
                if is_valid_english_word(english) and len(portuguese) >= 2:
                    key = english.lower()
                    if key not in seen:
                        seen.add(key)
                        words.append({
                            'english': english.lower(),
                            'ipa': ipa,
                            'portuguese': portuguese
                        })
            
            elif len(parts) == 2:
                # Pode ser palavra + IPA, com tradução na próxima linha
                english = parts[0].strip()
                ipa = parts[1].strip()
                
                if is_valid_english_word(english) and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if len(next_line) >= 2 and not is_valid_english_word(next_line.split()[0] if next_line.split() else ''):
                        portuguese = next_line
                        key = english.lower()
                        if key not in seen:
                            seen.add(key)
                            words.append({
                                'english': english.lower(),
                                'ipa': ipa,
                                'portuguese': portuguese
                            })
                        i += 1  # Pular próxima linha já processada
            
            elif len(parts) == 1 and is_valid_english_word(line):
                # Palavra sozinha, IPA e tradução nas próximas linhas
                english = line
                if i + 2 < len(lines):
                    ipa = lines[i + 1].strip()
                    portuguese = lines[i + 2].strip()
                    
                    if len(portuguese) >= 2:
                        key = english.lower()
                        if key not in seen:
                            seen.add(key)
                            words.append({
                                'english': english.lower(),
                                'ipa': ipa,
                                'portuguese': portuguese
                            })
                        i += 2  # Pular próximas linhas
            
            i += 1
        
        if (page_num - start_page + 1) % 20 == 0:
            print(f"  Processando página {page_num + 1}/{len(doc)} - {len(words)} palavras encontradas...")
    
    doc.close()
    print(f"\nTotal de palavras extraídas: {len(words)}")
    return words


def extract_table_format(pdf_path: str) -> list[dict]:
    """
    Parser específico para tabela do PDF.
    Analisa a estrutura visual da tabela usando blocos de texto.
    """
    print(f"Usando parser de tabela...")
    
    doc = fitz.open(pdf_path)
    words = []
    seen = set()
    
    # Começar da página 6 (índice 5)
    start_page = 5
    
    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        
        # Extrair blocos de texto com posição
        blocks = page.get_text("dict")["blocks"]
        
        # Coletar linhas de texto
        lines_data = []
        
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    text = ""
                    for span in line["spans"]:
                        text += span["text"]
                    
                    y_pos = line["bbox"][1]  # Posição Y
                    lines_data.append({
                        'text': text.strip(),
                        'y': y_pos
                    })
        
        # Agrupar por posição Y (mesma linha)
        lines_data.sort(key=lambda x: x['y'])
        
        current_y = -100
        current_texts = []
        grouped_lines = []
        
        for ld in lines_data:
            if abs(ld['y'] - current_y) < 10:  # Mesma linha (tolerância de 10px)
                current_texts.append(ld['text'])
            else:
                if current_texts:
                    grouped_lines.append(' '.join(current_texts))
                current_texts = [ld['text']]
                current_y = ld['y']
        
        if current_texts:
            grouped_lines.append(' '.join(current_texts))
        
        # Processar linhas agrupadas
        for line in grouped_lines:
            line = line.strip()
            if len(line) < 2:
                continue
            
            if is_header_line(line):
                continue
            
            # Tentar dividir por múltiplos espaços ou tabs
            parts = re.split(r'\s{2,}|\t', line)
            
            if len(parts) >= 3:
                english = parts[0].strip()
                ipa = parts[1].strip()
                portuguese = ' '.join(parts[2:]).strip()
                
                if is_valid_english_word(english) and len(portuguese) >= 2:
                    key = english.lower()
                    if key not in seen:
                        seen.add(key)
                        words.append({
                            'english': english.lower(),
                            'ipa': ipa,
                            'portuguese': portuguese
                        })
        
        if (page_num - start_page + 1) % 20 == 0:
            print(f"  Página {page_num + 1}/{len(doc)} - {len(words)} palavras...")
    
    doc.close()
    print(f"Total extraído: {len(words)} palavras")
    return words


def import_to_database(words: list[dict]):
    """Importa palavras no banco de dados."""
    db = SessionLocal()
    
    try:
        # Primeiro, limpar tabelas relacionadas (para evitar foreign key violation)
        existing = db.query(Word).count()
        if existing > 0:
            print(f"Limpando dados existentes...")
            # Deletar em ordem para respeitar foreign keys
            db.execute(text("DELETE FROM user_progress"))
            db.execute(text("DELETE FROM reviews"))
            db.execute(text("DELETE FROM words"))
            db.commit()
            print(f"  Removidos {existing} palavras e dados relacionados.")
        
        total = len(words)
        imported = 0
        
        for i, word_data in enumerate(words):
            level = get_level(i, total)
            
            word = Word(
                english=word_data['english'],
                ipa=word_data['ipa'] if word_data['ipa'] else f"/{word_data['english']}/",
                portuguese=word_data['portuguese'],
                level=level,
                tags=None,
                example_en=None,
                example_pt=None
            )
            
            db.add(word)
            imported += 1
            
            # Commit em lotes
            if imported % 500 == 0:
                db.commit()
                print(f"  Importadas {imported}/{total} palavras...")
        
        db.commit()
        print(f"\n✅ Importação concluída: {imported} palavras")
        
        # Resumo por nível
        print("\nResumo por nível:")
        for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            count = db.query(Word).filter(Word.level == level).count()
            print(f"  {level}: {count} palavras")
            
    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        db.close()


def main():
    pdf_path = "/app/Mais de 5 mil palavras em inglês traduzidas para português.pdf"
    
    # Verificar se foi passado caminho alternativo
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    print("=" * 60)
    print("  IMPORTAÇÃO DE PALAVRAS DO PDF")
    print("=" * 60)
    
    # Tentar extração com parser de tabela primeiro
    words = extract_table_format(pdf_path)
    
    if len(words) < 500:
        print(f"\nParser de tabela extraiu {len(words)} palavras.")
        print("Tentando parser alternativo...")
        words2 = extract_words_from_pdf_v2(pdf_path)
        if len(words2) > len(words):
            words = words2
    
    if len(words) == 0:
        print("❌ Nenhuma palavra encontrada no PDF!")
        print("Verifique o formato do arquivo.")
        return
    
    # Importar
    print(f"\nImportando {len(words)} palavras no banco de dados...")
    import_to_database(words)
    
    print("\n" + "=" * 60)
    print("  IMPORTAÇÃO FINALIZADA!")
    print("=" * 60)


if __name__ == "__main__":
    main()
