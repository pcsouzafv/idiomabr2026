#!/usr/bin/env python3
"""
Script para enriquecer palavras usando Ollama LOCAL (GRATUITO e ILIMITADO!)
Mesma qualidade das APIs pagas, mas sem custo de tokens.

Uso:
    python enrich_words_with_ollama.py --batch 100 --limit 500
    python enrich_words_with_ollama.py --fields definition_pt,example_en,example_pt
    python enrich_words_with_ollama.py --level A1 --limit 1000
"""

import os
import sys
import time
import argparse
import requests
from typing import Optional, List
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker, Session
from app.models.word import Word
from dotenv import load_dotenv

# Load environment variables
env_path = backend_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)


class OllamaWordEnricher:
    """Enriquece palavras usando Ollama LOCAL - GRATUITO e ILIMITADO!"""
    
    def __init__(self, model: str = "llama3.2:3b", dry_run: bool = False):
        self.dry_run = dry_run
        self.model = model
        self.ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
        
        print(f"🦙 Ollama URL: {self.ollama_url}")
        print(f"🤖 Modelo: {self.model}")
        
        # Test connection
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                print(f"✓ Ollama conectado! Modelos disponíveis: {', '.join(model_names)}")
                
                # Check if our model is available
                if not any(self.model in name for name in model_names):
                    print(f"⚠️  Modelo {self.model} não encontrado. Baixando...")
                    self._pull_model()
            else:
                print(f"⚠️  Ollama respondeu com status {response.status_code}")
        except Exception as e:
            print(f"❌ Erro ao conectar com Ollama: {e}")
            print("   Verifique se o container idiomasbr-ollama está rodando!")
            sys.exit(1)
        
        # Statistics
        self.stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'api_calls': 0,
            'total_tokens': 0  # Ollama é grátis, mas vamos contar para comparação
        }
    
    def _pull_model(self):
        """Download model if not available"""
        print(f"📥 Baixando modelo {self.model}... Isso pode demorar alguns minutos.")
        try:
            response = requests.post(
                f"{self.ollama_url}/api/pull",
                json={"name": self.model},
                stream=True,
                timeout=600
            )
            for line in response.iter_lines():
                if line:
                    data = line.decode('utf-8')
                    print(f"  {data}")
            print("✓ Modelo baixado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao baixar modelo: {e}")
            sys.exit(1)
    
    def _call_ollama(self, prompt: str, temperature: float = 0.7) -> Optional[str]:
        """Call Ollama API"""
        self.stats['api_calls'] += 1
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                
                # Track tokens (even though they're free!)
                self.stats['total_tokens'] += result.get('prompt_eval_count', 0)
                self.stats['total_tokens'] += result.get('eval_count', 0)
                
                return content if content else None
            else:
                print(f"  ⚠️  Ollama error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"  ⚠️  Ollama exception: {e}")
            return None
    
    def generate_definition_en(self, word: str, level: str) -> Optional[str]:
        """Generate English definition"""
        prompt = f"""Create a clear, simple English definition for the word "{word}" suitable for {level} level English learners.

Requirements:
- Use simple vocabulary appropriate for {level} level
- Be concise (1-2 sentences maximum)
- Focus on the most common meaning
- No examples in the definition itself

Return ONLY the definition text, nothing else."""
        
        return self._call_ollama(prompt, temperature=0.5)
    
    def generate_definition_pt(self, word: str, english_def: Optional[str], level: str) -> Optional[str]:
        """Generate Portuguese definition"""
        context = f"\nEnglish definition: {english_def}" if english_def else ""
        
        prompt = f"""Crie uma definição clara e simples em português brasileiro para a palavra inglesa "{word}" adequada para estudantes de nível {level}.{context}

Requisitos:
- Use vocabulário simples apropriado para nível {level}
- Seja conciso (1-2 frases no máximo)
- Foque no significado mais comum
- Não inclua exemplos na definição

Retorne APENAS o texto da definição em português, nada mais."""
        
        return self._call_ollama(prompt, temperature=0.5)
    
    def generate_example_en(self, word: str, level: str) -> Optional[str]:
        """Generate English example sentence"""
        prompt = f"""Create a natural English example sentence using the word "{word}" suitable for {level} level learners.

Requirements:
- Use vocabulary appropriate for {level} level
- Make it practical and realistic
- Show the word in common context
- Keep it simple and clear
- One sentence only

Return ONLY the example sentence, nothing else."""
        
        return self._call_ollama(prompt, temperature=0.7)
    
    def generate_example_pt(self, word: str, english_example: Optional[str], level: str) -> Optional[str]:
        """Generate Portuguese translation of example"""
        if english_example:
            prompt = f"""Traduza esta frase inglesa para português brasileiro de forma natural:

"{english_example}"

Requisitos:
- Tradução natural e fluente
- Apropriada para estudantes de nível {level}
- Mantenha o contexto e significado original

Retorne APENAS a tradução em português, nada mais."""
        else:
            prompt = f"""Crie uma frase de exemplo natural em português brasileiro usando a palavra inglesa "{word}" em contexto, adequada para estudantes de nível {level}.

Requisitos:
- Use vocabulário apropriado para nível {level}
- Seja prático e realista
- Mostre a palavra em contexto comum
- Mantenha simples e claro
- Apenas uma frase

Retorne APENAS a frase de exemplo em português, nada mais."""
        
        return self._call_ollama(prompt, temperature=0.7)
    
    def enrich_word(self, word: Word, fields: List[str]) -> bool:
        """Enrich a single word"""
        updated = False
        
        print(f"\n📝 [{word.id}] {word.english} (nível {word.level})")
        
        # Generate definition_en
        if 'definition_en' in fields and not word.definition_en:
            print("  🔍 Gerando definition_en...")
            definition = self.generate_definition_en(word.english, word.level)
            if definition:
                word.definition_en = definition
                print(f"  ✓ definition_en: {definition[:60]}...")
                updated = True
        
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
        
        # Generate example_en
        if 'example_en' in fields and not word.example_en:
            print("  🔍 Gerando example_en...")
            example = self.generate_example_en(word.english, word.level)
            if example:
                word.example_en = example
                print(f"  ✓ example_en: {example[:60]}...")
                updated = True
        
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
        
        return updated
    
    def process_words(
        self,
        db: Session,
        fields: List[str],
        level: Optional[str] = None,
        batch_size: int = 50,
        limit: Optional[int] = None,
        delay: float = 0.3
    ):
        """Process words from database"""
        # Build query for words with missing fields
        query = db.query(Word)
        
        # Filter by level if specified
        if level:
            query = query.filter(Word.level == level)
        
        # Filter words that need enrichment
        conditions = []
        if 'definition_en' in fields:
            conditions.append(Word.definition_en.is_(None))
            conditions.append(Word.definition_en == '')
        if 'definition_pt' in fields:
            conditions.append(Word.definition_pt.is_(None))
            conditions.append(Word.definition_pt == '')
        if 'example_en' in fields:
            conditions.append(Word.example_en.is_(None))
            conditions.append(Word.example_en == '')
        if 'example_pt' in fields:
            conditions.append(Word.example_pt.is_(None))
            conditions.append(Word.example_pt == '')
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        # Apply limit
        if limit:
            query = query.limit(limit)
        
        words = query.all()
        total = len(words)
        
        if total == 0:
            print("\n✓ Nenhuma palavra precisa de enriquecimento!")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 Total de palavras para processar: {total}")
        print(f"📋 Campos: {', '.join(fields)}")
        print(f"🦙 Usando Ollama LOCAL - 100% GRATUITO!")
        print(f"{'='*60}\n")
        
        batch_count = 0
        
        for i, word in enumerate(words, 1):
            self.stats['processed'] += 1
            
            print(f"\n[{i}/{total}]", end=" ")
            
            if self.dry_run:
                print(f"[DRY-RUN] Seria processado: {word.english}")
                continue
            
            try:
                updated = self.enrich_word(word, fields)
                
                if updated:
                    self.stats['updated'] += 1
                    batch_count += 1
                    print("  💾 Salvo no banco de dados")
                else:
                    self.stats['skipped'] += 1
                    print("  ⊘ Nenhum campo atualizado")
                
                # Commit batch
                if batch_count >= batch_size:
                    db.commit()
                    print(f"\n💾 Batch salvo ({batch_count} palavras)")
                    batch_count = 0
                
                # Delay between requests (Ollama local é rápido, mas evita sobrecarga)
                if i < total:
                    time.sleep(delay)
                    
            except Exception as e:
                self.stats['errors'] += 1
                print(f"  ✗ Erro: {e}")
                db.rollback()
        
        # Final commit
        if batch_count > 0:
            db.commit()
            print(f"\n💾 Batch final salvo ({batch_count} palavras)")
        
        # Print statistics
        print(f"\n{'='*60}")
        print("✅ ENRIQUECIMENTO CONCLUÍDO COM OLLAMA!")
        print(f"{'='*60}")
        print(f"\n✓ Palavras atualizadas: {self.stats['updated']}")
        print(f"⊘ Palavras ignoradas: {self.stats['skipped']}")
        print(f"✗ Erros: {self.stats['errors']}")
        print(f"📊 Total processado: {self.stats['processed']}")
        print(f"🔄 Chamadas à API: {self.stats['api_calls']}")
        print(f"🎯 Tokens usados: {self.stats['total_tokens']:,} (GRATUITOS!)")
        print(f"\n💰 Custo total: $0.00 (vs ~${self.stats['updated'] * 0.0005:.2f} com OpenAI)")
        print(f"{'='*60}\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Enriquecimento de palavras via Ollama LOCAL (GRATUITO!)"
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='llama3.2:3b',
        help='Modelo Ollama a usar (padrão: llama3.2:3b)'
    )
    
    parser.add_argument(
        '--fields',
        type=str,
        default='definition_pt,example_en,example_pt',
        help='Campos a preencher (separados por vírgula)'
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
        help='Tamanho do lote para commit (padrão: 50)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Número máximo de palavras a processar'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.3,
        help='Delay entre requisições em segundos (padrão: 0.3)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sem modificar banco de dados'
    )
    
    args = parser.parse_args()
    
    # Parse fields
    fields = [f.strip() for f in args.fields.split(',')]
    
    # Create enricher
    enricher = OllamaWordEnricher(model=args.model, dry_run=args.dry_run)
    
    # Create database session
    database_url = os.getenv('DATABASE_URL', 'postgresql://idiomasbr:idiomasbr123@postgres:5432/idiomasbr')
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
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
