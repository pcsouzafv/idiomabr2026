#!/usr/bin/env bash
# Script de Deploy para Google Cloud Run
# Automatiza build/push de imagens + deploy de backend e frontend.
#
# Importante: NÃO deixe segredos hardcoded aqui.
# Use Secret Manager + --set-secrets no Cloud Run.

set -euo pipefail

# =====================
# Configurações (override via env)
# =====================
PROJECT_ID="${PROJECT_ID:-idiomasbr}"
REGION="${REGION:-us-central1}"
REPO_NAME="${REPO_NAME:-idiomasbr-repo}"

BACKEND_SERVICE="${BACKEND_SERVICE:-idiomasbr-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-idiomasbr-frontend}"

# Nome da instância do Cloud SQL (Postgres) (ex: idiomasbr-db)
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-idiomasbr-db}"
CLOUDSQL_CONNECTION_NAME="${CLOUDSQL_CONNECTION_NAME:-$PROJECT_ID:$REGION:$DB_INSTANCE_NAME}"

# Tag da imagem (por padrão, tenta usar o git sha; se não existir, usa 'latest')
IMAGE_TAG="${IMAGE_TAG:-}"
if [[ -z "$IMAGE_TAG" ]]; then
    IMAGE_TAG="$(git rev-parse --short HEAD 2>/dev/null || true)"
fi
if [[ -z "$IMAGE_TAG" ]]; then
    # Se não há git disponível (ou não é um repo git), use timestamp para evitar
    # "deploy sem mudança" em tags fixas como :latest.
    IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
fi

# Secret Manager (recomendado)
USE_SECRET_MANAGER="${USE_SECRET_MANAGER:-true}"
DATABASE_URL_SECRET_NAME="${DATABASE_URL_SECRET_NAME:-idiomasbr-database-url}"
SECRET_KEY_SECRET_NAME="${SECRET_KEY_SECRET_NAME:-idiomasbr-secret-key}"

# AI (opcional) via Secret Manager
OPENAI_API_KEY_SECRET_NAME="${OPENAI_API_KEY_SECRET_NAME:-idiomasbr-openai-api-key}"
DEEPSEEK_API_KEY_SECRET_NAME="${DEEPSEEK_API_KEY_SECRET_NAME:-idiomasbr-deepseek-api-key}"
USE_OLLAMA_FALLBACK_ENV="${USE_OLLAMA_FALLBACK_ENV:-false}"
OLLAMA_URL_ENV="${OLLAMA_URL_ENV:-}"
FRONTEND_BASE_URL_ENV="${FRONTEND_BASE_URL_ENV:-https://idiomasbr.com}"

# Se true e os secrets de IA não existirem, cria a partir das variáveis de ambiente
# OPENAI_API_KEY / DEEPSEEK_API_KEY (do seu terminal). Não grava nada no repositório.
CREATE_AI_SECRETS_FROM_ENV="${CREATE_AI_SECRETS_FROM_ENV:-false}"

# Se true e os secrets de IA não existirem, tenta copiar do Cloud Run atual (BACKEND_SERVICE)
# Útil para migração sem downtime quando a app antiga já tinha env vars.
BOOTSTRAP_AI_SECRETS_FROM_CURRENT="${BOOTSTRAP_AI_SECRETS_FROM_CURRENT:-false}"

# Se true, falha o deploy se OpenAI/DeepSeek não estiverem configurados (secrets ou env)
REQUIRE_AI_SECRETS="${REQUIRE_AI_SECRETS:-false}"

# Se true, ao não encontrar os secrets, cria eles automaticamente usando os valores
# atuais do Cloud Run (BACKEND_SERVICE). Útil para migrar uma app existente sem downtime.
# Recomendação: depois rode novamente com valores novos (rotate) e revogue qualquer segredo exposto.
BOOTSTRAP_SECRETS_FROM_CURRENT="${BOOTSTRAP_SECRETS_FROM_CURRENT:-false}"

# Migração (opcional)
APPLY_MIGRATIONS="${APPLY_MIGRATIONS:-false}"
DB_USER="${DB_USER:-}"
DB_NAME="${DB_NAME:-idiomasbr}"
MIGRATION_FILE="${MIGRATION_FILE:-backend/migrations/add_word_details.sql}"

# Seed de dados (opcional) - palavras via CSV
SEED_WORDS="${SEED_WORDS:-false}"
WORD_FILES="${WORD_FILES:-backend/data/seed_words_core_unique.csv,backend/data/seed_words_extra_unique_v3.csv}"

