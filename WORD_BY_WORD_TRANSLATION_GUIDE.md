# 🤖 Guia: Geração de Traduções Palavra-por-Palavra

## 📋 Objetivo
Orientar o backend para gerar traduções com formato palavra-por-palavra que o frontend possa processar visualmente.

---

## 🎯 Formato Esperado

### Estrutura
```
[palavra1] [palavra2] palavra3 [palavra4]
```

### Regras
1. **Colchetes** `[]` indicam palavras importantes ou que são tradução direta
2. **Sem colchetes**: artigos, preposições e palavras de ligação que não possuem tradução direta
3. **Barra** `/` pode ser usada para alternativas: `um/uma`, `o/a`

---

## 📝 Exemplos Práticos

### Exemplo 1: "I received several calls today"
```json
{
  "example_en": "I received several calls today.",
  "example_pt": "[I] [recebi] [várias] [calls] hoje"
}
```

**Renderização:**
- `[I]` → badge azul claro
- `[recebi]` → badge azul claro
- `[várias]` → badge azul claro
- `[calls]` → badge azul claro (palavra estudada em destaque)
- `hoje` → texto normal

---

### Exemplo 2: "I paid a call to a dear friend of mine"
```json
{
  "example_en": "I paid a call to a dear friend of mine.",
  "example_pt": "[I] [paid] um/uma [call] [to] um/uma [dear] [friend] [of] [mine.]"
}
```

**Renderização:**
- Palavras entre colchetes: badges
- `um/uma`: texto normal (artigo sem equivalente direto em inglês)

---

## 🔧 Implementação com IA (OpenAI/Anthropic)

### Prompt para GPT-4 / Claude

```python
prompt = f"""
Você é um assistente especializado em ensino de idiomas.

Tarefa: Gerar tradução palavra-por-palavra de uma frase em inglês para português.

Regras:
1. Use [palavra] para indicar palavras que têm tradução direta
2. Deixe sem colchetes: artigos, preposições e conjunções que não têm equivalente direto
3. Use "/" para alternativas (ex: um/uma, o/a)
4. Mantenha pontuação dentro dos colchetes da última palavra
5. A palavra estudada ({word}) deve sempre estar entre colchetes

Exemplo de entrada:
"I love this beautiful city"

Exemplo de saída:
"[I] [love] este/esta [beautiful] [city]"

Agora traduza:
"{sentence}"

Responda APENAS com a tradução no formato palavra-por-palavra.
"""
```

---

### Script Python Exemplo

```python
import openai

def generate_word_by_word_translation(english_sentence: str, target_word: str) -> str:
    """
    Gera tradução palavra-por-palavra com colchetes para destaque visual.
    
    Args:
        english_sentence: Frase em inglês
        target_word: Palavra sendo estudada (será destacada)
    
    Returns:
        Tradução formatada: "[I] [received] [várias] [calls] hoje"
    """
    
    prompt = f"""
Você é um assistente de ensino de idiomas. Traduza a frase abaixo do inglês para o português 
usando o formato palavra-por-palavra com colchetes.

Regras:
1. Coloque [palavra] para palavras com tradução direta
2. Deixe sem colchetes: artigos (o, a, um, uma), preposições simples (de, em, para) quando não têm equivalente direto
3. Use "/" para alternativas: um/uma, o/a
4. A palavra "{target_word}" DEVE estar entre colchetes
5. Mantenha a ordem natural do português

Frase: "{english_sentence}"

Responda APENAS com a tradução no formato palavra-por-palavra, sem explicações.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um especialista em ensino de idiomas."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=200
    )
    
    translation = response.choices[0].message.content.strip()
    return translation


# Uso
sentence = "I received several calls today"
word = "call"

result = generate_word_by_word_translation(sentence, word)
print(result)
# Output: "[I] [recebi] [várias] [calls] hoje"
```

---

## 🗄️ Estrutura no Banco de Dados

### Tabela: `words`

