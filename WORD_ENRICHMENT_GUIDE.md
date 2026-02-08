# 📚 Guia de Enriquecimento de Palavras - IdiomasBR

## 🎯 Visão Geral

Este guia documenta as melhorias implementadas no sistema de palavras, adicionando informações detalhadas que enriquecem a experiência de aprendizado.

## 🆕 Novos Campos Adicionados

### 1. **word_type** (Tipo Gramatical)
- **Tipo**: String (50 caracteres)
- **Valores**: noun, verb, adjective, adverb, preposition, etc.
- **Exemplo**: "verb", "adjective"
- **Uso**: Exibido como badge no flashcard para contexto gramatical

### 2. **definition_en** (Definição em Inglês)
- **Tipo**: Text
- **Exemplo**: "to exist, to have a specified quality or nature"
- **Uso**: Ajuda a entender o significado na língua original

### 3. **definition_pt** (Definição em Português)
- **Tipo**: Text
- **Exemplo**: "existir, ter uma qualidade ou natureza especificada"
- **Uso**: Reforça a compreensão em português

### 4. **synonyms** (Sinônimos)
- **Tipo**: Text
- **Formato**: Separados por vírgula
- **Exemplo**: "exist, remain, live"
- **Uso**: Expande vocabulário relacionado

### 5. **antonyms** (Antônimos)
- **Tipo**: Text
- **Formato**: Separados por vírgula
- **Exemplo**: "bad, poor, terrible, awful"
- **Uso**: Ajuda a entender contraste de significados

### 6. **example_sentences** (Múltiplos Exemplos)
- **Tipo**: Text (JSON)
- **Formato**: Array de objetos `{en: string, pt: string}`
- **Exemplo**:
```json
[
  {"en": "I am a student.", "pt": "Eu sou um estudante."},
  {"en": "She is happy today.", "pt": "Ela está feliz hoje."}
]
```
- **Uso**: Múltiplos contextos de uso da palavra

### 7. **usage_notes** (Notas de Uso)
- **Tipo**: Text
- **Exemplo**: "O verbo 'be' é irregular e fundamental. Use 'am/is/are' no presente, 'was/were' no passado."
- **Uso**: Dicas importantes sobre quando e como usar a palavra

### 8. **collocations** (Colocações Comuns)
- **Tipo**: Text (JSON)
- **Formato**: Array de strings
- **Exemplo**: `["be careful", "be ready", "be sure", "be able to"]`
- **Uso**: Expressões e combinações comuns com a palavra

## 🚀 Como Usar

### 1. Migração do Banco de Dados

Execute a migração SQL para adicionar os novos campos:

```bash
# No Docker
docker-compose exec postgres psql -U idiomasbr -d idiomasbr -f /migrations/add_word_details.sql

# Ou localmente
psql -U idiomasbr -d idiomasbr -f backend/migrations/add_word_details.sql
```

### 2. Enriquecer Palavras Existentes

Execute o script Python para popular as palavras:

```bash
# No Docker
docker-compose exec backend python enrich_words.py

# Ou localmente
cd backend
python enrich_words.py
```

O script irá:
- ✅ Adicionar dados completos para palavras comuns (predefinidos)
- ✅ Gerar informações básicas para outras palavras
- ✅ Detectar automaticamente o tipo gramatical
- ✅ Criar exemplos contextualizados

### 3. Adicionar Novas Palavras Enriquecidas

Ao adicionar novas palavras via API, use o formato completo:

```python
from app.models.word import Word
import json

new_word = Word(
    english="learn",
    ipa="/lɜːrn/",
    portuguese="aprender",
    level="A1",

    # Informações gramaticais
    word_type="verb",
    definition_en="to gain knowledge or skill by studying, practicing, or being taught",
    definition_pt="adquirir conhecimento ou habilidade estudando, praticando ou sendo ensinado",
    synonyms="study, acquire, master",

    # Exemplos
    example_sentences=json.dumps([
        {"en": "I learn English every day.", "pt": "Eu aprendo inglês todos os dias."},
        {"en": "She learns quickly.", "pt": "Ela aprende rápido."},
        {"en": "They learned a lot.", "pt": "Eles aprenderam muito."}
    ]),

    usage_notes="Verbo regular. Passado: learned (US) ou learnt (UK). Comum com 'to' (learn to swim).",

    collocations=json.dumps([
        "learn a language",
        "learn from mistakes",
        "learn by heart",
        "learn the hard way"
    ])
)
```

## 🎨 Interface do Usuário

### Flashcard - Frente
- Palavra principal
- IPA (pronúncia)
- Botão de áudio (Text-to-Speech)

### Flashcard - Verso (NOVO!)
Agora mostra de forma organizada:

1. **Cabeçalho**
   - Tradução
   - IPA (se PT→EN)
   - Badge do tipo gramatical (noun, verb, etc.)