echo "🚀 Iniciando deploy para o projeto: $PROJECT_ID (região: $REGION, tag: $IMAGE_TAG)"

command -v gcloud >/dev/null 2>&1 || { echo "Erro: 'gcloud' não encontrado no PATH."; exit 1; }

# Garantir projeto configurado
gcloud config set project "$PROJECT_ID" >/dev/null

# 1. Habilitar APIs necessárias
echo "📦 Habilitando APIs do Google Cloud..."
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    sqladmin.googleapis.com

# 2. Criar repositório no Artifact Registry (se não existir)
echo "🏭 Verificando Artifact Registry ($REPO_NAME)..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" >/dev/null 2>&1; then
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Repositório para IdiomasBR"
fi

BACKEND_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/backend:$IMAGE_TAG"
FRONTEND_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/frontend:$IMAGE_TAG"

# 3. Build e Push do Backend
echo "🏗️ Construindo imagem do Backend: $BACKEND_IMAGE"
gcloud builds submit ./backend \
    --config ./backend/cloudbuild.yaml \
    --substitutions=_REGION="$REGION",_REPO_NAME="$REPO_NAME",_TAG="$IMAGE_TAG" \
    --timeout=1200s

# 4. Deploy do Backend no Cloud Run com conexão ao Cloud SQL
echo "🚀 Fazendo deploy do Backend ($BACKEND_SERVICE)..."

