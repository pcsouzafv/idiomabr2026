# Checklist de Deploy no GCP

Use este checklist para garantir que tudo está pronto antes de fazer deploy.

## 📋 Pré-requisitos (One-time Setup)

### 1. Ferramentas Instaladas
- [ ] gcloud CLI instalado e configurado
- [ ] Autenticado (`gcloud auth login`)
- [ ] Projeto configurado (`gcloud config set project idiomasbr`)
- [ ] Git Bash instalado (para Windows)

### 2. Cloud SQL (PostgreSQL)
- [ ] Instância criada (ex: `idiomasbr-db`)
- [ ] Database criado (ex: `idiomasbr`)
- [ ] Usuário e senha configurados
- [ ] Instância está RUNNABLE

### 3. Secret Manager
**Secrets obrigatórios:**
- [ ] `idiomasbr-database-url` criado
- [ ] `idiomasbr-secret-key` criado

**Secrets opcionais (AI):**
- [ ] `idiomasbr-openai-api-key` (se usar OpenAI)
- [ ] `idiomasbr-deepseek-api-key` (se usar DeepSeek)

**Comando para criar secrets:**
```bash
# DATABASE_URL (ajuste os valores)
printf %s "postgresql://USER:PASS@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE" | \
  gcloud secrets create idiomasbr-database-url --data-file=-

# SECRET_KEY
printf %s "sua-chave-secreta-forte-aqui" | \
  gcloud secrets create idiomasbr-secret-key --data-file=-

# OpenAI (opcional)
printf %s "$OPENAI_API_KEY" | \
  gcloud secrets create idiomasbr-openai-api-key --data-file=-

# DeepSeek (opcional)
printf %s "$DEEPSEEK_API_KEY" | \
  gcloud secrets create idiomasbr-deepseek-api-key --data-file=-
```

### 4. APIs Habilitadas
- [ ] Cloud Run API
- [ ] Artifact Registry API
- [ ] Cloud Build API
- [ ] Cloud SQL Admin API

**Comando para habilitar (o deploy_gcp.sh faz isso automaticamente):**
```bash
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    sqladmin.googleapis.com
```

## 🚀 Antes de Cada Deploy

### 1. Código Local
- [ ] Todas as mudanças commitadas no git (opcional, mas recomendado)
- [ ] Código testado localmente com Docker
- [ ] `.env` não está sendo commitado (verificar .gitignore)

### 2. Validação Automática
```bash
# Execute o script de validação
bash validate_deploy.sh
```

- [ ] Validação passou sem erros críticos
- [ ] Avisos revisados (se houver)

### 3. Configurações de Deploy

**Defina as variáveis de ambiente:**
```bash
export PROJECT_ID="idiomasbr"
export REGION="us-central1"
export DB_INSTANCE_NAME="idiomasbr-db"

# IMPORTANTE: Use tag única
export IMAGE_TAG="v$(date +%Y%m%d-%H%M%S)"
```

**Opcional - Se é o primeiro deploy ou migração:**
```bash
# Bootstrap secrets do Cloud Run atual
export BOOTSTRAP_SECRETS_FROM_CURRENT=true

# Criar secrets AI a partir do .env local
export CREATE_AI_SECRETS_FROM_ENV=true
export OPENAI_API_KEY="sua-chave"
export DEEPSEEK_API_KEY="sua-chave"

# Aplicar migrações SQL
export APPLY_MIGRATIONS=true
export DB_USER="seu-usuario"

# Fazer seed de palavras
export SEED_WORDS=true
```

## 🎯 Deploy

### Opção 1: Script Automatizado (Recomendado)
```bash
# Windows
quick_deploy.bat

# Linux/Mac
bash validate_deploy.sh && bash deploy_gcp.sh
```

### Opção 2: Manual
```bash
# Validar
bash validate_deploy.sh

# Deploy
export IMAGE_TAG="v$(date +%Y%m%d-%H%M%S)"
bash ./deploy_gcp.sh
```

