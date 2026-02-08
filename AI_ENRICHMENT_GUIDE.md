# 🤖 Guia de Enriquecimento com IA

Sistema automatizado para preencher campos vazios nas palavras usando **OpenAI** ou **DeepSeek**.

## 📊 Situação Atual

- **Total de palavras**: 10,067
- **Campos vazios**:
  - `definition_en`: 2,971 (29.5%)
  - `definition_pt`: 4,612 (45.8%)
  - `example_en`: 6,757 (67.1%)
  - `example_pt`: 7,677 (76.3%)

## 🚀 Como Usar

### 1. Configurar APIs

Edite o arquivo `.env` e adicione suas chaves de API:

```bash
# Pelo menos UMA dessas chaves é necessária
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
```

### 2. Opção A: Menu Interativo (Recomendado)

```bash
# Windows
enrich_ai.bat

# Linux/Mac
chmod +x enrich_ai.sh
./enrich_ai.sh
```

Opções do menu:
1. **Teste**: 10 palavras em modo dry-run (não salva)
2. **Nível A1**: 50 palavras do nível A1
3. **Nível A2**: 50 palavras do nível A2
4. **Todos os níveis**: 100 palavras
5. **TUDO**: Processa todas as 10,067 palavras ⚠️
6. **Custom**: Especificar parâmetros manualmente

### 3. Opção B: Linha de Comando

```bash
# Teste sem salvar (dry-run)
python backend/scripts/enrich_words_with_ai.py --limit 10 --dry-run

# Processar nível A1
python backend/scripts/enrich_words_with_ai.py --level A1 --limit 50

# Processar apenas definições
python backend/scripts/enrich_words_with_ai.py --fields definition_en,definition_pt --limit 100

# Processar apenas exemplos
python backend/scripts/enrich_words_with_ai.py --fields example_en,example_pt --limit 100

# Processar tudo (cuidado!)
python backend/scripts/enrich_words_with_ai.py --delay 1.5
```

## 📋 Parâmetros

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `--fields` | Campos para preencher (separados por vírgula) | `definition_en,definition_pt,example_en,example_pt` |
| `--level` | Filtrar por nível (A1, A2, B1, B2, C1, C2) | Todos |
| `--limit` | Limitar número de palavras | Todas |
| `--delay` | Delay entre chamadas API (segundos) | 1.0 |
| `--batch` | Tamanho do lote (não usado atualmente) | 50 |
| `--dry-run` | Testar sem salvar no banco | False |

## 🎯 Exemplos de Uso

### Testar Primeiro
```bash
# Sempre teste primeiro!
python backend/scripts/enrich_words_with_ai.py --limit 5 --dry-run
```

### Processar por Nível
```bash
# Começar pelo mais fácil
python backend/scripts/enrich_words_with_ai.py --level A1 --limit 100
python backend/scripts/enrich_words_with_ai.py --level A2 --limit 100
python backend/scripts/enrich_words_with_ai.py --level B1 --limit 100
```

### Processar por Campo
```bash
# Primeiro as definições em inglês
python backend/scripts/enrich_words_with_ai.py --fields definition_en --limit 200

# Depois as definições em português
python backend/scripts/enrich_words_with_ai.py --fields definition_pt --limit 200

# Por último os exemplos
python backend/scripts/enrich_words_with_ai.py --fields example_en,example_pt --limit 200
```

## 💰 Custos Estimados

### OpenAI (gpt-4o-mini)
- **Input**: $0.150 / 1M tokens
- **Output**: $0.600 / 1M tokens
- **Estimativa por palavra**: ~300 tokens (input + output)
- **Custo por palavra**: ~$0.0002
- **Custo para 10,000 palavras**: ~$2.00

### DeepSeek
- **Custo**: ~70% mais barato que OpenAI
- **Custo para 10,000 palavras**: ~$0.60

## ⚠️ Avisos Importantes