if [[ "$USE_SECRET_MANAGER" == "true" ]]; then
    # Descobrir o service account atual do backend (para conceder acesso aos secrets)
    BACKEND_SA="$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --format 'value(spec.template.spec.serviceAccountName)')"
    if [[ -z "$BACKEND_SA" ]]; then
        # Cloud Run pode omitir explicitamente; nesse caso usa o default compute SA.
        PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')"
        BACKEND_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
    fi

    # Garantir que os secrets existam; se não existirem, opcionalmente fazer bootstrap
    NEED_BOOTSTRAP=false
    if ! gcloud secrets describe "$DATABASE_URL_SECRET_NAME" >/dev/null 2>&1; then
        NEED_BOOTSTRAP=true
    fi
    if ! gcloud secrets describe "$SECRET_KEY_SECRET_NAME" >/dev/null 2>&1; then
        NEED_BOOTSTRAP=true
    fi

    if [[ "$NEED_BOOTSTRAP" == "true" && "$BOOTSTRAP_SECRETS_FROM_CURRENT" == "true" ]]; then
        echo "🔐 Bootstrap: criando secrets no Secret Manager a partir do Cloud Run atual (backend)."

        # Usa JSON + Python para extrair valores com segurança (evita problemas com filtros do --format)
        CURRENT_DATABASE_URL="$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --format=json | \
            python -c "import sys, json; d=json.load(sys.stdin); env=(d.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[{}])[0].get('env',[]) or []); print(next((e.get('value','') for e in env if e.get('name')=='DATABASE_URL'),''))")"
        CURRENT_SECRET_KEY="$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --format=json | \
            python -c "import sys, json; d=json.load(sys.stdin); env=(d.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[{}])[0].get('env',[]) or []); print(next((e.get('value','') for e in env if e.get('name')=='SECRET_KEY'),''))")"

        if [[ -z "$CURRENT_DATABASE_URL" || -z "$CURRENT_SECRET_KEY" ]]; then
            echo "Erro: não consegui ler DATABASE_URL/SECRET_KEY do Cloud Run para bootstrap."
            echo "Dica: crie os secrets manualmente e rode novamente."
            exit 1
        fi

        if ! gcloud secrets describe "$DATABASE_URL_SECRET_NAME" >/dev/null 2>&1; then
            printf %s "$CURRENT_DATABASE_URL" | gcloud secrets create "$DATABASE_URL_SECRET_NAME" --data-file=- >/dev/null
        fi
        if ! gcloud secrets describe "$SECRET_KEY_SECRET_NAME" >/dev/null 2>&1; then
            printf %s "$CURRENT_SECRET_KEY" | gcloud secrets create "$SECRET_KEY_SECRET_NAME" --data-file=- >/dev/null
        fi
    fi

    # Validar existência dos secrets
    if ! gcloud secrets describe "$DATABASE_URL_SECRET_NAME" >/dev/null 2>&1; then
        echo "Erro: secret não encontrado: $DATABASE_URL_SECRET_NAME"
        echo "Crie no Secret Manager (ou rode com BOOTSTRAP_SECRETS_FROM_CURRENT=true)."
        exit 1
    fi
    if ! gcloud secrets describe "$SECRET_KEY_SECRET_NAME" >/dev/null 2>&1; then
        echo "Erro: secret não encontrado: $SECRET_KEY_SECRET_NAME"
        echo "Crie no Secret Manager (ou rode com BOOTSTRAP_SECRETS_FROM_CURRENT=true)."
        exit 1
    fi

    # Garantir que o service account do Cloud Run tem acesso aos secrets
    gcloud secrets add-iam-policy-binding "$DATABASE_URL_SECRET_NAME" \
        --member="serviceAccount:$BACKEND_SA" \
        --role="roles/secretmanager.secretAccessor" >/dev/null
    gcloud secrets add-iam-policy-binding "$SECRET_KEY_SECRET_NAME" \
        --member="serviceAccount:$BACKEND_SA" \
        --role="roles/secretmanager.secretAccessor" >/dev/null

    # ===== AI secrets (OpenAI/DeepSeek) =====
    # Estratégia:
    # 1) Se o secret existe: usa.
    # 2) Se não existe e BOOTSTRAP_AI_SECRETS_FROM_CURRENT=true: copia do Cloud Run atual.
    # 3) Se não existe e CREATE_AI_SECRETS_FROM_ENV=true: cria a partir de OPENAI_API_KEY/DEEPSEEK_API_KEY do seu terminal.

    if ! gcloud secrets describe "$OPENAI_API_KEY_SECRET_NAME" >/dev/null 2>&1; then
        if [[ "$BOOTSTRAP_AI_SECRETS_FROM_CURRENT" == "true" ]]; then
            CURRENT_OPENAI_API_KEY="$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --format=json | \
                python -c "import sys, json; d=json.load(sys.stdin); env=(d.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[{}])[0].get('env',[]) or []); print(next((e.get('value','') for e in env if e.get('name')=='OPENAI_API_KEY'),''))")"
            if [[ -n "$CURRENT_OPENAI_API_KEY" ]]; then
                printf %s "$CURRENT_OPENAI_API_KEY" | gcloud secrets create "$OPENAI_API_KEY_SECRET_NAME" --data-file=- >/dev/null
            fi
        fi

        if [[ "$CREATE_AI_SECRETS_FROM_ENV" == "true" && -n "${OPENAI_API_KEY:-}" ]]; then
            printf %s "$OPENAI_API_KEY" | gcloud secrets create "$OPENAI_API_KEY_SECRET_NAME" --data-file=- >/dev/null
        fi
    fi

    if ! gcloud secrets describe "$DEEPSEEK_API_KEY_SECRET_NAME" >/dev/null 2>&1; then
        if [[ "$BOOTSTRAP_AI_SECRETS_FROM_CURRENT" == "true" ]]; then
            CURRENT_DEEPSEEK_API_KEY="$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --format=json | \
                python -c "import sys, json; d=json.load(sys.stdin); env=(d.get('spec',{}).get('template',{}).get('spec',{}).get('containers',[{}])[0].get('env',[]) or []); print(next((e.get('value','') for e in env if e.get('name')=='DEEPSEEK_API_KEY'),''))")"
            if [[ -n "$CURRENT_DEEPSEEK_API_KEY" ]]; then
                printf %s "$CURRENT_DEEPSEEK_API_KEY" | gcloud secrets create "$DEEPSEEK_API_KEY_SECRET_NAME" --data-file=- >/dev/null
            fi
        fi

        if [[ "$CREATE_AI_SECRETS_FROM_ENV" == "true" && -n "${DEEPSEEK_API_KEY:-}" ]]; then
            printf %s "$DEEPSEEK_API_KEY" | gcloud secrets create "$DEEPSEEK_API_KEY_SECRET_NAME" --data-file=- >/dev/null
        fi
    fi

    # AI secrets (opcional): se existirem, injeta no Cloud Run
    AI_SECRETS_CSV=""
    if gcloud secrets describe "$OPENAI_API_KEY_SECRET_NAME" >/dev/null 2>&1; then
        gcloud secrets add-iam-policy-binding "$OPENAI_API_KEY_SECRET_NAME" \
            --member="serviceAccount:$BACKEND_SA" \
            --role="roles/secretmanager.secretAccessor" >/dev/null
        AI_SECRETS_CSV=",OPENAI_API_KEY=$OPENAI_API_KEY_SECRET_NAME:latest"
    else
        echo "💡 Secret de AI não encontrado (OK): $OPENAI_API_KEY_SECRET_NAME"
    fi

    if gcloud secrets describe "$DEEPSEEK_API_KEY_SECRET_NAME" >/dev/null 2>&1; then
        gcloud secrets add-iam-policy-binding "$DEEPSEEK_API_KEY_SECRET_NAME" \
            --member="serviceAccount:$BACKEND_SA" \
            --role="roles/secretmanager.secretAccessor" >/dev/null
        AI_SECRETS_CSV="$AI_SECRETS_CSV,DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY_SECRET_NAME:latest"
    else
        echo "💡 Secret de AI não encontrado (OK): $DEEPSEEK_API_KEY_SECRET_NAME"
    fi

    if [[ "$REQUIRE_AI_SECRETS" == "true" ]]; then
        if [[ "$AI_SECRETS_CSV" != *"OPENAI_API_KEY="* ]]; then
            echo "Erro: OpenAI não configurada. Crie o secret $OPENAI_API_KEY_SECRET_NAME (ou rode com CREATE_AI_SECRETS_FROM_ENV=true e OPENAI_API_KEY setado)."; exit 1
        fi
        if [[ "$AI_SECRETS_CSV" != *"DEEPSEEK_API_KEY="* ]]; then
            echo "Erro: DeepSeek não configurada. Crie o secret $DEEPSEEK_API_KEY_SECRET_NAME (ou rode com CREATE_AI_SECRETS_FROM_ENV=true e DEEPSEEK_API_KEY setado)."; exit 1
        fi
    fi

    # Espera que você já tenha criado os secrets no Secret Manager.
    # Exemplo:
    #   echo -n "postgresql://USER:SENHA@/DB?host=/cloudsql/CONNECTION" | gcloud secrets create idiomasbr-database-url --data-file=-
    #   echo -n "minha-secret-key" | gcloud secrets create idiomasbr-secret-key --data-file=-
    OLLAMA_ENV_CSV=""
    if [[ -n "$OLLAMA_URL_ENV" ]]; then
        OLLAMA_ENV_CSV=",OLLAMA_URL=$OLLAMA_URL_ENV"
    fi

    gcloud run deploy "$BACKEND_SERVICE" \
        --image "$BACKEND_IMAGE" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --add-cloudsql-instances "$CLOUDSQL_CONNECTION_NAME" \
        --set-secrets "DATABASE_URL=$DATABASE_URL_SECRET_NAME:latest,SECRET_KEY=$SECRET_KEY_SECRET_NAME:latest$AI_SECRETS_CSV" \
        --set-env-vars "ENVIRONMENT=production,ALGORITHM=HS256,ACCESS_TOKEN_EXPIRE_MINUTES=10080,DEBUG=false,AUTH_REQUIRE_EMAIL_VERIFICATION=true,FRONTEND_BASE_URL=$FRONTEND_BASE_URL_ENV,USE_OLLAMA_FALLBACK=$USE_OLLAMA_FALLBACK_ENV$OLLAMA_ENV_CSV"
