# Guia de Sincronização de Banco de Dados

## Problema

O banco de dados de **produção (GCP Cloud SQL)** está diferente do banco de **homologação (local/Docker)**. Você precisa sincronizar os dados.

## Soluções Disponíveis

Criamos scripts que oferecem **5 opções** de sincronização:

### 1️⃣ Aplicar Migrações (RECOMENDADO - Seguro)

**O que faz**: Aplica mudanças de schema (ALTER TABLE, ADD COLUMN, etc)
**Segurança**: ✅ Seguro - Não remove dados existentes
**Quando usar**: Quando você adicionou novas colunas ou alterou estrutura

```bash
# Windows
sync_database.bat
# Escolha opção 1

# Linux/Mac
bash sync_database.sh migrations
```

**Arquivos aplicados**:
- `backend/migrations/add_word_details.sql` - Adiciona colunas de detalhes nas palavras
- `backend/migrations/add_is_admin_to_users.sql` - Adiciona flag de admin nos usuários

### 2️⃣ Importar Palavras (RECOMENDADO - Seguro)

**O que faz**: Importa palavras dos arquivos CSV para o banco
**Segurança**: ✅ Seguro - Adiciona/atualiza sem remover existentes
**Quando usar**: Quando você tem novas palavras para adicionar

```bash
# Windows
sync_database.bat
# Escolha opção 2

# Linux/Mac
bash sync_database.sh seed-words
```

**Arquivos importados**:
- `backend/data/seed_words_core_unique.csv` - Palavras essenciais
- `backend/data/seed_words_extra_unique_v3.csv` - Palavras extras

### 3️⃣ Restauração Completa (CUIDADO - Destrutivo)

**O que faz**: Apaga TUDO e restaura do dump completo
**Segurança**: ⚠️ PERIGOSO - Remove todos os dados
**Quando usar**: Apenas se precisa resetar completamente ou tem backup

```bash
# Windows
sync_database.bat
# Escolha opção 3
# Digite "SIM" para confirmar

# Linux/Mac
bash sync_database.sh full-restore
# Digite "SIM" para confirmar
```

**ATENÇÃO**:
- Remove TODOS os usuários existentes
- Remove TODO o progresso de aprendizado
- Remove TODAS as configurações
- Use apenas se tiver certeza!

### 4️⃣ Exportar Produção (Backup)

**O que faz**: Baixa uma cópia do banco de produção
**Segurança**: ✅ Seguro - Apenas leitura
**Quando usar**: Para fazer backup ou analisar dados

```bash
# Windows
sync_database.bat
# Escolha opção 4

# Linux/Mac
bash sync_database.sh export-prod
```

**Resultado**: Cria arquivo `dump_prod_YYYYMMDD_HHMMSS.sql`

### 5️⃣ Comparar Esquemas (Análise)

**O que faz**: Mostra diferenças entre local e produção
**Segurança**: ✅ Seguro - Apenas visualização
**Quando usar**: Para descobrir o que está diferente

```bash
# Windows
sync_database.bat
# Escolha opção 5

# Linux/Mac
bash sync_database.sh compare
```

## Fluxo Recomendado

### Cenário 1: Primeira sincronização (banco novo)

```bash
# 1. Aplicar estrutura do banco (migrações)
bash sync_database.sh migrations

# 2. Importar dados (palavras)
bash sync_database.sh seed-words
```

### Cenário 2: Atualizar banco existente

```bash
# 1. Fazer backup primeiro (importante!)
bash sync_database.sh export-prod

# 2. Aplicar novas migrações
bash sync_database.sh migrations

# 3. Adicionar novas palavras (se houver)
bash sync_database.sh seed-words
```

### Cenário 3: Resetar tudo (último recurso)

```bash
# 1. Fazer backup primeiro (IMPORTANTE!)
bash sync_database.sh export-prod

# 2. Restaurar dump completo
bash sync_database.sh full-restore
# Digite "SIM" para confirmar
```

## Estrutura de Arquivos

```
projeto/
├── sync_database.sh          # Script principal (Linux/Mac)
├── sync_database.bat          # Script principal (Windows)
│
├── backend/
│   ├── migrations/            # Migrações SQL
│   │   ├── add_word_details.sql
│   │   └── add_is_admin_to_users.sql
│   │
│   └── data/                  # Dados para importar
│       ├── seed_words_core_unique.csv
│       └── seed_words_extra_unique_v3.csv
│
├── dump_final.sql             # Dump completo (backup local)
└── cloudbuild.*.yaml          # Configs do Cloud Build
```

