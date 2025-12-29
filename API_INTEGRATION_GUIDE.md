# 🌐 Guia de Integração com APIs de Dicionário

## 📚 APIs Utilizadas

### 1. **Free Dictionary API** (Principal)
- **URL**: https://dictionaryapi.dev/
- **Custo**: GRÁTIS (sem limite)
- **Sem cadastro**: Não precisa de API key
- **Dados fornecidos**:
  - ✅ Definições detalhadas
  - ✅ Tipo gramatical (noun, verb, etc)
  - ✅ Pronúncia (IPA)
  - ✅ Sinônimos e antônimos
  - ✅ Exemplos de uso
  - ✅ Áudio de pronúncia (URL)

**Exemplo de uso:**
```python
from services.dictionary_api import enrich_word_from_api

data = enrich_word_from_api("happy")
# Retorna: definição, sinônimos, exemplos, IPA, etc.
```

**Exemplo de resposta:**
```json
{
  "word_type": "adjective",
  "definition_en": "feeling or showing pleasure or contentment",
  "ipa": "ˈhæp.i",
  "synonyms": "joyful, cheerful, pleased",
  "antonyms": "sad, unhappy, miserable",
  "example_sentences": [
    {
      "en": "I'm happy to see you.",
      "pt": "Estou feliz em te ver."
    }
  ]
}
```

### 2. **Datamuse API** (Complementar)
- **URL**: https://www.datamuse.com/api/
- **Custo**: GRÁTIS (100.000 req/dia)
- **Sem cadastro**: Não precisa de API key
- **Dados fornecidos**:
  - ✅ Sinônimos (mais abrangente)
  - ✅ Palavras relacionadas
  - ✅ Colocações comuns
  - ✅ Rimas
  - ✅ Palavras que soam parecido

**Uso para sinônimos:**
```python
from services.dictionary_api import DictionaryAPI

api = DictionaryAPI()
synonyms = api.get_synonyms_datamuse("happy")
# ['joyful', 'cheerful', 'glad', 'pleased', 'delighted']
```

**Uso para colocações:**
```python
collocations = api.get_collocations_datamuse("happy")
# ['birthday', 'ending', 'hour', 'new', 'year']
```

### 3. **Opções Premium** (Futuro)

#### WordsAPI (RapidAPI)
- **Custo**: 2.500 req/dia GRÁTIS, depois pago
- **Dados**: Definições, exemplos, sinônimos, pronúncia
- **Requer**: Cadastro no RapidAPI

#### Merriam-Webster API
- **Custo**: 1.000 req/dia GRÁTIS
- **Dados**: Definições de alta qualidade
- **Requer**: Cadastro e API key

#### Oxford Dictionary API
- **Custo**: PAGO (mais caro)
- **Dados**: Definições premium, exemplos reais
- **Requer**: Conta paga

## 🚀 Como Usar

### Opção 1: Enriquecer TODAS as Palavras

```bash
# Docker
docker-compose exec backend python enrich_words_api.py

# Local
cd backend
python enrich_words_api.py
```

**Saída esperada:**
```
🚀 Iniciando enriquecimento via API...

📊 Total de palavras a processar: 5000
⏱️  Tempo estimado: ~25 minutos

[1/5000] hello... ✓
[2/5000] world... ✓
[3/5000] happy... ✓
...
[50/5000] learn... ✓

💾 Salvando progresso... (50 atualizadas)

...

===================================================
✅ ENRIQUECIMENTO CONCLUÍDO!

✓ Palavras atualizadas: 4523
⊘ Palavras sem novos dados: 377
✗ Palavras não encontradas: 100
📊 Total processado: 5000
===================================================
```

### Opção 2: Enriquecer Apenas Algumas Palavras

```bash
# Processar apenas 100 palavras
docker-compose exec backend python enrich_words_api.py --limit 100

# Processar palavras específicas
docker-compose exec backend python enrich_words_api.py --words happy learn time good
```

### Opção 3: Reprocessar Todas (incluindo já enriquecidas)

```bash
docker-compose exec backend python enrich_words_api.py --all
```

### Opção 4: Integrar no Import de Palavras

Você pode enriquecer palavras automaticamente ao importá-las:

```python
# Exemplo: import_words_with_enrichment.py
from app.models.word import Word
from app.core.database import SessionLocal
from services.dictionary_api import enrich_word_from_api

db = SessionLocal()

# Criar palavra
new_word = Word(
    english="amazing",
    portuguese="incrível",
    level="B1"
)
db.add(new_word)
db.flush()

# Enriquecer automaticamente
api_data = enrich_word_from_api("amazing")
if api_data:
    new_word.word_type = api_data.get("word_type")
    new_word.definition_en = api_data.get("definition_en")
    new_word.synonyms = api_data.get("synonyms")
    # ... etc

db.commit()
```

## ⚡ Performance e Rate Limiting

### Cache Automático
O sistema tem cache embutido para evitar requisições repetidas:

```python
api = DictionaryAPI()

# Primeira chamada: busca da API
data1 = api.get_word_data("happy")  # ~200ms

# Segunda chamada: retorna do cache
data2 = api.get_word_data("happy")  # ~0.1ms
```

### Rate Limiting
O script usa delay de **0.3 segundos** entre requisições:

```python
# Configurável
enrich_all_words(db, delay=0.3)  # 0.3s entre cada palavra

# Mais rápido (pode sobrecarregar API)
enrich_all_words(db, delay=0.1)

# Mais lento (mais seguro)
enrich_all_words(db, delay=0.5)
```

### Estimativa de Tempo