1. **Teste Sempre Primeiro**: Use `--dry-run` e `--limit 10` para testar
2. **Rate Limiting**: Use `--delay 1.0` ou mais para evitar bloqueios
3. **Custos**: Processar 10,000 palavras custará $1-2 em APIs
4. **Tempo**: ~3-4 horas para processar tudo (com delay 1.5s)
5. **Backup**: Faça backup do banco antes de processar tudo

## 📊 Estatísticas em Tempo Real

O script mostra:
- ✅ Palavras atualizadas
- ⏭️ Palavras puladas (já completas)
- ❌ Erros
- 🌐 Total de chamadas API
- 📊 Progresso a cada 10 palavras

## 🔧 Como Funciona

1. **Busca palavras** com campos vazios no banco
2. **Gera conteúdo** usando IA (OpenAI ou DeepSeek)
3. **Valida** se o conteúdo foi gerado
4. **Salva** no banco de dados
5. **Rate limiting** para evitar bloqueios
6. **Progresso** em tempo real

### Prompts da IA

O script usa prompts especializados:

- **definition_en**: Definição clara em inglês, nível apropriado
- **definition_pt**: Tradução/adaptação da definição em português
- **example_en**: Frase de exemplo natural em inglês
- **example_pt**: Tradução natural da frase em português

## 🎯 Estratégia Recomendada

### Fase 1: Teste (5 minutos)
```bash
python backend/scripts/enrich_words_with_ai.py --limit 10 --dry-run
```

### Fase 2: Piloto (30 minutos)
```bash
python backend/scripts/enrich_words_with_ai.py --level A1 --limit 50
```

### Fase 3: Por Nível (2-3 horas)
```bash
# Processar cada nível separadamente
for level in A1 A2 B1 B2 C1 C2; do
  python backend/scripts/enrich_words_with_ai.py --level $level --delay 1.0
done
```

### Fase 4: Finalizações (1 hora)
```bash
# Preencher o que ficou faltando
python backend/scripts/enrich_words_with_ai.py --delay 1.5
```

## 🔍 Troubleshooting

### Erro: "Nenhuma API de IA configurada"
- Configure `OPENAI_API_KEY` ou `DEEPSEEK_API_KEY` no `.env`

### Erro: "DATABASE_URL não configurado"
- Verifique se `.env` tem `DATABASE_URL`

### API Rate Limit
- Aumente o `--delay` para 2.0 ou 3.0

### Respostas Vazias
- IA pode falhar ocasionalmente, palavras serão puladas

### Script Travou
- Ctrl+C para parar
- Progresso já foi salvo no banco
- Pode retomar executando novamente

## 📈 Monitoramento

### Verificar Progresso
```sql
-- Quantas palavras ainda faltam
SELECT 
    COUNT(*) FILTER (WHERE definition_en IS NULL OR definition_en = '') as missing_def_en,
    COUNT(*) FILTER (WHERE definition_pt IS NULL OR definition_pt = '') as missing_def_pt,
    COUNT(*) FILTER (WHERE example_en IS NULL OR example_en = '') as missing_ex_en,
    COUNT(*) FILTER (WHERE example_pt IS NULL OR example_pt = '') as missing_ex_pt
FROM words;
```

### Verificar Qualidade
```sql
-- Verificar exemplos de palavras enriquecidas
SELECT english, definition_en, example_en
FROM words
WHERE definition_en IS NOT NULL
ORDER BY RANDOM()
LIMIT 5;
```

## 🎉 Próximos Passos

Após enriquecer as palavras:

1. **Validar qualidade**: Revisar amostra aleatória
2. **Backup**: Fazer backup do banco enriquecido
3. **Deploy**: Atualizar produção
4. **Monitorar**: Verificar feedback dos usuários
5. **Iterar**: Melhorar prompts se necessário

## 💡 Dicas

- **Comece pequeno**: Teste com 10-50 palavras primeiro
- **Use níveis**: Processar por nível é mais organizado
- **Monitore custos**: Acompanhe gastos na dashboard da OpenAI/DeepSeek
- **Backup regular**: Faça backup antes de grandes processamentos
- **Pause e retome**: Pode parar (Ctrl+C) e retomar depois
