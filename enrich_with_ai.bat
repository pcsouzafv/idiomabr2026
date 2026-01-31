@echo off
REM =====================================================
REM  Enriquecimento Inteligente com IA
REM  IdiomaBR - Usando OpenAI/DeepSeek
REM =====================================================

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo   ENRIQUECIMENTO COM IA - IdiomaBR
echo ========================================================
echo.
echo Este processo usa suas chaves de IA (OpenAI/DeepSeek) para:
echo   - Preencher definicoes em portugues (definition_pt)
echo   - Criar exemplos em ingles (example_en)
echo   - Traduzir exemplos para portugues (example_pt)
echo.

:MENU
echo Escolha uma opcao:
echo.
echo  1. Lote pequeno (50 palavras - teste)
echo  2. Lote medio (200 palavras)
echo  3. Lote grande (500 palavras)
echo  4. Lote muito grande (1000 palavras)
echo  5. Processar TODAS as palavras incompletas
echo  6. Verificar progresso
echo  7. Sair
echo.

set /p opcao="Digite o numero da opcao: "

if "%opcao%"=="1" goto SMALL
if "%opcao%"=="2" goto MEDIUM
if "%opcao%"=="3" goto LARGE
if "%opcao%"=="4" goto XLARGE
if "%opcao%"=="5" goto ALL
if "%opcao%"=="6" goto STATUS
if "%opcao%"=="7" goto END

echo Opcao invalida!
goto MENU

:SMALL
echo.
echo Processando 50 palavras...
docker exec idiomasbr-backend bash -c "cd /app && python scripts/enrich_words_with_ai.py --batch 50 --limit 50 --fields definition_pt,example_en,example_pt --delay 0.8"
echo.
pause
goto MENU

:MEDIUM
echo.
echo Processando 200 palavras...
docker exec idiomasbr-backend bash -c "cd /app && python scripts/enrich_words_with_ai.py --batch 100 --limit 200 --fields definition_pt,example_en,example_pt --delay 0.8"
echo.
pause
goto MENU

:LARGE
echo.
echo Processando 500 palavras...
docker exec idiomasbr-backend bash -c "cd /app && python scripts/enrich_words_with_ai.py --batch 100 --limit 500 --fields definition_pt,example_en,example_pt --delay 0.8"
echo.
pause
goto MENU

:XLARGE
echo.
echo Processando 1000 palavras...
docker exec idiomasbr-backend bash -c "cd /app && python scripts/enrich_words_with_ai.py --batch 200 --limit 1000 --fields definition_pt,example_en,example_pt --delay 0.8"
echo.
pause
goto MENU

:ALL
echo.
set /p confirm="Processar TODAS as palavras incompletas? Isso pode demorar muito! (S/N): "
if /i not "%confirm%"=="S" (
    echo Operacao cancelada.
    pause
    goto MENU
)
echo.
echo Processando todas as palavras...
docker exec idiomasbr-backend bash -c "cd /app && python scripts/enrich_words_with_ai.py --batch 200 --fields definition_pt,example_en,example_pt --delay 0.8"
echo.
pause
goto MENU

:STATUS
echo.
echo Verificando progresso...
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze
echo.
pause
goto MENU

:END
echo.
echo Saindo...
exit /b 0
