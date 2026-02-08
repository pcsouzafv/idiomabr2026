# 📚 Guia de Atualização de Palavras

## 🔍 Problema Identificado

### Análise do arquivo `words_export.csv`

O arquivo contém **10.067 palavras**, mas muitas estão **incompletas**:

| Campo | Vazios | Porcentagem |
|-------|--------|-------------|
| `definition_en` | 2.971 | 29.5% |
| `definition_pt` | 4.612 | 45.8% |
| `example_en` | 6.757 | 67.1% |
| `example_pt` | 7.677 | 76.3% |

### 🚨 Por que isso é um problema?

Esses campos são **essenciais** para o funcionamento correto do sistema:

1. **`definition_en/pt`**: Necessários para explicar o significado das palavras aos alunos
2. **`example_en/pt`**: Necessários para mostrar contexto de uso prático
3. **`word_type`**: Importante para classificação gramatical (verb, noun, adjective, etc.)
4. **`ipa`**: Pronúncia fonética para ajudar na pronúncia correta

**Sem essas informações:**
- ❌ Os jogos de aprendizado ficam limitados
- ❌ Os alunos não têm contexto suficiente
- ❌ O sistema de revisão espaçada fica menos efetivo
- ❌ A experiência de aprendizado é prejudicada

---

## 📊 Estrutura dos Dados

### Esquema do Banco de Dados (tabela `words`)

```sql
CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    english VARCHAR(255) NOT NULL,      -- Palavra em inglês
    ipa VARCHAR(255),                    -- Pronúncia (IPA)
    portuguese VARCHAR(255) NOT NULL,    -- Tradução
    level VARCHAR(10) DEFAULT 'A1',      -- Nível CEFR
    
    -- Informações gramaticais
    word_type VARCHAR(50),               -- noun, verb, adjective, etc
    definition_en TEXT,                  -- Definição em inglês
    definition_pt TEXT,                  -- Definição em português
    synonyms TEXT,                       -- Sinônimos
    antonyms TEXT,                       -- Antônimos
    
    -- Exemplos de uso
    example_en TEXT,                     -- Exemplo em inglês
    example_pt TEXT,                     -- Exemplo em português
    example_sentences TEXT,              -- JSON com múltiplos exemplos
    usage_notes TEXT,                    -- Dicas de uso
    collocations TEXT,                   -- Colocações comuns
    
    -- Categorização
    tags VARCHAR(500),                   -- Tags separadas por vírgula
    audio_url VARCHAR(500)               -- URL do áudio
);
```

### Estrutura do CSV

```csv
id,english,ipa,portuguese,level,word_type,definition_en,definition_pt,example_en,example_pt,tags
42,abandon,əbændən,abandonar,A1,verb,"To give up...",,,,
```

---

## 🛠️ Soluções Implementadas

### Script: `update_words_from_csv.py`

Criei um script completo em `backend/scripts/update_words_from_csv.py` com as seguintes funcionalidades:

#### 1. 📊 **Análise** (sem modificar dados)

```bash
# Local
python backend/scripts/update_words_from_csv.py --analyze

# Docker
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
```

**O que faz:**
- Analisa o CSV e mostra estatísticas
- Analisa o banco de dados atual
- Identifica quantas palavras precisam de enriquecimento
- Fornece recomendações de ações

**Saída esperada:**
```
======================================================================
                         ANÁLISE DO CSV
======================================================================

📊 ESTATÍSTICAS GERAIS:
   Total de palavras: 10,067
   Palavras completas: 3,095 (30.7%)
   Precisam enriquecimento: 6,972 (69.3%)

📝 CAMPOS VAZIOS:
   IPA: 234 (2.3%)
   Tipo (word_type): 1,456 (14.5%)
   Definição EN: 2,971 (29.5%)
   Definição PT: 4,612 (45.8%)
   Exemplo EN: 6,757 (67.1%)
   Exemplo PT: 7,677 (76.3%)
   Tags: 5,234 (52.0%)
```

#### 2. 📥 **Importação** do CSV para o Banco

```bash
# DRY-RUN (visualiza o que será feito sem aplicar)
python backend/scripts/update_words_from_csv.py --import

# APLICAR mudanças
python backend/scripts/update_words_from_csv.py --import --apply

# Docker
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --apply
```

**O que faz:**
- Lê palavras do CSV
- Compara com palavras existentes no banco (case-insensitive)
- Atualiza apenas campos vazios (não sobrescreve dados existentes)
- Cria novas palavras se não existirem

**Lógica de atualização:**
```python
# Atualiza apenas se o campo no banco estiver vazio
if csv_data.definition_en and not db_word.definition_en:
    db_word.definition_en = csv_data.definition_en
```

#### 3. 🏷️ **Marcação** de Palavras Incompletas

```bash
# DRY-RUN
python backend/scripts/update_words_from_csv.py --mark-for-enrichment

# APLICAR
python backend/scripts/update_words_from_csv.py --mark-for-enrichment --apply

# Docker
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --mark-for-enrichment --apply
```

**O que faz:**
- Identifica palavras com campos vazios
- Adiciona a tag `needs_enrichment` nas palavras incompletas
- Permite processar essas palavras depois com APIs de enriquecimento

#### 4. 🔄 **Tudo de uma vez**

```bash
# Importar E marcar (DRY-RUN)
python backend/scripts/update_words_from_csv.py --import --mark-for-enrichment

# Importar E marcar (APLICAR)
python backend/scripts/update_words_from_csv.py --import --mark-for-enrichment --apply

# Docker
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply
```

---

## 📋 Passo a Passo Completo

### 1️⃣ Analisar Situação Atual

