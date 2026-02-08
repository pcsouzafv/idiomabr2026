#!/usr/bin/env bash
# Script para sincronizar banco de dados local com produção (GCP Cloud SQL)
#
# IMPORTANTE: Este script oferece várias opções de sincronização.
# Escolha a opção adequada para sua necessidade.

set -euo pipefail

# Configurações
PROJECT_ID="${PROJECT_ID:-idiomasbr}"
REGION="${REGION:-us-central1}"
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-idiomasbr-db}"
DB_NAME="${DB_NAME:-idiomasbr}"
DB_USER="${DB_USER:-postgres}"

# Arquivos
DUMP_FILE="${DUMP_FILE:-dump_final.sql}"
MIGRATIONS_DIR="backend/migrations"
DATA_DIR="backend/data"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SINCRONIZAÇÃO DE BANCO DE DADOS - GCP Cloud SQL     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Função de ajuda
show_help() {
    cat << EOF
Uso: $0 [OPÇÃO]

Opções de sincronização:

  1) migrations    - Aplica apenas migrações SQL (ALTER TABLE, etc)
                     Seguro: Não sobrescreve dados existentes

  2) seed-words    - Importa palavras dos CSVs (INSERT/UPSERT)
                     Seguro: Adiciona dados sem remover existentes

  3) full-restore  - Restaura dump completo (DROP + CREATE + INSERT)
                     ATENÇÃO: Remove TODOS os dados e recria

  4) export-prod   - Exporta banco de produção para arquivo local
                     Útil para backup ou análise

  5) compare       - Compara esquemas local vs produção
                     Mostra diferenças sem fazer alterações

Variáveis de ambiente (opcional):
  PROJECT_ID         - ID do projeto GCP (padrão: idiomasbr)
  REGION             - Região do Cloud SQL (padrão: us-central1)
  DB_INSTANCE_NAME   - Nome da instância (padrão: idiomasbr-db)
  DB_NAME            - Nome do database (padrão: idiomasbr)
  DB_USER            - Usuário do banco (padrão: postgres)

Exemplos:
  # Aplicar migrações
  bash sync_database.sh migrations

  # Importar palavras
  bash sync_database.sh seed-words

  # Restauração completa (CUIDADO!)
  bash sync_database.sh full-restore

  # Exportar banco de produção
  bash sync_database.sh export-prod

  # Comparar esquemas
  bash sync_database.sh compare
EOF
}

# Validar gcloud
check_gcloud() {
    if ! command -v gcloud >/dev/null 2>&1; then
        echo -e "${RED}❌ Erro: gcloud CLI não encontrado${NC}"
        echo "Instale: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    # Validar projeto configurado
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
    if [[ "$CURRENT_PROJECT" != "$PROJECT_ID" ]]; then
        echo -e "${YELLOW}⚠️  Configurando projeto: $PROJECT_ID${NC}"
        gcloud config set project "$PROJECT_ID"
    fi

    echo -e "${GREEN}✅ gcloud configurado (projeto: $PROJECT_ID)${NC}"
}

# Opção 1: Aplicar Migrações
apply_migrations() {
    echo -e "${BLUE}📝 Aplicando migrações SQL...${NC}"

    if [[ ! -d "$MIGRATIONS_DIR" ]]; then
        echo -e "${RED}❌ Diretório de migrações não encontrado: $MIGRATIONS_DIR${NC}"
        exit 1
    fi

    MIGRATION_FILES=$(find "$MIGRATIONS_DIR" -name "*.sql" | sort)

    if [[ -z "$MIGRATION_FILES" ]]; then
        echo -e "${YELLOW}⚠️  Nenhuma migração encontrada${NC}"
        return
    fi

    for migration in $MIGRATION_FILES; do
        MIGRATION_NAME=$(basename "$migration")
        echo -e "${BLUE}  → Aplicando: $MIGRATION_NAME${NC}"

        # Usar cloudbuild.migrate.yaml
        gcloud builds submit . \
            --config cloudbuild.migrate.yaml \
            --substitutions=_INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME",_DATABASE_URL_SECRET_NAME="idiomasbr-database-url",_MIGRATION_FILE="$migration" \
            --timeout=600s

        echo -e "${GREEN}  ✅ $MIGRATION_NAME aplicada${NC}"
    done

    echo -e "${GREEN}✅ Todas as migrações aplicadas com sucesso!${NC}"
}