2. **Definição**
   - Definição na língua de destino

3. **Sinônimos e Antônimos**
   - Grid com sinônimos e antônimos

4. **Exemplos**
   - Até 3 frases de exemplo com tradução
   - Formatação clara (itálico para EN, tradução em menor)

5. **Colocações Comuns**
   - Badges com expressões comuns
   - Limite de 6 para não sobrecarregar

6. **Dicas de Uso**
   - Destaque especial (fundo âmbar)
   - Informações importantes sobre gramática e uso

## 📊 Estatísticas

### Palavras com Dados Completos
- ✅ Verbos básicos: be, have, do, go, get, make, etc.
- ✅ Substantivos comuns: time, person, day, etc.
- ✅ Adjetivos: good, new, happy, etc.
- ✅ Advérbios: very, well, etc.
- ✅ Preposições: in, on, at, etc.

### Palavras com Dados Gerados
- ✅ Tipo gramatical detectado automaticamente
- ✅ Exemplos básicos gerados por padrão
- ✅ Estrutura pronta para enriquecimento manual

## 🔧 Personalização

### Adicionar Mais Palavras com Dados Completos

Edite `backend/enrich_words.py` e adicione ao dicionário `ENRICHED_DATA`:

```python
ENRICHED_DATA = {
    "sua_palavra": {
        "word_type": "noun",
        "definition_en": "...",
        "definition_pt": "...",
        "synonyms": "...",
        "antonyms": "...",
        "example_sentences": json.dumps([...]),
        "usage_notes": "...",
        "collocations": json.dumps([...])
    }
}
```

### Melhorar Detecção de Tipo

A função `detect_word_type()` usa padrões morfológicos. Você pode adicionar mais padrões:

```python
def detect_word_type(word: str) -> str:
    word_lower = word.lower()

    # Adicione seus padrões aqui
    if word_lower.endswith('ção'):
        return "noun"

    # ... resto do código
```

## 💡 Melhores Práticas

### 1. Definições
- ✅ Use linguagem clara e objetiva
- ✅ Foque no significado mais comum primeiro
- ❌ Evite definições circulares

### 2. Sinônimos
- ✅ Liste apenas sinônimos próximos
- ✅ Mantenha no mesmo nível (A1 com A1)
- ❌ Não liste palavras muito avançadas

### 3. Exemplos
- ✅ Use contextos do dia a dia
- ✅ Varie os sujeitos (I, you, he, she, they)
- ✅ Mantenha frases curtas (máx. 10 palavras)
- ❌ Evite estruturas muito complexas

### 4. Notas de Uso
- ✅ Inclua irregularidades (be → am/is/are)
- ✅ Mencione diferenças US/UK se relevante
- ✅ Aponte erros comuns de brasileiros
- ❌ Não sobrecarregue com detalhes

### 5. Colocações
- ✅ Liste as 4-6 mais comuns
- ✅ Priorize uso frequente em conversação
- ❌ Evite expressões muito formais ou raras

## 🎯 Próximos Passos

### Melhorias Futuras
- [ ] Integração com API de dicionário (WordNet, Oxford)
- [ ] Áudio real das palavras (TTS premium ou gravações)
- [ ] Imagens ilustrativas para substantivos
- [ ] Quiz específico de colocações
- [ ] Exercícios de preencher lacunas com sinônimos
- [ ] Favoritos e anotações pessoais

### IA Generativa (Futuro)
- [ ] Gerar definições automaticamente via GPT-4
- [ ] Criar exemplos contextualizados dinamicamente
- [ ] Sugerir sinônimos baseado em nível do usuário
- [ ] Traduzir notas de uso automaticamente

## 📝 Changelog

### v2.0.0 - 2025-12-15
- ✅ Adicionados 8 novos campos ao modelo Word
- ✅ Criada migração SQL
- ✅ Desenvolvido script de enriquecimento automático
- ✅ Interface do flashcard completamente redesenhada
- ✅ Dados completos para 15+ palavras mais comuns
- ✅ Sistema de detecção automática de tipo gramatical
- ✅ Geração inteligente de exemplos

## 🆘 Troubleshooting

### Erro: "column does not exist"
**Solução**: Execute a migração SQL primeiro

### Erro: JSON parse error
**Solução**: Verifique se `example_sentences` e `collocations` são JSON válidos

### Flashcard muito grande
**Solução**: O scroll está habilitado automaticamente. Ajuste `max-h-[600px]` se necessário

### Dados não aparecem
**Solução**:
1. Verifique se a migração foi executada
2. Execute o script `enrich_words.py`
3. Confirme que o backend foi reiniciado

## 📞 Suporte

Para dúvidas ou sugestões sobre o sistema de enriquecimento:
- Abra uma issue no GitHub
- Consulte a documentação técnica em `DOCUMENTACAO.md`

---

**Desenvolvido com ❤️ para melhorar o aprendizado de inglês!**