```bash
# Ver estado atual
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
```

### 2️⃣ Testar Importação (DRY-RUN)

```bash
# Ver o que será feito SEM modificar
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment
```

### 3️⃣ Aplicar Mudanças

```bash
# Aplicar importação e marcação
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply
```

### 4️⃣ Enriquecer Palavras Marcadas

Após importar e marcar, use o sistema de enriquecimento existente:

```bash
# Enriquecer palavras com tag 'needs_enrichment'
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment

# Ou processar por lotes
docker exec idiomasbr-backend python scripts/enrich_words_api.py --batch 100 --delay 2 --tags needs_enrichment
```

### 5️⃣ Verificar Progresso

```bash
# Ver estatísticas atualizadas
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
```

---

## 🔧 Opções Avançadas

### Especificar CSV Diferente

```bash
python backend/scripts/update_words_from_csv.py --csv-path /caminho/para/outro.csv --analyze
```

### Workflow Completo com Backup

```bash
# 1. Fazer backup do banco
docker exec -it idiomasbr-postgres pg_dump -U idiomasbr -d idiomasbr > backup_antes_update.sql

# 2. Analisar
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze

# 3. Testar (DRY-RUN)
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment

# 4. Aplicar
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply

# 5. Enriquecer
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment --batch 50

# 6. Verificar resultado
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
```

---

## 🎯 Estratégias de Enriquecimento

### Opção 1: Enriquecimento Automático via APIs

**Vantagens:**
- ✅ Rápido e automatizado
- ✅ Usa dados de dicionários confiáveis
- ✅ Já implementado no sistema

**Comandos:**
```bash
# Enriquecer usando Free Dictionary API
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment

# Ver guia completo
cat WORD_ENRICHMENT_GUIDE.md
```

### Opção 2: Enriquecimento Manual

**Vantagens:**
- ✅ Maior controle de qualidade
- ✅ Contexto específico para brasileiros
- ✅ Exemplos mais relevantes

**Como fazer:**

1. **Exportar palavras que precisam de atenção:**

```sql
-- Palavras sem definição em inglês
COPY (
    SELECT id, english, portuguese, level, word_type
    FROM words
    WHERE definition_en IS NULL OR definition_en = ''
    ORDER BY level, english
) TO '/tmp/words_need_definition_en.csv' WITH CSV HEADER;

-- Palavras sem exemplos
COPY (
    SELECT id, english, portuguese, level
    FROM words
    WHERE example_en IS NULL OR example_en = ''
    ORDER BY level, english
) TO '/tmp/words_need_examples.csv' WITH CSV HEADER;
```

2. **Editar manualmente e re-importar:**

```bash
# Criar CSV com atualizações
# id,english,definition_en,example_en,example_pt
# 42,abandon,"To give up","He had to abandon the car","Ele teve que abandonar o carro"

# Importar usando script customizado
python backend/scripts/import_manual_updates.py --csv manual_updates.csv --apply
```

### Opção 3: Híbrida (Recomendada)

1. Importar dados do CSV atual
2. Enriquecer automaticamente com APIs
3. Revisar manualmente palavras mais importantes (A1, A2)
4. Adicionar exemplos específicos para contexto brasileiro

---

## 📈 Métricas de Sucesso

### Antes da Atualização
- ❌ 29.5% sem definição em inglês
- ❌ 45.8% sem definição em português
- ❌ 67.1% sem exemplo em inglês
- ❌ 76.3% sem exemplo em português

### Meta Após Atualização
- ✅ 95%+ com definição em inglês
- ✅ 95%+ com definição em português
- ✅ 85%+ com exemplo em inglês
- ✅ 85%+ com exemplo em português
- ✅ 90%+ com word_type definido
- ✅ 100% com IPA (pronúncia)

---

## 🐛 Troubleshooting

### Erro: "CSV não encontrado"

```bash
# Verificar caminho
ls -la words_export.csv

# Especificar caminho completo
docker exec idiomasbr-backend python scripts/update_words_from_csv.py \
  --csv-path /app/words_export.csv \
  --analyze
```

### Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps postgres

# Ver logs
docker-compose logs postgres

# Reiniciar se necessário
docker-compose restart postgres
```

### Verificar se script está acessível no container

```bash
# Copiar para dentro do container se necessário
docker cp backend/scripts/update_words_from_csv.py idiomasbr-backend:/app/scripts/

# Ou executar do host
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
```

---

## 📚 Documentos Relacionados

- [WORD_ENRICHMENT_GUIDE.md](WORD_ENRICHMENT_GUIDE.md) - Guia completo de enriquecimento
- [SETUP_WORD_ENRICHMENT.md](SETUP_WORD_ENRICHMENT.md) - Setup inicial do sistema
- [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md) - Integração com APIs externas

---

## ✅ Checklist de Atualização

- [ ] Fazer backup do banco de dados
- [ ] Analisar estado atual (`--analyze`)
- [ ] Testar importação em DRY-RUN
- [ ] Aplicar importação (`--import --apply`)
- [ ] Marcar palavras incompletas (`--mark-for-enrichment --apply`)
- [ ] Enriquecer com APIs
- [ ] Verificar progresso
- [ ] Revisar manualmente palavras A1/A2
- [ ] Atualizar exemplos com contexto brasileiro
- [ ] Fazer backup final

---

## 📞 Suporte

Para mais informações sobre enriquecimento de palavras, consulte:
- [WORD_ENRICHMENT_GUIDE.md](WORD_ENRICHMENT_GUIDE.md)
- Script: `backend/scripts/enrich_words_api.py`
- Script: `backend/scripts/update_words_from_csv.py`
