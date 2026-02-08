# Como Atualizar a Aplicação no GCP

## O que foi corrigido

### Problema Identificado
O backend não tinha um arquivo `cloudbuild.yaml` dedicado, diferente do frontend. Isso causava inconsistências no processo de build e dificultava a atualização das imagens.

### Solução Implementada
1. ✅ Criado `backend/cloudbuild.yaml` (padronizado com o frontend)
2. ✅ Atualizado `deploy_gcp.sh` para usar o cloudbuild.yaml do backend
3. ✅ Agora backend e frontend usam o mesmo padrão de build

## Arquivos Modificados/Criados

- **NOVO**: `backend/cloudbuild.yaml` - Configuração de build do backend
- **MODIFICADO**: `deploy_gcp.sh` (linhas 98-103) - Usa cloudbuild.yaml do backend

## Como Atualizar no GCP

### 1. Preparação (apenas primeira vez)

Se ainda não configurou os secrets, siga o [GCP_DEPLOY_GUIDE.md](GCP_DEPLOY_GUIDE.md).

### 2. Atualização das Imagens Docker

Agora que você atualizou as imagens Docker localmente, rode:

```bash
# Configure as variáveis de ambiente
export PROJECT_ID="idiomasbr"
export REGION="us-central1"
export DB_INSTANCE_NAME="idiomasbr-db"

# IMPORTANTE: Use uma nova tag para forçar atualização
export IMAGE_TAG="v$(date +%Y%m%d-%H%M%S)"

# Execute o deploy
bash ./deploy_gcp.sh
```

### 3. Verificar se atualizou

Após o deploy, verifique:

```bash
# URL do backend
gcloud run services describe idiomasbr-backend \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'

# URL do frontend
gcloud run services describe idiomasbr-frontend \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)'

# Testar health check
curl https://SUA_URL_BACKEND/health
```

## Processo de Build Agora

### Backend (NOVO):
```
1. gcloud builds submit ./backend
2. Usa backend/cloudbuild.yaml
3. Build com Docker
4. Push para Artifact Registry com tag específica
5. Deploy no Cloud Run
```

### Frontend (já existia):
```
1. gcloud builds submit ./frontend
2. Usa frontend/cloudbuild.yaml
3. Build multi-stage com NEXT_PUBLIC_API_URL
4. Push para Artifact Registry com tag específica
5. Deploy no Cloud Run
```

## Vantagens da Padronização

1. **Consistência**: Backend e frontend usam o mesmo padrão
2. **Versionamento**: Tags únicas garantem atualização (não usa cache antigo)
3. **Rastreabilidade**: Cada build tem uma tag específica
4. **Rollback fácil**: Pode voltar para tags antigas se necessário

## Tags Recomendadas

```bash
# Desenvolvimento/teste
export IMAGE_TAG="dev-$(date +%Y%m%d-%H%M%S)"

# Produção (com número de versão)
export IMAGE_TAG="v1.2.3"

# Baseado no commit git
export IMAGE_TAG="$(git rev-parse --short HEAD)"

# Automático (padrão do script)
# Usa git sha se disponível, senão timestamp
```

## Forçar Rebuild Completo

Se precisar forçar um rebuild completo (sem cache):

```bash
# Para backend
gcloud builds submit ./backend \
    --config ./backend/cloudbuild.yaml \
    --no-cache \
    --substitutions=_REGION="us-central1",_REPO_NAME="idiomasbr-repo",_TAG="v-new-$(date +%s)"

# Para frontend
gcloud builds submit ./frontend \
    --config ./frontend/cloudbuild.yaml \
    --no-cache \
    --substitutions=_NEXT_PUBLIC_API_URL="https://SUA_URL_BACKEND",_REGION="us-central1",_REPO_NAME="idiomasbr-repo",_TAG="v-new-$(date +%s)"
```

## Troubleshooting

### Imagem não está atualizando?

1. **Verifique a tag**: Use tags únicas (não reutilize `latest`)
```bash
export IMAGE_TAG="v$(date +%s)"  # Timestamp Unix único
```

2. **Limpe o cache do Cloud Build**:
```bash
gcloud builds submit --no-cache ...
```

3. **Verifique qual imagem está rodando**:
```bash
gcloud run services describe idiomasbr-backend \
  --region us-central1 \
  --format 'value(spec.template.spec.containers[0].image)'
```

### Deploy falhou?

1. **Veja os logs do Cloud Build**:
```bash
gcloud builds list --limit=5
gcloud builds log BUILD_ID
```

2. **Veja os logs do Cloud Run**:
```bash
gcloud run services logs read idiomasbr-backend --region us-central1
```

### Backend não conecta no banco?

Verifique se o secret DATABASE_URL está correto:
```bash
gcloud secrets versions access latest --secret="idiomasbr-database-url"
```

## Próximos Passos

Após o deploy bem-sucedido:

1. Teste todas as funcionalidades principais
2. Verifique os logs para erros
3. Monitore o desempenho no Cloud Console
4. Configure alertas de monitoramento (opcional)

## Comandos Úteis

```bash
# Listar todas as imagens no Artifact Registry
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/idiomasbr/idiomasbr-repo

# Deletar imagens antigas (economizar storage)
gcloud artifacts docker images delete \
  us-central1-docker.pkg.dev/idiomasbr/idiomasbr-repo/backend:TAG_ANTIGA

# Ver todas as revisões do Cloud Run
gcloud run revisions list \
  --service idiomasbr-backend \
  --region us-central1

# Fazer rollback para revisão anterior
gcloud run services update-traffic idiomasbr-backend \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```
