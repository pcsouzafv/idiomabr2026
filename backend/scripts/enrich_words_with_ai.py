#!/usr/bin/env python3
"""
Script para enriquecer palavras do banco de dados usando IA (OpenAI/DeepSeek).
Gera automaticamente definições e exemplos para campos vazios.

Uso:
    python enrich_words_with_ai.py --batch 50 --delay 1.0 --dry-run
    python enrich_words_with_ai.py --batch 100 --fields definition_en,example_en
    python enrich_words_with_ai.py --level A1 --limit 10
"""

import os
import sys
import time
import argparse
from typing import Optional, List
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.word import Word
from dotenv import load_dotenv

# Load environment variables
env_path = backend_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)


class WordEnricher:
    """Enriquece palavras usando IA para gerar definições e exemplos."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize AI clients
        self.deepseek_client = None
        self.openai_client = None
        
        if self.openai_api_key:
            print("✓ OpenAI configurado")
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        if self.deepseek_api_key:
            print("✓ DeepSeek configurado")
            self.deepseek_client = OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
        
        if not self.openai_client and not self.deepseek_client:
            raise ValueError(
                "Nenhuma API de IA configurada! Configure OPENAI_API_KEY ou DEEPSEEK_API_KEY"
            )
        
        # Statistics
        self.stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'api_calls': 0
        }
    
    def _get_ai_response(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Get response from AI (tries OpenAI first, then DeepSeek)."""
        self.stats['api_calls'] += 1
        
        # Try OpenAI first
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=300
                )
                content = response.choices[0].message.content
                return content.strip() if content else None
            except Exception as e:
                print(f"  ⚠️  OpenAI error: {e}")
        
        # Fallback to DeepSeek
        if self.deepseek_client:
            try:
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=300
                )
                content = response.choices[0].message.content
                return content.strip() if content else None
            except Exception as e:
                print(f"  ⚠️  DeepSeek error: {e}")
        
        return None
    
    def generate_definition_en(self, word: str, level: str) -> Optional[str]:
        """Generate English definition for a word."""
        prompt = f"""Create a clear, simple English definition for the word "{word}" suitable for {level} level learners.

Requirements:
- Use simple vocabulary appropriate for {level} level
- Be concise (1-2 sentences maximum)
- Focus on the most common meaning
- No examples in the definition itself

Return ONLY the definition text, nothing else."""
        
        return self._get_ai_response(prompt, temperature=0.5)
    
    def generate_definition_pt(self, word: str, english_def: Optional[str], level: str) -> Optional[str]:
        """Generate Portuguese definition for a word."""
        context = f"\nEnglish definition: {english_def}" if english_def else ""
        
        prompt = f"""Crie uma definição clara e simples em português para a palavra inglesa "{word}" adequada para estudantes de nível {level}.{context}

Requisitos:
- Use vocabulário simples apropriado para nível {level}
- Seja conciso (1-2 frases no máximo)
- Foque no significado mais comum
- Não inclua exemplos na definição

Retorne APENAS o texto da definição, nada mais."""
        
        return self._get_ai_response(prompt, temperature=0.5)
    
    def generate_example_en(self, word: str, level: str) -> Optional[str]:
        """Generate English example sentence."""
        prompt = f"""Create a natural English example sentence using the word "{word}" suitable for {level} level learners.

Requirements:
- Use vocabulary appropriate for {level} level
- Make it practical and realistic
- Show the word in common context
- Keep it simple and clear
- One sentence only

Return ONLY the example sentence, nothing else."""
        
        return self._get_ai_response(prompt, temperature=0.7)
    
    def generate_example_pt(self, word: str, english_example: Optional[str], level: str) -> Optional[str]:
        """Generate Portuguese translation of example."""
        if english_example:
            prompt = f"""Traduza esta frase inglesa para português brasileiro de forma natural:

"{english_example}"

Requisitos:
- Tradução natural e fluente
- Apropriada para estudantes de nível {level}
- Mantenha o contexto e significado original

Retorne APENAS a tradução, nada mais."""
        else:
            prompt = f"""Crie uma frase de exemplo natural em português usando a palavra inglesa "{word}" em contexto, adequada para estudantes de nível {level}.

Requisitos:
- Use vocabulário apropriado para nível {level}
- Seja prático e realista
- Mostre a palavra em contexto comum
- Mantenha simples e claro
- Apenas uma frase

Retorne APENAS a frase de exemplo, nada mais."""
        
        return self._get_ai_response(prompt, temperature=0.7)
    
    def enrich_word(self, word: Word, fields: List[str]) -> bool:
        """Enrich a single word with AI-generated content."""
        updated = False
        
        print(f"\n📝 Processando: {word.english} (nível {word.level})")
        
        # Generate definition_en
        if 'definition_en' in fields and not word.definition_en:
            print("  🔍 Gerando definition_en...")
            definition = self.generate_definition_en(word.english, word.level)
            if definition:
                word.definition_en = definition
                print(f"  ✓ definition_en: {definition[:60]}...")
                updated = True
            else:
                print("  ✗ Falha ao gerar definition_en")
        
        # Generate definition_pt
        if 'definition_pt' in fields and not word.definition_pt:
            print("  🔍 Gerando definition_pt...")
            definition = self.generate_definition_pt(
                word.english, 
                word.definition_en, 
                word.level
            )
            if definition:
                word.definition_pt = definition
                print(f"  ✓ definition_pt: {definition[:60]}...")
                updated = True
            else:
                print("  ✗ Falha ao gerar definition_pt")
        
        # Generate example_en
        if 'example_en' in fields and not word.example_en:
            print("  🔍 Gerando example_en...")
            example = self.generate_example_en(word.english, word.level)
            if example:
                word.example_en = example
                print(f"  ✓ example_en: {example[:60]}...")
                updated = True
            else:
                print("  ✗ Falha ao gerar example_en")
        
        # Generate example_pt
        if 'example_pt' in fields and not word.example_pt:
            print("  🔍 Gerando example_pt...")
            example = self.generate_example_pt(
                word.english,
                word.example_en,
                word.level
            )
            if example:
                word.example_pt = example
                print(f"  ✓ example_pt: {example[:60]}...")
                updated = True
            else:
                print("  ✗ Falha ao gerar example_pt")
        
        return updated
    
    def process_words(
        self,
        db: Session,
        fields: List[str],
        level: Optional[str] = None,
        batch_size: int = 50,
        limit: Optional[int] = None,
        delay: float = 1.0
    ):
        """Process words from database."""
        # Build query for words with missing fields
        query = db.query(Word)
        
        if level:
            query = query.filter(Word.level == level)
        
        # Filter for words missing at least one field
        conditions = []
        if 'definition_en' in fields:
            conditions.append(Word.definition_en.is_(None) | (Word.definition_en == ''))
        if 'definition_pt' in fields:
            conditions.append(Word.definition_pt.is_(None) | (Word.definition_pt == ''))
        if 'example_en' in fields:
            conditions.append(Word.example_en.is_(None) | (Word.example_en == ''))
        if 'example_pt' in fields:
            conditions.append(Word.example_pt.is_(None) | (Word.example_pt == ''))
        
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
        
        if limit:
            query = query.limit(limit)
        
        words = query.all()
        total = len(words)
        
        print(f"\n{'='*60}")
        print(f"📊 Total de palavras para processar: {total}")
        print(f"📋 Campos: {', '.join(fields)}")
        if level:
            print(f"🎯 Nível: {level}")
        print(f"{'='*60}\n")
        
        if self.dry_run:
            print("⚠️  MODO DRY-RUN: Nenhuma alteração será salva\n")
        
        for i, word in enumerate(words, 1):
            print(f"\n[{i}/{total}] ", end="")
            
            try:
                updated = self.enrich_word(word, fields)
                
                if updated:
                    if not self.dry_run:
                        db.commit()
                        print("  💾 Salvo no banco de dados")
                    else:
                        db.rollback()
                        print("  🔍 [DRY-RUN] Não salvo")
                    self.stats['updated'] += 1
                else:
                    print("  ⏭️  Nenhum campo atualizado")
                    self.stats['skipped'] += 1
                
                self.stats['processed'] += 1
                
                # Progress update every 10 words
                if i % 10 == 0:
                    self._print_progress()
                
                # Rate limiting
                if i < total and delay > 0:
                    time.sleep(delay)
                
            except Exception as e:
                print(f"  ❌ Erro: {e}")
                self.stats['errors'] += 1
                db.rollback()
                continue
        
        # Final statistics
        self._print_final_stats()
    
    def _print_progress(self):
        """Print progress statistics."""
        print(f"\n{'─'*60}")
        print(f"📊 Progresso: {self.stats['processed']} processadas")
        print(f"✓ Atualizadas: {self.stats['updated']}")
        print(f"⏭️  Puladas: {self.stats['skipped']}")
        print(f"❌ Erros: {self.stats['errors']}")
        print(f"🌐 Chamadas API: {self.stats['api_calls']}")
        print(f"{'─'*60}\n")
    
    def _print_final_stats(self):
        """Print final statistics."""
        print(f"\n{'='*60}")
        print(f"✅ CONCLUÍDO!")
        print(f"{'='*60}")
        print(f"📊 Total processadas: {self.stats['processed']}")
        print(f"✓ Atualizadas: {self.stats['updated']}")
        print(f"⏭️  Puladas: {self.stats['skipped']}")
        print(f"❌ Erros: {self.stats['errors']}")
        print(f"🌐 Total de chamadas API: {self.stats['api_calls']}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Enriquecer palavras com IA (gera definições e exemplos)"
    )
    parser.add_argument(
        '--fields',
        type=str,
        default='definition_en,definition_pt,example_en,example_pt',
        help='Campos para preencher (separados por vírgula)'
    )
    parser.add_argument(
        '--level',
        type=str,
        help='Filtrar por nível (A1, A2, B1, B2, C1, C2)'
    )
    parser.add_argument(
        '--batch',
        type=int,
        default=50,
        help='Tamanho do lote'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limitar número de palavras'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay entre chamadas (segundos)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Testar sem salvar no banco'
    )
    
    args = parser.parse_args()
    
    # Parse fields
    fields = [f.strip() for f in args.fields.split(',')]
    valid_fields = ['definition_en', 'definition_pt', 'example_en', 'example_pt']
    fields = [f for f in fields if f in valid_fields]
    
    if not fields:
        print("❌ Nenhum campo válido especificado!")
        print(f"Campos válidos: {', '.join(valid_fields)}")
        return
    
    # Database connection
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL não configurado!")
        return
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        enricher = WordEnricher(dry_run=args.dry_run)
        enricher.process_words(
            db=db,
            fields=fields,
            level=args.level,
            batch_size=args.batch,
            limit=args.limit,
            delay=args.delay
        )
    finally:
        db.close()


if __name__ == '__main__':
    main()
