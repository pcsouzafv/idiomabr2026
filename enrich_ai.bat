@echo off
REM Script para enriquecer palavras usando IA
REM Gera definições e exemplos automaticamente

echo ========================================
echo ENRIQUECIMENTO DE PALAVRAS COM IA
echo ========================================
echo.

:menu
echo Escolha uma opcao:
echo.
echo 1. Teste (10 palavras, dry-run)
echo 2. Nivel A1 (50 palavras)
echo 3. Nivel A2 (50 palavras)
echo 4. Todos os niveis (100 palavras)
echo 5. Processar TUDO (cuidado: muitas chamadas API!)
echo 6. Custom (especificar parametros)
echo 0. Sair
echo.

set /p choice="Digite sua escolha: "

if "%choice%"=="1" goto test
if "%choice%"=="2" goto a1
if "%choice%"=="3" goto a2
if "%choice%"=="4" goto all
if "%choice%"=="5" goto full
if "%choice%"=="6" goto custom
if "%choice%"=="0" goto end

echo Opcao invalida!
goto menu

:test
echo.
echo Executando teste (10 palavras, dry-run)...
python backend\scripts\enrich_words_with_ai.py --limit 10 --dry-run --delay 0.5
pause
goto menu

:a1
echo.
echo Processando nivel A1 (50 palavras)...
python backend\scripts\enrich_words_with_ai.py --level A1 --limit 50 --delay 1.0
pause
goto menu

:a2
echo.
echo Processando nivel A2 (50 palavras)...
python backend\scripts\enrich_words_with_ai.py --level A2 --limit 50 --delay 1.0
pause
goto menu

:all
echo.
echo Processando todos os niveis (100 palavras)...
python backend\scripts\enrich_words_with_ai.py --limit 100 --delay 1.0
pause
goto menu

:full
echo.
echo ========================================
echo ATENCAO: Isso vai processar TODAS as palavras!
echo Pode levar horas e gastar muita API!
echo ========================================
set /p confirm="Tem certeza? (S/N): "
if /i "%confirm%"=="S" (
    python backend\scripts\enrich_words_with_ai.py --delay 1.5
) else (
    echo Cancelado.
)
pause
goto menu

:custom
echo.
echo Parametros disponiveis:
echo   --fields definition_en,definition_pt,example_en,example_pt
echo   --level A1/A2/B1/B2/C1/C2
echo   --limit N
echo   --delay 1.0
echo   --dry-run
echo.
set /p params="Digite os parametros: "
python backend\scripts\enrich_words_with_ai.py %params%
pause
goto menu

:end
echo.
echo Ate logo!
