# 🚀 Setup - Sistema de Enriquecimento de Palavras

## Passos para Implementação

### 1️⃣ Aplicar Migração do Banco de Dados

#### Docker (Recomendado):
```bash
# Copiar arquivo de migração para o container
docker cp backend/migrations/add_word_details.sql idiomasbr-postgres:/tmp/

# Executar migração
docker-compose exec postgres psql -U idiomasbr -d idiomasbr -f /tmp/add_word_details.sql
```

#### Local (PostgreSQL rodando localmente):
```bash
# Windows
psql -U idiomasbr -d idiomasbr -f backend/migrations/add_word_details.sql

# Linux/Mac
psql -U idiomasbr -d idiomasbr -f backend/migrations/add_word_details.sql
```

**Verificar se funcionou:**
```sql
-- Conectar ao banco
docker-compose exec postgres psql -U idiomasbr -d idiomasbr

-- Verificar colunas
\d words

-- Deve mostrar as novas colunas:
-- word_type, definition_en, definition_pt, synonyms, antonyms,
-- example_sentences, usage_notes, collocations
```

### 2️⃣ Enriquecer Palavras Existentes

#### Docker:
```bash
# Executar script de enriquecimento
docker-compose exec backend python enrich_words.py
```

#### Local:
```bash
# Ativar ambiente virtual
cd backend
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows

# Executar script
python enrich_words.py
```

**Saída esperada:**
```
🚀 Iniciando enriquecimento de palavras...
📊 Total de palavras: 5000
⏳ Processadas: 100/5000
⏳ Processadas: 200/5000
...
✅ Enriquecimento concluído!
📚 Palavras com dados completos: 15
🤖 Palavras com dados gerados: 4985
📊 Total processado: 5000
```

### 3️⃣ Reiniciar Backend

É necessário reiniciar o backend para carregar os novos campos do modelo:

#### Docker:
```bash
docker-compose restart backend
```

#### Local:
```bash
# Ctrl+C para parar o uvicorn
# Depois reiniciar:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4️⃣ Reiniciar Frontend (Se necessário)

O frontend já está atualizado, mas se houver cache:

#### Docker:
```bash
docker-compose restart frontend
```

#### Local:
```bash
# Ctrl+C para parar o Next.js
# Depois reiniciar:
npm run dev
```

### 5️⃣ Testar a Funcionalidade

1. Acesse: http://localhost:3000
2. Faça login
3. Vá para "Estudar Agora"
4. Configure uma sessão de estudo
5. Vire o card (clique ou pressione Espaço)
6. Verifique se aparecem:
   - ✅ Tipo da palavra (badge)
   - ✅ Definição
   - ✅ Sinônimos/Antônimos (se disponível)
   - ✅ Múltiplos exemplos
   - ✅ Colocações comuns
   - ✅ Dicas de uso (destaque âmbar)

## 📋 Checklist de Verificação

- [ ] Migração SQL executada com sucesso
- [ ] Script de enriquecimento rodou sem erros
- [ ] Backend reiniciado
- [ ] Frontend funcionando
- [ ] Novos campos aparecem nos flashcards
- [ ] Scroll funciona no card verso
- [ ] Estilo está correto (cores, espaçamento)

## 🐛 Problemas Comuns

### ❌ Erro: "column already exists"
**Causa**: Migração já foi executada antes
**Solução**: Ignorar, os campos já existem

### ❌ Erro: "relation words does not exist"
**Causa**: Banco de dados não foi criado
**Solução**: Execute `docker-compose up -d` e aguarde o PostgreSQL inicializar

### ❌ Cards não mostram novos dados
**Verificar**:
1. Backend foi reiniciado?
2. Script de enriquecimento foi executado?
3. Limpar cache do navegador (Ctrl+Shift+R)

### ❌ JSON.parse error no frontend
**Causa**: Campos JSON mal formatados
**Solução**: Execute novamente o script de enriquecimento

### ❌ Scroll não funciona no card
**Verificar**:
1. Arquivo `globals.css` foi atualizado?
2. Frontend foi reiniciado?
3. Cache do navegador foi limpo?

## 🎨 Customizações Opcionais

### Ajustar Altura Máxima do Card
Edite `frontend/src/app/study/page.tsx`:

```tsx
// Linha 865 - Mudar max-h-[600px] para sua preferência
<div className="card-back ... max-h-[800px] ...">
```

### Mudar Cores do Card Verso
Edite `frontend/src/app/study/page.tsx`:

```tsx
// Linha 865 - Alterar gradiente
<div className="card-back bg-gradient-to-br from-indigo-500 to-purple-600 ...">
```

### Adicionar Mais Palavras com Dados Completos

Edite `backend/enrich_words.py` e adicione ao dicionário `ENRICHED_DATA`:

```python
"learn": {
    "word_type": "verb",
    "definition_en": "to gain knowledge...",
    "definition_pt": "adquirir conhecimento...",
    # ... etc
}
```

Depois execute novamente:
```bash
docker-compose exec backend python enrich_words.py
```

## 📊 Banco de Dados - Queries Úteis

### Ver palavras enriquecidas:
```sql
SELECT english, word_type, definition_en, usage_notes
FROM words
WHERE word_type IS NOT NULL
LIMIT 10;
```

### Contar por tipo:
```sql
SELECT word_type, COUNT(*)
FROM words
WHERE word_type IS NOT NULL
GROUP BY word_type;
```

### Ver exemplos JSON:
```sql
SELECT english, example_sentences
FROM words
WHERE example_sentences IS NOT NULL
LIMIT 5;
```

### Atualizar palavra manualmente:
```sql
UPDATE words
SET
  word_type = 'verb',
  definition_en = 'to acquire knowledge',
  definition_pt = 'adquirir conhecimento',
  usage_notes = 'Verbo regular, passado: learned'
WHERE english = 'learn';
```

## ✅ Tudo Pronto!

Agora você tem um sistema completo de enriquecimento de palavras! 🎉

Para mais detalhes, consulte:
- `WORD_ENRICHMENT_GUIDE.md` - Guia completo
- `DOCUMENTACAO.md` - Documentação técnica geral
- `README.md` - Setup básico do projeto

---

**Problemas?** Abra uma issue no GitHub com detalhes do erro.