### Durante o Deploy
- [ ] Backend build iniciou
- [ ] Backend push para Artifact Registry
- [ ] Backend deploy no Cloud Run
- [ ] Frontend build iniciou (com NEXT_PUBLIC_API_URL correto)
- [ ] Frontend push para Artifact Registry
- [ ] Frontend deploy no Cloud Run
- [ ] Migrações aplicadas (se APPLY_MIGRATIONS=true)
- [ ] Seed de palavras concluído (se SEED_WORDS=true)

## ✅ Pós-Deploy

### 1. Verificar URLs
```bash
# Backend URL
gcloud run services describe idiomasbr-backend \
  --region us-central1 --format 'value(status.url)'

# Frontend URL
gcloud run services describe idiomasbr-frontend \
  --region us-central1 --format 'value(status.url)'
```

- [ ] Backend URL obtida
- [ ] Frontend URL obtida

### 2. Testes Básicos
```bash
# Health check do backend
curl https://SUA_URL_BACKEND/health

# Verificar se retorna: {"status":"healthy"}
```

- [ ] Health check passou
- [ ] Frontend abre no navegador
- [ ] Login funciona
- [ ] API está respondendo

### 3. Verificar Logs (se houver problemas)
```bash
# Logs do backend
gcloud run services logs read idiomasbr-backend --region us-central1 --limit 50

# Logs do frontend
gcloud run services logs read idiomasbr-frontend --region us-central1 --limit 50

# Logs do Cloud Build
gcloud builds list --limit 5
gcloud builds log BUILD_ID
```

### 4. Monitoramento
- [ ] Verificar métricas no Cloud Console
- [ ] Configurar alertas (opcional)
- [ ] Verificar custos estimados

## 🔥 Em Caso de Problemas

### Build falhou?
1. Ver logs: `gcloud builds list --limit 5`
2. Ver detalhes: `gcloud builds log BUILD_ID`
3. Verificar Dockerfile e cloudbuild.yaml
4. Verificar permissões do Cloud Build service account

### Deploy falhou?
1. Ver logs: `gcloud run services logs read SERVICE_NAME --region us-central1`
2. Verificar secrets estão criados e com permissões corretas
3. Verificar Cloud SQL está acessível
4. Verificar DATABASE_URL está correta

### Aplicação não funciona?
1. **Erro de CORS**: Verificar backend/app/main.py permite o domínio do frontend
2. **Erro de banco**: Verificar DATABASE_URL e permissões do Cloud SQL
3. **Erro 500**: Ver logs detalhados do Cloud Run
4. **Frontend não conecta no backend**: Verificar NEXT_PUBLIC_API_URL

### Fazer Rollback
```bash
# Listar revisões
gcloud run revisions list --service idiomasbr-backend --region us-central1

# Voltar para revisão anterior
gcloud run services update-traffic idiomasbr-backend \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

## 📊 Comandos Úteis

### Ver imagens no Artifact Registry
```bash
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/idiomasbr/idiomasbr-repo
```

### Ver todas as revisões
```bash
gcloud run revisions list --service idiomasbr-backend --region us-central1
```

### Ver service accounts
```bash
gcloud iam service-accounts list
```

### Ver secrets
```bash
gcloud secrets list
gcloud secrets versions access latest --secret idiomasbr-database-url
```

### Limpar imagens antigas (economizar storage)
```bash
gcloud artifacts docker images delete \
  us-central1-docker.pkg.dev/idiomasbr/idiomasbr-repo/backend:TAG_ANTIGA
```

## 🎓 Dicas de Produção

- [ ] Rotacione secrets regularmente
- [ ] Use service accounts dedicados com permissões mínimas
- [ ] Configure Cloud Armor para proteção DDoS (opcional)
- [ ] Configure Cloud CDN para assets estáticos (opcional)
- [ ] Configure backup automático do Cloud SQL
- [ ] Configure alertas de monitoramento
- [ ] Configure budget alerts para evitar custos inesperados
- [ ] Use tags de versão semântica (v1.0.0, v1.0.1, etc.)

## 🔄 Deploy Contínuo (Opcional)

Para automatizar deploys a cada push:

1. Configure Cloud Build Triggers
2. Configure GitHub Actions
3. Use Workload Identity para autenticação

Ver documentação em: [CI/CD Setup Guide](https://cloud.google.com/run/docs/continuous-deployment)