else
    echo "⚠️ USE_SECRET_MANAGER=false: você precisa definir DATABASE_URL e SECRET_KEY via --set-env-vars manualmente."
    echo "   Recomendo fortemente usar Secret Manager para produção."
    exit 1
fi

# Capturar URL do Backend
BACKEND_URL="$(gcloud run services describe "$BACKEND_SERVICE" --platform managed --region "$REGION" --format 'value(status.url)')"
echo "✅ Backend disponível em: $BACKEND_URL"

# 5. Build e Push do Frontend (injeta NEXT_PUBLIC_API_URL no build)
echo "🏗️ Construindo imagem do Frontend: $FRONTEND_IMAGE"
gcloud builds submit ./frontend \
    --config ./frontend/cloudbuild.yaml \
    --substitutions=_NEXT_PUBLIC_API_URL="$BACKEND_URL",_REGION="$REGION",_REPO_NAME="$REPO_NAME",_TAG="$IMAGE_TAG" \
    --timeout=1200s

# 6. Deploy do Frontend no Cloud Run
echo "🚀 Fazendo deploy do Frontend ($FRONTEND_SERVICE)..."
gcloud run deploy "$FRONTEND_SERVICE" \
    --image "$FRONTEND_IMAGE" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "NEXT_PUBLIC_API_URL=$BACKEND_URL"

