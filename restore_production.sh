#!/usr/bin/env bash
# Script para restaurar banco de produção com dump_final.sql
# Usa gcloud SQL import direto

set -euo pipefail

# Configurações
PROJECT_ID="${PROJECT_ID:-idiomasbr}"
REGION="${REGION:-us-central1}"
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-idiomasbr-db}"
DB_NAME="${DB_NAME:-idiomasbr}"
DUMP_FILE="dump_final.sql"
BUCKET_NAME="gs://${PROJECT_ID}-db-imports"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║        RESTAURAÇÃO COMPLETA - BANCO DE PRODUÇÃO        ║${NC}"
echo -e "${RED}║                                                        ║${NC}"
echo -e "${RED}║  ⚠️  ISSO VAI APAGAR TODOS OS DADOS EXISTENTES! ⚠️     ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Validações
if [[ ! -f "$DUMP_FILE" ]]; then
    echo -e "${RED}❌ Arquivo de dump não encontrado: $DUMP_FILE${NC}"
    exit 1
fi

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo -e "${BLUE}📄 Arquivo: $DUMP_FILE ($DUMP_SIZE)${NC}"
echo -e "${BLUE}🎯 Destino: $DB_INSTANCE_NAME/$DB_NAME${NC}"
echo ""

# Confirmação
echo -e "${YELLOW}Você tem certeza absoluta?${NC}"
read -p "Digite 'RESTAURAR' em maiúsculas para confirmar: " confirm

if [[ "$confirm" != "RESTAURAR" ]]; then
    echo -e "${YELLOW}Operação cancelada${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}🚀 Iniciando restauração...${NC}"

# 1. Criar bucket se não existir
echo -e "${BLUE}📦 Verificando bucket de imports...${NC}"
if ! gsutil ls "$BUCKET_NAME" >/dev/null 2>&1; then
    echo -e "${BLUE}   Criando bucket...${NC}"
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "$BUCKET_NAME"
fi
echo -e "${GREEN}   ✅ Bucket pronto${NC}"

# 2. Upload do dump
echo -e "${BLUE}📤 Fazendo upload do dump...${NC}"
gsutil -o "GSUtil:parallel_process_count=1" cp "$DUMP_FILE" "$BUCKET_NAME/"
echo -e "${GREEN}   ✅ Upload concluído${NC}"

# 3. Restaurar banco
echo -e "${BLUE}🔄 Restaurando banco de dados...${NC}"
echo -e "${YELLOW}   (Isso pode levar alguns minutos)${NC}"

gcloud sql import sql "$DB_INSTANCE_NAME" \
    "$BUCKET_NAME/$(basename $DUMP_FILE)" \
    --database="$DB_NAME" \
    --quiet

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         RESTAURAÇÃO CONCLUÍDA COM SUCESSO!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Banco de produção agora está igual ao de homologação${NC}"
echo ""
echo "Próximos passos:"
echo "1. Testar aplicação: https://idiomasbr-frontend-7rpgvb7uga-uc.a.run.app"
echo "2. Verificar dados no banco"
echo "3. Reiniciar backend se necessário"