| Palavras | Delay | Tempo Estimado |
|----------|-------|----------------|
| 100      | 0.3s  | ~30 segundos   |
| 500      | 0.3s  | ~2.5 minutos   |
| 1000     | 0.3s  | ~5 minutos     |
| 5000     | 0.3s  | ~25 minutos    |
| 10000    | 0.3s  | ~50 minutos    |

## 🎯 Estratégia Recomendada

### Fase 1: Palavras Mais Comuns (A1-A2)
```bash
# Processar apenas níveis básicos primeiro
# (Requer modificação do script)
docker-compose exec backend python enrich_words_api.py --limit 1000
```

### Fase 2: Níveis Intermediários (B1-B2)
```bash
# Processar próximas 2000 palavras
docker-compose exec backend python enrich_words_api.py --limit 2000
```

### Fase 3: Níveis Avançados (C1-C2)
```bash
# Processar todas restantes
docker-compose exec backend python enrich_words_api.py
```

### Fase 4: Enriquecimento Contínuo
- Novas palavras são enriquecidas automaticamente ao serem adicionadas
- Revisão manual das palavras mais importantes
- Atualização periódica (mensal) de todas as palavras

## 🔧 Customização

### Adicionar Nova API

Edite `backend/services/dictionary_api.py`:

```python
class DictionaryAPI:
    def __init__(self):
        # ... APIs existentes
        self.nova_api_url = "https://api.example.com"
        self.nova_api_key = "sua_chave_aqui"

    def get_from_nova_api(self, word: str):
        response = requests.get(
            f"{self.nova_api_url}/{word}",
            headers={"Authorization": f"Bearer {self.nova_api_key}"}
        )
        # ... processar resposta
```

### Melhorar Tradução de Exemplos

O sistema atual usa tradução palavra-por-palavra (limitada). Para melhorar:

**Opção 1: Google Translate API** (PAGA)
```python
from googletrans import Translator

translator = Translator()
translated = translator.translate(text, src='en', dest='pt').text
```

**Opção 2: DeepL API** (Melhor qualidade, 500k char/mês grátis)
```python
import deepl

translator = deepl.Translator("sua_chave")
result = translator.translate_text(text, target_lang="PT-BR")
```

**Opção 3: OpenAI GPT (Mais cara, melhor contexto)**
```python
import openai

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{
        "role": "user",
        "content": f"Translate to Brazilian Portuguese: {text}"
    }]
)
translated = response.choices[0].message.content
```

### Adicionar Validação Manual

Crie uma rota admin para revisar e editar:

```python
# backend/app/routes/admin.py
@router.get("/words/to-review")
def get_words_to_review(db: Session = Depends(get_db)):
    """Retorna palavras que precisam de revisão."""
    return db.query(Word).filter(
        Word.definition_en != None,
        Word.manually_reviewed == False
    ).limit(50).all()

@router.put("/words/{word_id}/approve")
def approve_word(word_id: int, db: Session = Depends(get_db)):
    """Aprova palavra enriquecida."""
    word = db.query(Word).get(word_id)
    word.manually_reviewed = True
    db.commit()
    return {"status": "approved"}
```

## 📊 Monitoramento

### Ver Progresso

```sql
-- Palavras enriquecidas
SELECT COUNT(*)
FROM words
WHERE definition_en IS NOT NULL;

-- Palavras por tipo
SELECT word_type, COUNT(*)
FROM words
WHERE word_type IS NOT NULL
GROUP BY word_type
ORDER BY COUNT(*) DESC;

-- Palavras com exemplos
SELECT COUNT(*)
FROM words
WHERE example_sentences IS NOT NULL;

-- Palavras pendentes
SELECT COUNT(*)
FROM words
WHERE definition_en IS NULL;
```

### Dashboard de Qualidade

```sql
-- Qualidade do enriquecimento
SELECT
  COUNT(*) as total,
  COUNT(definition_en) as with_definition,
  COUNT(synonyms) as with_synonyms,
  COUNT(example_sentences) as with_examples,
  COUNT(usage_notes) as with_notes,
  ROUND(100.0 * COUNT(definition_en) / COUNT(*), 2) as pct_enriched
FROM words;
```

## 🐛 Troubleshooting

### Erro: "Connection timeout"
**Solução**: Aumentar timeout nas requisições
```python
response = requests.get(url, timeout=10)  # 10 segundos
```

### Erro: "Too many requests"
**Solução**: Aumentar delay entre requisições
```python
enrich_all_words(db, delay=1.0)  # 1 segundo
```

### Palavra não encontrada
**Solução**: Normal para algumas palavras. Opções:
1. Adicionar manualmente
2. Usar API alternativa
3. Marcar para revisão manual

### JSON inválido em example_sentences
**Solução**: Validar JSON antes de salvar
```python
import json

try:
    json.dumps(examples)
except:
    print(f"JSON inválido para {word.english}")
```

## 💡 Dicas

1. **Execute em lotes**: Processe 500-1000 palavras por vez
2. **Monitore progresso**: Use `--limit` para testar
3. **Backup primeiro**: Faça backup do banco antes de processar tudo
4. **Horário**: Execute à noite para não impactar usuários
5. **Logs**: Mantenha logs para auditoria

## 📞 APIs Alternativas

Se precisar de mais dados:

- **Cambridge Dictionary API**: https://dictionary.cambridge.org/
- **Collins Dictionary**: https://www.collinsdictionary.com/
- **Wordnik**: https://www.wordnik.com/
- **Linguee API**: https://linguee.com/ (bilíngue)
- **Reverso Context**: https://context.reverso.net/

---

**Desenvolvido para enriquecer automaticamente milhares de palavras! 🚀**