## Como Funciona Internamente

### Migrações (opção 1)

```bash
1. Script encontra todos os .sql em backend/migrations/
2. Para cada arquivo:
   - Envia para Cloud Build
   - Cloud Build usa cloudbuild.migrate.yaml
   - Conecta no Cloud SQL via proxy
   - Executa o SQL (ALTER TABLE, etc)
   - Retorna sucesso/erro
```

### Seed de Palavras (opção 2)

```bash
1. Script encontra todos os CSV em backend/data/
2. Envia lista de arquivos para Cloud Build
3. Cloud Build usa cloudbuild.seed_words.yaml
4. Executa backend/import_words.py:
   - Lê cada CSV
   - Faz INSERT ou UPDATE (UPSERT)
   - Não remove palavras existentes
```

### Restauração Completa (opção 3)

```bash
1. Faz upload do dump para Cloud Storage (bucket temporário)
2. Usa gcloud sql import para restaurar:
   - DROP de todas as tabelas
   - CREATE de estrutura nova
   - INSERT de todos os dados
```

## Troubleshooting

### Erro: "gcloud not found"
**Solução**: Instale o gcloud CLI
```bash
# https://cloud.google.com/sdk/docs/install
```

### Erro: "Permission denied"
**Solução**: Autentique no gcloud
```bash
gcloud auth login
gcloud config set project idiomasbr
```

### Erro: "Secret not found"
**Solução**: Certifique-se que os secrets existem
```bash
gcloud secrets list | grep idiomasbr
# Deve mostrar: idiomasbr-database-url
```

### Erro: "Cloud SQL instance not found"
**Solução**: Verifique se a instância está correta
```bash
gcloud sql instances list
# Deve mostrar: idiomasbr-db (RUNNABLE)
```

### Migração falhou
**Causa comum**: Coluna já existe (se rodou 2x)
**Solução**: Migrações usam `IF NOT EXISTS` - é seguro rodar múltiplas vezes

### Import de palavras falhou
**Causa comum**: Formato do CSV incorreto
**Solução**: Verifique se CSV tem cabeçalho correto:
```csv
english,portuguese,level,category,phonetic,audio_url
hello,olá,A1,greetings,,
```

## Logs e Monitoramento

### Ver logs do Cloud Build
```bash
# Listar builds recentes
gcloud builds list --limit=5

# Ver logs de um build específico
gcloud builds log BUILD_ID
```

### Ver logs do Cloud SQL
```bash
gcloud sql operations list --instance idiomasbr-db --limit=5
```

### Verificar dados no banco
```bash
# Conectar via psql (requer psql instalado)
gcloud sql connect idiomasbr-db --user=postgres --database=idiomasbr

# Dentro do psql:
SELECT COUNT(*) FROM words;
SELECT COUNT(*) FROM users;
\dt  # Listar tabelas
```

## Custos

### Cloud Build
- **Primeiros 120 build-minutes/dia**: Grátis
- **Depois**: $0.003/build-minute
- **Estimativa**: Migrações/seeds levam ~2-5 min = ~$0.01 por sync

### Cloud Storage (imports/exports temporários)
- **Storage**: $0.020/GB-month
- **Transferência**: Primeira 1GB grátis
- **Estimativa**: ~$0.01-0.05 por operação

### Cloud SQL Proxy
- Grátis (incluído no Cloud SQL)

## Próximos Passos

### Automação
Você pode integrar no CI/CD:

```yaml
# .github/workflows/deploy.yml
- name: Sync Database
  run: |
    bash sync_database.sh migrations
    bash sync_database.sh seed-words
```

### Backups Automáticos
Configure no Cloud SQL:

```bash
gcloud sql instances patch idiomasbr-db \
  --backup-start-time=03:00 \
  --backup-retention=7
```

### Monitoramento
Configure alertas de falhas:

```bash
# Cloud Monitoring
# Criar alerta para falhas de backup
# Criar alerta para baixa disponibilidade
```

## Comandos Rápidos

```bash
# Fazer tudo (primeira vez)
bash sync_database.sh migrations && bash sync_database.sh seed-words

# Backup antes de mudança importante
bash sync_database.sh export-prod

# Reset completo (com confirmação)
bash sync_database.sh full-restore

# Ver ajuda
bash sync_database.sh --help
```

## Suporte

Se tiver problemas:

1. Verifique os logs do Cloud Build
2. Verifique se o Cloud SQL está RUNNABLE
3. Verifique se os secrets estão configurados
4. Teste conexão: `gcloud sql connect idiomasbr-db --user=postgres`