```sql
-- Exemplo de palavra enriquecida
UPDATE words 
SET 
  example_en = 'I received several calls today.',
  example_pt = '[I] [recebi] [várias] [calls] hoje',
  example_sentences = JSON_ARRAY(
    JSON_OBJECT(
      'en', 'I received several calls today.',
      'pt', '[I] [recebi] [várias] [calls] hoje'
    ),
    JSON_OBJECT(
      'en', 'She makes important calls every morning.',
      'pt', '[She] [faz] [importantes] [calls] toda manhã'
    )
  )
WHERE english = 'call';
```

---

## 🎨 Renderização no Frontend (Já Implementada)

A função `formatWordByWordTranslation()` processa automaticamente:

```tsx
// Input: "[I] [recebi] [várias] [calls] hoje"
// Output visual:
<span>
  <span className="badge">[I]</span>
  <span className="badge">[recebi]</span>
  <span className="badge">[várias]</span>
  <span className="badge">[calls]</span>
  <span className="text">hoje</span>
</span>
```

---

## 📊 Casos Especiais

### 1. Phrasal Verbs
```
Entrada: "I gave up smoking"
Saída: "[I] [gave up] o/a fumar"
```
(phrasal verb como unidade única)

### 2. Expressões Idiomáticas
```
Entrada: "It's raining cats and dogs"
Saída: "[Está] [chovendo] muito forte"
```
(tradução do sentido, não literal)

### 3. Pronomes Possessivos
```
Entrada: "This is my car"
Saída: "Este/Esta é [meu/minha] [carro/carro]"
```

### 4. Contrações
```
Entrada: "I'm going home"
Saída: "[Eu] [estou indo] para casa"
```
(expandir contração)

---

## ✅ Validação

### Checklist para Qualidade:
- [ ] Palavra estudada está entre colchetes?
- [ ] Artigos sem equivalente direto estão sem colchetes?
- [ ] Ordem das palavras faz sentido em português?
- [ ] Alternativas (um/uma) estão formatadas corretamente?
- [ ] Pontuação está no lugar certo?

---

## 🚀 Script de Enriquecimento em Lote

```python
import pandas as pd
from tqdm import tqdm
import time

def enrich_examples_with_word_by_word(words_df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa todas as palavras e adiciona traduções palavra-por-palavra.
    """
    
    enriched_words = []
    
    for idx, row in tqdm(words_df.iterrows(), total=len(words_df)):
        word = row['english']
        example_en = row['example_en']
        
        # Pular se já tiver tradução no formato correto
        if pd.notna(row['example_pt']) and '[' in row['example_pt']:
            enriched_words.append(row)
            continue
        
        # Gerar tradução palavra-por-palavra
        if pd.notna(example_en):
            try:
                word_by_word = generate_word_by_word_translation(example_en, word)
                row['example_pt'] = word_by_word
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"Erro na palavra '{word}': {e}")
        
        enriched_words.append(row)
    
    return pd.DataFrame(enriched_words)


# Uso
df = pd.read_sql("SELECT * FROM words WHERE example_en IS NOT NULL", conn)
enriched_df = enrich_examples_with_word_by_word(df)

# Salvar de volta no banco
enriched_df.to_sql('words', conn, if_exists='replace', index=False)
```

---

## 💡 Dicas de Otimização

1. **Cache de traduções comuns:**
   ```python
   common_translations = {
       "I": "[I]",
       "you": "[você]",
       "the": "",  # sem tradução
       "a": "um/uma",
   }
   ```

2. **Processamento em lote:**
   - Enviar múltiplas frases em uma única chamada à API
   - Usar async/await para paralelizar

3. **Fallback:**
   - Se a IA falhar, usar tradução simples sem colchetes
   - Frontend ainda renderizará corretamente

---

## 📚 Recursos Adicionais

### APIs Úteis
- **OpenAI GPT-4:** Melhor para traduções complexas
- **Google Translate API:** Bom para tradução básica
- **DeepL API:** Alta qualidade em português

### Bibliotecas Python
- `openai` - Integração com GPT
- `anthropic` - Integração com Claude
- `googletrans` - Google Translate (free)
- `deep-translator` - Múltiplos serviços

---

**Status:** 📝 Guia Completo  
**Pronto para Implementação no Backend**
