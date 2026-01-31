@echo off
REM =====================================================
REM  Enriquecimento Automatico Completo (Overnight)
REM  IdiomaBR - Processamento em Lotes com DeepSeek
REM =====================================================

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo   ENRIQUECIMENTO AUTOMATICO COMPLETO - IdiomaBR
echo ========================================================
echo.
echo Este script vai processar TODAS as palavras incompletas
echo em lotes de 1000 palavras, salvando o progresso a cada lote.
echo.
echo Estimativa: 
echo   - ~9000 palavras restantes
echo   - ~9 lotes de 1000 palavras
echo   - ~3-4 horas de processamento total
echo   - Usando DeepSeek (sua chave API)
echo.

set /p confirm="Confirma inicio do processamento automatico? (S/N): "
if /i not "%confirm%"=="S" (
    echo Operacao cancelada.
    pause
    exit /b 0
)

echo.
echo ========================================================
echo   INICIANDO PROCESSAMENTO EM LOTES
echo ========================================================
echo.

REM Criar diretorio para logs
if not exist "logs" mkdir logs

REM Data e hora para log
set "timestamp=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "timestamp=%timestamp: =0%"
set "logfile=logs\enrich_overnight_%timestamp%.log"

echo [%date% %time%] Iniciando enriquecimento automatico >> "%logfile%"
echo. >> "%logfile%"

REM Contador de lotes
set /a lote=1
set /a total_processadas=0
set /a total_atualizadas=0

:PROCESSAR_LOTE

echo.
echo ========================================================
echo   LOTE %lote% - Processando 1000 palavras
echo ========================================================
echo.
echo [%date% %time%] Iniciando lote %lote%...

REM Executar enriquecimento
docker exec idiomasbr-backend python scripts/enrich_words_with_ai.py --batch 200 --limit 1000 --fields definition_pt,example_en,example_pt --delay 0.3 >> "%logfile%" 2>&1

if errorlevel 1 (
    echo [ERRO] Falha no lote %lote%
    echo [%date% %time%] ERRO no lote %lote% >> "%logfile%"
    goto RELATORIO_FINAL
) else (
    echo [OK] Lote %lote% concluido com sucesso!
    echo [%date% %time%] Lote %lote% concluido >> "%logfile%"
)

REM Incrementar contador
set /a lote+=1
set /a total_processadas+=1000

echo.
echo Progresso: ~%total_processadas% palavras processadas
echo.
echo Aguardando 10 segundos antes do proximo lote...
timeout /t 10 /nobreak > nul

REM Verificar se ainda ha palavras para processar
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze > temp_status.txt 2>&1
findstr /C:"Precisam enriquecimento: 0" temp_status.txt > nul
if %errorlevel%==0 (
    echo.
    echo ========================================================
    echo   TODAS AS PALAVRAS FORAM PROCESSADAS!
    echo ========================================================
    del temp_status.txt
    goto RELATORIO_FINAL
)
del temp_status.txt

REM Continuar processando se ainda houver palavras
if %lote% LEQ 12 goto PROCESSAR_LOTE

:RELATORIO_FINAL

echo.
echo ========================================================
echo   PROCESSAMENTO CONCLUIDO!
echo ========================================================
echo.
echo [%date% %time%] Processamento finalizado >> "%logfile%"
echo. >> "%logfile%"

REM Analise final
echo Gerando relatorio final...
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze >> "%logfile%"

echo.
echo Gerando relatorio HTML...
docker exec idiomasbr-backend python scripts/generate_words_report.py
docker cp idiomasbr-backend://app/words_report.html ./words_report_%timestamp%.html

echo.
echo ========================================================
echo   RESUMO FINAL
echo ========================================================
echo.
echo Total de lotes processados: %lote%
echo Log salvo em: %logfile%
echo Relatorio HTML: words_report_%timestamp%.html
echo.
echo [%date% %time%] Resumo: %lote% lotes processados >> "%logfile%"
echo. >> "%logfile%"

set /p open="Abrir relatorio HTML? (S/N): "
if /i "%open%"=="S" (
    start words_report_%timestamp%.html
)

echo.
echo Processamento completo!
echo.
pause
exit /b 0
