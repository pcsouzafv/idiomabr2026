@echo off
REM =====================================================
REM  Script de Atualização Rápida de Palavras
REM  IdiomaBR - Sistema de Aprendizado de Inglês
REM =====================================================

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo   ATUALIZACAO DE PALAVRAS - IdiomaBR
echo ========================================================
echo.

:MENU
echo Escolha uma opcao:
echo.
echo  1. Analisar estado atual (CSV + Banco)
echo  2. Importar CSV (DRY-RUN - apenas visualizar)
echo  3. Importar CSV (APLICAR mudancas)
echo  4. Importar e Marcar (APLICAR tudo)
echo  5. Enriquecer palavras marcadas
echo  6. Gerar relatorio HTML
echo  7. Workflow completo (Backup + Import + Enrich + Report)
echo  8. Ver estatisticas rapidas
echo  9. Sair
echo.

set /p opcao="Digite o numero da opcao: "

if "%opcao%"=="1" goto ANALISAR
if "%opcao%"=="2" goto IMPORT_DRYRUN
if "%opcao%"=="3" goto IMPORT_APPLY
if "%opcao%"=="4" goto IMPORT_MARK_APPLY
if "%opcao%"=="5" goto ENRICH
if "%opcao%"=="6" goto REPORT
if "%opcao%"=="7" goto WORKFLOW
if "%opcao%"=="8" goto STATS
if "%opcao%"=="9" goto END

echo Opcao invalida!
goto MENU

:ANALISAR
echo.
echo ========================================================
echo   ANALISANDO ESTADO ATUAL
echo ========================================================
echo.
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
echo.
pause
goto MENU

:IMPORT_DRYRUN
echo.
echo ========================================================
echo   IMPORTACAO (DRY-RUN - SEM APLICAR)
echo ========================================================
echo.
echo Isso mostrara o que sera feito SEM modificar o banco.
echo.
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment
echo.
pause
goto MENU

:IMPORT_APPLY
echo.
echo ========================================================
echo   IMPORTACAO (APLICAR MUDANCAS)
echo ========================================================
echo.
set /p confirm="Tem certeza? Isso vai modificar o banco de dados (S/N): "
if /i not "%confirm%"=="S" (
    echo Operacao cancelada.
    pause
    goto MENU
)
echo.
echo Aplicando mudancas...
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --apply
echo.
pause
goto MENU

:IMPORT_MARK_APPLY
echo.
echo ========================================================
echo   IMPORTAR E MARCAR (APLICAR TUDO)
echo ========================================================
echo.
echo Isso vai:
echo   1. Importar dados do CSV
echo   2. Marcar palavras incompletas para enriquecimento
echo.
set /p confirm="Confirma? (S/N): "
if /i not "%confirm%"=="S" (
    echo Operacao cancelada.
    pause
    goto MENU
)
echo.
echo Processando...
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply
echo.
echo Concluido!
pause
goto MENU

:ENRICH
echo.
echo ========================================================
echo   ENRIQUECENDO PALAVRAS
echo ========================================================
echo.
echo Escolha o tamanho do lote:
echo   1. Pequeno (50 palavras)
echo   2. Medio (100 palavras)
echo   3. Grande (200 palavras)
echo   4. Customizado
echo.
set /p lote="Digite a opcao (1-4): "

if "%lote%"=="1" set batch=50
if "%lote%"=="2" set batch=100
if "%lote%"=="3" set batch=200
if "%lote%"=="4" (
    set /p batch="Digite o numero de palavras: "
)

echo.
echo Enriquecendo !batch! palavras...
echo Isso pode demorar alguns minutos...
echo.
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment --batch !batch!
echo.
echo Concluido!
pause
goto MENU

:REPORT
echo.
echo ========================================================
echo   GERANDO RELATORIO HTML
echo ========================================================
echo.
docker exec idiomasbr-backend python scripts/generate_words_report.py
echo.
set /p open="Abrir relatorio no navegador? (S/N): "
if /i "%open%"=="S" (
    start words_report.html
)
pause
goto MENU

:WORKFLOW
echo.
echo ========================================================
echo   WORKFLOW COMPLETO
echo ========================================================
echo.
echo Este processo vai executar:
echo   1. Backup do banco de dados
echo   2. Importar dados do CSV
echo   3. Marcar palavras incompletas
echo   4. Enriquecer palavras (50 por vez)
echo   5. Gerar relatorio final
echo.
set /p confirm="Confirma execucao completa? (S/N): "
if /i not "%confirm%"=="S" (
    echo Operacao cancelada.
    pause
    goto MENU
)

echo.
echo [1/5] Fazendo backup...
docker exec -it idiomasbr-postgres pg_dump -U idiomasbr -d idiomasbr > backup_antes_update_%date:~-4,4%%date:~-7,2%%date:~-10,2%.sql
if errorlevel 1 (
    echo ERRO ao fazer backup!
    pause
    goto MENU
)
echo Backup salvo!

echo.
echo [2/5] Analisando estado atual...
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze

echo.
echo [3/5] Importando e marcando...
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --import --mark-for-enrichment --apply
if errorlevel 1 (
    echo ERRO na importacao!
    pause
    goto MENU
)

echo.
echo [4/5] Enriquecendo palavras...
docker exec idiomasbr-backend python scripts/enrich_words_api.py --tags needs_enrichment --batch 50

echo.
echo [5/5] Gerando relatorio final...
docker exec idiomasbr-backend python scripts/generate_words_report.py

echo.
echo ========================================================
echo   WORKFLOW CONCLUIDO COM SUCESSO!
echo ========================================================
echo.
echo Arquivos gerados:
echo   - backup_antes_update_*.sql (backup do banco)
echo   - words_report.html (relatorio visual)
echo.
set /p open="Abrir relatorio? (S/N): "
if /i "%open%"=="S" (
    start words_report.html
)
pause
goto MENU

:STATS
echo.
echo ========================================================
echo   ESTATISTICAS RAPIDAS
echo ========================================================
echo.
echo Conectando ao banco...
docker exec idiomasbr-postgres psql -U idiomasbr -d idiomasbr -c "SELECT COUNT(*) as total_palavras FROM words;"
echo.
docker exec idiomasbr-postgres psql -U idiomasbr -d idiomasbr -c "SELECT level, COUNT(*) as quantidade FROM words GROUP BY level ORDER BY level;"
echo.
docker exec idiomasbr-postgres psql -U idiomasbr -d idiomasbr -c "SELECT COUNT(*) as sem_definicao_en FROM words WHERE definition_en IS NULL OR definition_en = '';"
echo.
docker exec idiomasbr-postgres psql -U idiomasbr -d idiomasbr -c "SELECT COUNT(*) as sem_exemplo_en FROM words WHERE example_en IS NULL OR example_en = '';"
echo.
pause
goto MENU

:END
echo.
echo Saindo...
echo.
exit /b 0
