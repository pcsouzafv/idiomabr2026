#!/usr/bin/env bash
# Script de validação pré-deploy
# Verifica se tudo está pronto antes de fazer deploy no GCP

set -euo pipefail

echo "🔍 Validando configurações para deploy no GCP..."
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Função para erro
error() {
    echo -e "${RED}❌ ERRO: $1${NC}"
    ((ERRORS++))
}

# Função para warning
warning() {
    echo -e "${YELLOW}⚠️  AVISO: $1${NC}"
    ((WARNINGS++))
}

# Função para sucesso
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo "1️⃣ Verificando gcloud CLI..."
if ! command -v gcloud >/dev/null 2>&1; then
    error "gcloud não encontrado. Instale: https://cloud.google.com/sdk/docs/install"
else
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$PROJECT_ID" ]]; then
        error "Projeto GCP não configurado. Execute: gcloud config set project SEU_PROJETO"
    else
        success "gcloud configurado (projeto: $PROJECT_ID)"
    fi
fi

echo ""
echo "2️⃣ Verificando autenticação..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q "@"; then
    ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
    success "Autenticado como: $ACCOUNT"
else
    error "Não autenticado. Execute: gcloud auth login"
fi

echo ""
echo "3️⃣ Verificando APIs habilitadas..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "artifactregistry.googleapis.com"
    "cloudbuild.googleapis.com"
    "sqladmin.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"; then
        success "API habilitada: $api"
    else
        warning "API não habilitada: $api (o script deploy_gcp.sh vai habilitar)"
    fi
done

echo ""
echo "4️⃣ Verificando arquivos necessários..."
FILES=(
    "backend/Dockerfile"
    "backend/cloudbuild.yaml"
    "backend/requirements.txt"
    "backend/app/main.py"
    "frontend/Dockerfile"
    "frontend/cloudbuild.yaml"
    "frontend/package.json"
    "deploy_gcp.sh"
)

for file in "${FILES[@]}"; do
    if [[ -f "$file" ]]; then
        success "Arquivo existe: $file"
    else
        error "Arquivo faltando: $file"
    fi
done

echo ""
echo "5️⃣ Verificando configurações do backend..."
if [[ -f "backend/requirements.txt" ]]; then
    if grep -q "fastapi" backend/requirements.txt && grep -q "uvicorn" backend/requirements.txt; then
        success "Dependências FastAPI encontradas"
    else
        error "FastAPI ou uvicorn não encontrado em requirements.txt"
    fi
fi

if [[ -f "backend/app/main.py" ]]; then
    if grep -q "FastAPI" backend/app/main.py; then
        success "FastAPI app encontrada em main.py"
    else
        warning "FastAPI não encontrado em main.py"
    fi
fi

echo ""
echo "6️⃣ Verificando configurações do frontend..."
if [[ -f "frontend/package.json" ]]; then
    if grep -q "next" frontend/package.json; then
        success "Next.js encontrado em package.json"
    else
        error "Next.js não encontrado em package.json"
    fi
fi

if [[ -f "frontend/next.config.js" ]]; then
    if grep -q "standalone" frontend/next.config.js; then
        success "Output 'standalone' configurado no Next.js"
    else
        warning "Output 'standalone' não encontrado (necessário para Cloud Run)"
    fi
fi

echo ""
echo "7️⃣ Verificando secrets no GCP..."
SECRET_NAMES=(
    "idiomasbr-database-url"
    "idiomasbr-secret-key"
)

for secret in "${SECRET_NAMES[@]}"; do
    if gcloud secrets describe "$secret" >/dev/null 2>&1; then
        success "Secret existe: $secret"
    else
        warning "Secret não existe: $secret (crie antes do deploy ou use BOOTSTRAP_SECRETS_FROM_CURRENT=true)"
    fi
done

# Secrets opcionais de IA
AI_SECRETS=(
    "idiomasbr-openai-api-key"
    "idiomasbr-deepseek-api-key"
)

for secret in "${AI_SECRETS[@]}"; do
    if gcloud secrets describe "$secret" >/dev/null 2>&1; then
        success "Secret AI existe: $secret"
    else
        warning "Secret AI não existe: $secret (opcional - pode criar com CREATE_AI_SECRETS_FROM_ENV=true)"
    fi
done

echo ""
echo "8️⃣ Verificando Cloud SQL..."
DB_INSTANCE="${DB_INSTANCE_NAME:-idiomasbr-db}"
if gcloud sql instances describe "$DB_INSTANCE" >/dev/null 2>&1; then
    success "Instância Cloud SQL existe: $DB_INSTANCE"

    # Verificar se está rodando
    STATUS=$(gcloud sql instances describe "$DB_INSTANCE" --format="value(state)" 2>/dev/null)
    if [[ "$STATUS" == "RUNNABLE" ]]; then
        success "Instância Cloud SQL está RUNNABLE"
    else
        warning "Instância Cloud SQL não está RUNNABLE (estado: $STATUS)"
    fi
else
    error "Instância Cloud SQL não encontrada: $DB_INSTANCE"
fi

echo ""
echo "9️⃣ Verificando Artifact Registry..."
REPO_NAME="${REPO_NAME:-idiomasbr-repo}"
REGION="${REGION:-us-central1}"
if gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" >/dev/null 2>&1; then
    success "Artifact Registry existe: $REPO_NAME"
else
    warning "Artifact Registry não existe: $REPO_NAME (será criado automaticamente)"
fi

echo ""
echo "🔟 Verificando serviços Cloud Run existentes..."
SERVICES=("idiomasbr-backend" "idiomasbr-frontend")
for service in "${SERVICES[@]}"; do
    if gcloud run services describe "$service" --platform managed --region "$REGION" >/dev/null 2>&1; then
        URL=$(gcloud run services describe "$service" --platform managed --region "$REGION" --format="value(status.url)" 2>/dev/null)
        success "Cloud Run existe: $service ($URL)"
    else
        warning "Cloud Run não existe: $service (será criado no primeiro deploy)"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESUMO DA VALIDAÇÃO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}✅ Tudo OK! Pronto para deploy.${NC}"
    echo ""
    echo "Execute:"
    echo "  export IMAGE_TAG=\"v\$(date +%Y%m%d-%H%M%S)\""
    echo "  bash ./deploy_gcp.sh"
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}⚠️  $WARNINGS avisos encontrados (não críticos)${NC}"
    echo ""
    echo "Você pode prosseguir com o deploy, mas revise os avisos acima."
    echo ""
    echo "Execute:"
    echo "  export IMAGE_TAG=\"v\$(date +%Y%m%d-%H%M%S)\""
    echo "  bash ./deploy_gcp.sh"
    exit 0
else
    echo -e "${RED}❌ $ERRORS erros encontrados${NC}"
    echo -e "${YELLOW}⚠️  $WARNINGS avisos encontrados${NC}"
    echo ""
    echo "Corrija os erros antes de fazer deploy."
    exit 1
fi
