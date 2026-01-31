#!/bin/bash
#######################################################
# Enriquecimento Contínuo - IdiomaBR
# Processa em lotes até completar todas as palavras
#######################################################

set -e

echo ""
echo "========================================================"
echo "  ENRIQUECIMENTO CONTÍNUO - IdiomaBR"
echo "========================================================"
echo ""
echo "Este script processa palavras em lotes até completar"
echo "todas as palavras incompletas no banco de dados."
echo ""

# Criar diretório de logs
mkdir -p logs

# Timestamp para logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="logs/enrich_continuous_${TIMESTAMP}.log"

echo "[$(date)] Iniciando enriquecimento contínuo" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# Contadores
LOTE=1
TOTAL_PROCESSADAS=0

# Função para verificar palavras restantes
check_remaining() {
    docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze 2>/dev/null | \
        grep "Precisam enriquecimento:" | \
        awk '{print $3}' | \
        tr -d ','
}

# Loop principal
while true; do
    # Verificar quantas palavras restam
    REMAINING=$(check_remaining)
    
    if [ -z "$REMAINING" ] || [ "$REMAINING" -eq 0 ]; then
        echo ""
        echo "========================================================"
        echo "  TODAS AS PALAVRAS FORAM PROCESSADAS!"
        echo "========================================================"
        break
    fi
    
    echo ""
    echo "========================================================"
    echo "  LOTE $LOTE - Restam $REMAINING palavras"
    echo "========================================================"
    echo ""
    echo "[$(date)] Lote $LOTE - $REMAINING palavras restantes" | tee -a "$LOGFILE"
    
    # Calcular tamanho do lote (máximo 1000)
    BATCH_SIZE=$((REMAINING < 1000 ? REMAINING : 1000))
    
    # Executar enriquecimento
    docker exec idiomasbr-backend python scripts/enrich_words_with_ai.py \
        --batch 200 \
        --limit $BATCH_SIZE \
        --fields definition_pt,example_en,example_pt \
        --delay 0.3 2>&1 | tee -a "$LOGFILE"
    
    if [ $? -eq 0 ]; then
        echo "[OK] Lote $LOTE concluído com sucesso!"
        echo "[$(date)] Lote $LOTE concluído" >> "$LOGFILE"
    else
        echo "[ERRO] Falha no lote $LOTE"
        echo "[$(date)] ERRO no lote $LOTE" >> "$LOGFILE"
        break
    fi
    
    # Incrementar contadores
    ((LOTE++))
    ((TOTAL_PROCESSADAS += BATCH_SIZE))
    
    echo ""
    echo "Progresso: ~$TOTAL_PROCESSADAS palavras processadas"
    echo ""
    
    # Aguardar antes do próximo lote
    echo "Aguardando 10 segundos..."
    sleep 10
done

# Relatório final
echo ""
echo "========================================================"
echo "  PROCESSAMENTO CONCLUÍDO!"
echo "========================================================"
echo ""
echo "[$(date)] Processamento finalizado" >> "$LOGFILE"

# Análise final
echo "Gerando relatório final..."
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze | tee -a "$LOGFILE"

echo ""
echo "Gerando relatório HTML..."
docker exec idiomasbr-backend python scripts/generate_words_report.py
docker cp idiomasbr-backend://app/words_report.html ./words_report_${TIMESTAMP}.html

echo ""
echo "========================================================"
echo "  RESUMO FINAL"
echo "========================================================"
echo ""
echo "Total de lotes processados: $LOTE"
echo "Total de palavras processadas: ~$TOTAL_PROCESSADAS"
echo "Log salvo em: $LOGFILE"
echo "Relatório HTML: words_report_${TIMESTAMP}.html"
echo ""
echo "[$(date)] Total: $LOTE lotes, ~$TOTAL_PROCESSADAS palavras" >> "$LOGFILE"

echo ""
echo "Processamento completo!"
echo ""