# Capturar URL do Frontend
FRONTEND_URL="$(gcloud run services describe "$FRONTEND_SERVICE" --platform managed --region "$REGION" --format 'value(status.url)')"

# 7. Aplicar migração (opcional)
if [[ "$APPLY_MIGRATIONS" == "true" ]]; then
    if [[ ! -f "$MIGRATION_FILE" ]]; then
        echo "Erro: arquivo de migração não encontrado: $MIGRATION_FILE"; exit 1
    fi

    echo "🗄️ Aplicando migração no Cloud SQL ($DB_INSTANCE_NAME)..."

    if command -v psql >/dev/null 2>&1; then
        if [[ -z "$DB_USER" ]]; then
            echo "Erro: psql disponível localmente, mas DB_USER não foi definido."; exit 1
        fi
        # Dica: rode isso no Cloud Shell para evitar problemas de rede.
        gcloud sql connect "$DB_INSTANCE_NAME" --user="$DB_USER" --database="$DB_NAME" < "$MIGRATION_FILE"
        echo "✅ Migração aplicada: $MIGRATION_FILE"
    else
        echo "ℹ️ psql não encontrado localmente; aplicando via Cloud Build (cloudbuild.migrate.yaml)"

        if [[ "$USE_SECRET_MANAGER" != "true" ]]; then
            echo "Erro: para rodar migração via Cloud Build sem psql, USE_SECRET_MANAGER precisa ser true."; exit 1
        fi

        if ! gcloud secrets describe "$DATABASE_URL_SECRET_NAME" >/dev/null 2>&1; then
            echo "Erro: secret não encontrado: $DATABASE_URL_SECRET_NAME"; exit 1
        fi

        PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')"
        CLOUDBUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"
        gcloud secrets add-iam-policy-binding "$DATABASE_URL_SECRET_NAME" \
            --member="serviceAccount:$CLOUDBUILD_SA" \
            --role="roles/secretmanager.secretAccessor" >/dev/null

        if [[ ! -f "cloudbuild.migrate.yaml" ]]; then
            echo "Erro: arquivo cloudbuild.migrate.yaml não encontrado na raiz do projeto."; exit 1
        fi

        gcloud builds submit . \
            --config cloudbuild.migrate.yaml \
            --substitutions=_INSTANCE_CONNECTION_NAME="$CLOUDSQL_CONNECTION_NAME",_DATABASE_URL_SECRET_NAME="$DATABASE_URL_SECRET_NAME",_MIGRATION_FILE="$MIGRATION_FILE" \
            --timeout=1200s

        echo "✅ Migração aplicada via Cloud Build: $MIGRATION_FILE"
    fi
fi

# 8. Seed de palavras (opcional)
if [[ "$SEED_WORDS" == "true" ]]; then
    echo "🌱 Fazendo seed de palavras no Cloud SQL ($DB_INSTANCE_NAME)..."

    if [[ "$USE_SECRET_MANAGER" != "true" ]]; then
        echo "Erro: para rodar seed via Cloud Build, USE_SECRET_MANAGER precisa ser true."; exit 1
    fi

    if ! gcloud secrets describe "$DATABASE_URL_SECRET_NAME" >/dev/null 2>&1; then
        echo "Erro: secret não encontrado: $DATABASE_URL_SECRET_NAME"; exit 1
    fi

    PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')"
    CLOUDBUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"
    gcloud secrets add-iam-policy-binding "$DATABASE_URL_SECRET_NAME" \
        --member="serviceAccount:$CLOUDBUILD_SA" \
        --role="roles/secretmanager.secretAccessor" >/dev/null

    if [[ ! -f "cloudbuild.seed_words.yaml" ]]; then
        echo "Erro: arquivo cloudbuild.seed_words.yaml não encontrado na raiz do projeto."; exit 1
    fi

    gcloud builds submit . \
        --config cloudbuild.seed_words.yaml \
        --substitutions=_INSTANCE_CONNECTION_NAME="$CLOUDSQL_CONNECTION_NAME",_DATABASE_URL_SECRET_NAME="$DATABASE_URL_SECRET_NAME",_WORD_FILES="$WORD_FILES" \
        --timeout=1200s

    echo "✅ Seed de palavras concluído."
fi

echo "🎉 Deploy concluído com sucesso!"
echo "🌍 Frontend: $FRONTEND_URL"
echo "⚙️ Backend: $BACKEND_URL"