# Opção 2: Seed de Palavras
seed_words() {
    echo -e "${BLUE}🌱 Importando palavras dos CSVs...${NC}"

    # Verificar se existem CSVs
    if [[ ! -d "$DATA_DIR" ]]; then
        echo -e "${RED}❌ Diretório de dados não encontrado: $DATA_DIR${NC}"
        exit 1
    fi

    WORD_FILES=$(find "$DATA_DIR" -name "seed_words*.csv" | tr '\n' ',' | sed 's/,$//')

    if [[ -z "$WORD_FILES" ]]; then
        echo -e "${YELLOW}⚠️  Nenhum arquivo de palavras encontrado${NC}"
        return
    fi

    echo -e "${BLUE}  Arquivos encontrados:${NC}"
    echo "$WORD_FILES" | tr ',' '\n' | while read -r file; do
        echo -e "${BLUE}    - $(basename "$file")${NC}"
    done

    # Usar cloudbuild.seed_words.yaml
    echo -e "${BLUE}  → Executando import via Cloud Build...${NC}"
    gcloud builds submit . \
        --config cloudbuild.seed_words.yaml \
        --substitutions=_INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:$DB_INSTANCE_NAME",_DATABASE_URL_SECRET_NAME="idiomasbr-database-url",_WORD_FILES="$WORD_FILES" \
        --timeout=1200s

    echo -e "${GREEN}✅ Palavras importadas com sucesso!${NC}"
}

# Opção 3: Restauração Completa
full_restore() {
    echo -e "${RED}⚠️  ATENÇÃO: RESTAURAÇÃO COMPLETA${NC}"
    echo -e "${RED}   Isso vai APAGAR todos os dados e restaurar do dump!${NC}"
    echo ""
    read -p "Tem certeza? Digite 'SIM' em maiúsculas para confirmar: " confirm

    if [[ "$confirm" != "SIM" ]]; then
        echo -e "${YELLOW}Operação cancelada${NC}"
        exit 0
    fi

    if [[ ! -f "$DUMP_FILE" ]]; then
        echo -e "${RED}❌ Arquivo de dump não encontrado: $DUMP_FILE${NC}"
        exit 1
    fi

    echo -e "${BLUE}📤 Fazendo upload do dump para Cloud Storage...${NC}"

    # Criar bucket temporário (se não existir)
    BUCKET_NAME="gs://${PROJECT_ID}-db-imports"
    if ! gsutil ls "$BUCKET_NAME" >/dev/null 2>&1; then
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "$BUCKET_NAME"
    fi

    # Upload do dump
    gsutil cp "$DUMP_FILE" "$BUCKET_NAME/$(basename $DUMP_FILE)"

    echo -e "${BLUE}🔄 Restaurando banco de dados...${NC}"

    # Import via gcloud
    gcloud sql import sql "$DB_INSTANCE_NAME" \
        "$BUCKET_NAME/$(basename $DUMP_FILE)" \
        --database="$DB_NAME" \
        --quiet

    echo -e "${GREEN}✅ Restauração completa concluída!${NC}"
}

# Opção 4: Exportar Produção
export_prod() {
    EXPORT_FILE="dump_prod_$(date +%Y%m%d_%H%M%S).sql"

    echo -e "${BLUE}📥 Exportando banco de produção...${NC}"
    echo -e "${BLUE}   Arquivo: $EXPORT_FILE${NC}"

    # Criar bucket temporário (se não existir)
    BUCKET_NAME="gs://${PROJECT_ID}-db-exports"
    if ! gsutil ls "$BUCKET_NAME" >/dev/null 2>&1; then
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "$BUCKET_NAME"
    fi

    # Export via gcloud
    gcloud sql export sql "$DB_INSTANCE_NAME" \
        "$BUCKET_NAME/$EXPORT_FILE" \
        --database="$DB_NAME"

    # Download local
    gsutil cp "$BUCKET_NAME/$EXPORT_FILE" "./$EXPORT_FILE"

    echo -e "${GREEN}✅ Exportação concluída: $EXPORT_FILE${NC}"
}

# Opção 5: Comparar Esquemas
compare_schemas() {
    echo -e "${BLUE}🔍 Comparando esquemas (local vs produção)...${NC}"
    echo -e "${YELLOW}⚠️  Funcionalidade ainda não implementada${NC}"
    echo ""
    echo "Para comparar manualmente:"
    echo "1. Export do schema de produção:"
    echo "   gcloud sql export sql $DB_INSTANCE_NAME gs://bucket/schema.sql --database=$DB_NAME"
    echo ""
    echo "2. Export do schema local:"
    echo "   docker-compose exec postgres pg_dump -U idiomasbr -s idiomasbr > schema_local.sql"
    echo ""
    echo "3. Compare os arquivos com diff ou ferramenta visual"
}

# Main
main() {
    if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_help
        exit 0
    fi

    check_gcloud

    case "$1" in
        migrations)
            apply_migrations
            ;;
        seed-words)
            seed_words
            ;;
        full-restore)
            full_restore
            ;;
        export-prod)
            export_prod
            ;;
        compare)
            compare_schemas
            ;;
        *)
            echo -e "${RED}❌ Opção inválida: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO          ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
}

main "$@"
