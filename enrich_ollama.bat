@echo off
REM =====================================================
REM  Enriquecimento GRATUITO com Ollama Local
REM  IdiomaBR - SEM CUSTO DE TOKENS!
REM =====================================================

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo   ENRIQUECIMENTO COM OLLAMA - 100%% GRATUITO!
echo ========================================================
echo.
echo Usando IA local (Ollama) - SEM LIMITES e SEM CUSTOS!
echo.

:MENU
echo Escolha uma opcao:
echo.
echo  1. Teste rapido (10 palavras)
echo  2. Lote pequeno (50 palavras)
echo  3. Lote medio (200 palavras)
echo  4. Lote grande (500 palavras)
echo  5. Lote muito grande (1000 palavras)
echo  6. Processar TODAS (sem limite!)
echo  7. Processar por nivel (A1, A2, etc)
echo  8. Verificar status do Ollama
echo  9. Comparar custos (Ollama vs APIs pagas)
echo  10. Sair
echo.

set /p opcao="Digite o numero da opcao: "

if "%opcao%"=="1" goto TEST
if "%opcao%"=="2" goto SMALL
if "%opcao%"=="3" goto MEDIUM
if "%opcao%"=="4" goto LARGE
if "%opcao%"=="5" goto XLARGE
if "%opcao%"=="6" goto ALL
if "%opcao%"=="7" goto BY_LEVEL
if "%opcao%"=="8" goto STATUS
if "%opcao%"=="9" goto COMPARE
if "%opcao%"=="10" goto END

echo Opcao invalida!
goto MENU

:TEST
echo.
echo Testando com 10 palavras...
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --limit 10 --batch 10 --delay 0.2
echo.
pause
goto MENU

:SMALL
echo.
echo Processando 50 palavras...
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --limit 50 --batch 25 --delay 0.2
echo.
pause
goto MENU

:MEDIUM
echo.
echo Processando 200 palavras...
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --limit 200 --batch 50 --delay 0.2
echo.
pause
goto MENU

:LARGE
echo.
echo Processando 500 palavras...
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --limit 500 --batch 100 --delay 0.2
echo.
pause
goto MENU

:XLARGE
echo.
echo Processando 1000 palavras...
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --limit 1000 --batch 100 --delay 0.2
echo.
pause
goto MENU

:ALL
echo.
set /p confirm="Processar TODAS as palavras incompletas? Pode demorar, mas e GRATUITO! (S/N): "
if /i not "%confirm%"=="S" (
    echo Operacao cancelada.
    pause
    goto MENU
)
echo.
echo Processando todas as palavras com Ollama...
echo Isso e 100%% GRATUITO - sem limites!
echo.
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --batch 100 --delay 0.2
echo.
pause
goto MENU

:BY_LEVEL
echo.
echo Escolha o nivel:
echo   1. A1 (iniciante)
echo   2. A2 (basico)
echo   3. B1 (intermediario)
echo   4. B2 (intermediario-avancado)
echo   5. C1 (avancado)
echo   6. C2 (proficiencia)
echo.
set /p level_choice="Digite o numero: "

if "%level_choice%"=="1" set level=A1
if "%level_choice%"=="2" set level=A2
if "%level_choice%"=="3" set level=B1
if "%level_choice%"=="4" set level=B2
if "%level_choice%"=="5" set level=C1
if "%level_choice%"=="6" set level=C2

if not defined level (
    echo Opcao invalida!
    pause
    goto MENU
)

echo.
echo Processando palavras do nivel !level!...
docker exec idiomasbr-backend python scripts/enrich_words_with_ollama.py --level !level! --batch 100 --delay 0.2
echo.
pause
goto MENU

:STATUS
echo.
echo Verificando status do Ollama...
echo.
docker exec idiomasbr-ollama ollama list
echo.
echo Testando conectividade...
docker exec idiomasbr-backend curl -s http://ollama:11434/api/tags | head -20
echo.
pause
goto MENU

:COMPARE
echo.
echo ========================================================
echo   COMPARACAO DE CUSTOS: Ollama vs APIs Pagas
echo ========================================================
echo.
echo Para enriquecer 9.000 palavras (3 campos cada):
echo.
echo OpenAI GPT-4o-mini:
echo   - Custo estimado: $4-5 USD
echo   - Tokens: ~1.5 milhoes
echo   - Tempo: ~90 minutos
echo   - Limite: Pode atingir rate limits
echo.
echo DeepSeek:
echo   - Custo estimado: $2-3 USD
echo   - Tokens: ~1.5 milhoes
echo   - Tempo: ~90 minutos
echo   - Limite: Pode atingir rate limits
echo.
echo Ollama (LOCAL):
echo   - Custo: $0.00 (GRATUITO!)
echo   - Tokens: Ilimitados
echo   - Tempo: ~120-180 minutos*
echo   - Limite: Nenhum!
echo.
echo * Tempo depende do hardware local
echo.
echo Vantagens do Ollama:
echo   + 100%% gratuito e ilimitado
echo   + Privacidade total (processamento local)
echo   + Sem dependencia de internet estavel
echo   + Sem preocupacao com rate limits
echo   + Pode processar em background
echo.
echo Desvantagens:
echo   - Pode ser um pouco mais lento
echo   - Requer recursos locais (CPU/GPU)
echo.
pause
goto MENU

:END
echo.
echo Saindo...
exit /b 0
