# Deploy/Atualização na GCP (Cloud Run + Cloud SQL)

Este projeto já possui o script [deploy_gcp.sh](deploy_gcp.sh) para **build + deploy** do backend (FastAPI) e do frontend (Next.js) no **Cloud Run**, usando imagens no **Artifact Registry** e banco no **Cloud SQL (PostgreSQL)**.

## Pré-requisitos

- `gcloud` instalado e autenticado (`gcloud auth login`)
- Projeto GCP já criado
- APIs habilitadas (o script habilita automaticamente)

## 1) One-time setup (Cloud SQL)

1. Crie uma instância Postgres no Cloud SQL (ex: `idiomasbr-db`) na mesma região do Cloud Run.
2. Crie o database (ex: `idiomasbr`) e um usuário.
3. Garanta que o Cloud Run consiga acessar o Cloud SQL:
   - O script usa `--add-cloudsql-instances` (Cloud SQL connector)
   - O *service account* do Cloud Run precisa de permissão `Cloud SQL Client`.

## 2) One-time setup (Secret Manager)

O script foi ajustado para **não hardcodar segredos**.

Crie 2 secrets no Secret Manager (nomes padrão):

- `idiomasbr-database-url`: contém a `DATABASE_URL`
- `idiomasbr-secret-key`: contém a `SECRET_KEY`

Exemplo (rode no Cloud Shell ou no seu terminal):

```bash
# Ajuste PROJECT_ID/REGION/DB_INSTANCE_NAME/DB_USER/DB_PASS conforme seu ambiente
PROJECT_ID="idiomasbr"
REGION="us-central1"
DB_INSTANCE_NAME="idiomasbr-db"
DB_NAME="idiomasbr"
DB_USER="SEU_USUARIO"
DB_PASS="SUA_SENHA"

CLOUDSQL_CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME"

DATABASE_URL_VALUE="postgresql://$DB_USER:$DB_PASS@/$DB_NAME?host=/cloudsql/$CLOUDSQL_CONNECTION_NAME"

printf %s "$DATABASE_URL_VALUE" | gcloud secrets create idiomasbr-database-url --data-file=-
printf %s "SUA_SECRET_KEY_FORTE" | gcloud secrets create idiomasbr-secret-key --data-file=-
```

Depois, dê permissão de leitura dos secrets para o service account do Cloud Run (o padrão do projeto, ou um dedicado):

- Role: `Secret Manager Secret Accessor`

### 2.1) Secrets de IA (OpenAI / DeepSeek)

Localmente (Docker Compose), suas chaves podem estar vindo de variáveis do host e/ou de um arquivo `.env` montado por volume.
No **Cloud Run**, não existe volume montando seu repositório, e além disso o backend tem um `.dockerignore` que **exclui `.env` da imagem**.

Por isso, para a IA funcionar em produção você deve injetar as chaves por **Secret Manager**.

Secrets opcionais (nomes padrão):

- `idiomasbr-openai-api-key` → `OPENAI_API_KEY`
- `idiomasbr-deepseek-api-key` → `DEEPSEEK_API_KEY`

O script [deploy_gcp.sh](deploy_gcp.sh) injeta automaticamente esses secrets **se eles existirem**.

Se você quiser fazer exatamente como no Docker (pegar as chaves do seu ambiente local e subir para a GCP), você pode rodar o deploy assim:

```bash
export OPENAI_API_KEY="SUA_CHAVE_OPENAI"
export DEEPSEEK_API_KEY="SUA_CHAVE_DEEPSEEK"

export CREATE_AI_SECRETS_FROM_ENV=true
export REQUIRE_AI_SECRETS=true

bash ./deploy_gcp.sh
```

Isso cria (se não existirem) e injeta no Cloud Run:
- `idiomasbr-openai-api-key`
- `idiomasbr-deepseek-api-key`

Ordem de uso na aplicação (fallback): **OpenAI → DeepSeek → Ollama**.

### 2.2) Sobre Ollama no Cloud Run

No Docker local você tem o serviço `ollama` no `docker-compose.yml`.
No Cloud Run isso não existe automaticamente.

Para usar Ollama em produção, você precisa ter um endpoint acessível (ex.: outro serviço Cloud Run/VM) e passar:

- `USE_OLLAMA_FALLBACK_ENV=true`
- `OLLAMA_URL_ENV=https://SUA_URL_DO_OLLAMA`

## 3) Deploy / Atualização

Rode o script na raiz do repositório:

```bash
# Exemplo (ajuste os valores)
export PROJECT_ID="idiomasbr"
export REGION="us-central1"
export DB_INSTANCE_NAME="idiomasbr-db"

# Opcional: usar tag específica (recomendado)
export IMAGE_TAG="v2025-12-16"

bash ./deploy_gcp.sh
```

O script vai:

- criar/verificar o Artifact Registry
- build/push do backend
- deploy do backend no Cloud Run (com Cloud SQL)
- descobrir a URL do backend
- build/push do frontend já com `NEXT_PUBLIC_API_URL` apontando para o backend
- deploy do frontend

Se você quiser habilitar o fallback para Ollama (somente se tiver um Ollama acessível):

```bash
export USE_OLLAMA_FALLBACK_ENV=true
export OLLAMA_URL_ENV="https://SUA_URL_DO_OLLAMA"

bash ./deploy_gcp.sh
```


## 4) Aplicar migração SQL (opcional, recomendado quando houver mudanças de schema)

Existe uma migração SQL em [backend/migrations/add_word_details.sql](backend/migrations/add_word_details.sql).

Você pode pedir para o script aplicar após o deploy:

```bash
export APPLY_MIGRATIONS=true
export DB_USER="SEU_USUARIO"
export DB_NAME="idiomasbr"  # opcional (default)

bash ./deploy_gcp.sh
```

Obs.: essa etapa usa `gcloud sql connect ... < arquivo.sql`. Em alguns ambientes é mais simples rodar no **Cloud Shell**.

## 5) Seed de palavras no Cloud SQL (opcional, recomendado para preencher conteúdo)

Ter o schema/migrações aplicados não garante que o banco tenha conteúdo (palavras/frases).
Para popular o Cloud SQL com os CSVs do repositório, rode:

```bash
export SEED_WORDS=true
# Você pode customizar a lista de CSVs (separados por vírgula)
export WORD_FILES="backend/data/seed_words_core_unique.csv,backend/data/seed_words_extra_unique_v3.csv"

bash ./deploy_gcp.sh
```

Isso executa o Cloud Build [cloudbuild.seed_words.yaml](cloudbuild.seed_words.yaml) que importa os CSVs usando `backend/import_words.py`.

## Variáveis que você pode sobrescrever

- `PROJECT_ID`, `REGION`
- `REPO_NAME` (default: `idiomasbr-repo`)
- `BACKEND_SERVICE`, `FRONTEND_SERVICE`
- `DB_INSTANCE_NAME` ou `CLOUDSQL_CONNECTION_NAME`
- `IMAGE_TAG`
- `DATABASE_URL_SECRET_NAME`, `SECRET_KEY_SECRET_NAME`

## Dica de produção

- Rotacione qualquer credencial que já tenha sido committada (o script antigo tinha valores hardcoded).
- Use um service account dedicado por serviço (backend/frontend) e permissões mínimas.
