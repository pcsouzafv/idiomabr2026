@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Script para atualizar e reconstruir as imagens Docker do IdiomasBR (Windows)

REM Permite rodar sem travar em ambientes nao-interativos (ex: extensoes/CI)
set "NOPAUSE="
if /i "%~2"=="nopause" set "NOPAUSE=1"
if /i "%NO_PAUSE%"=="1" set "NOPAUSE=1"

REM Garante execucao a partir da pasta onde este .bat esta localizado (raiz do repo)
pushd "%~dp0"

REM Seleciona o comando do Compose (prefere v2: "docker compose" / fallback v1: "docker-compose")
set "COMPOSE_CMD="
docker compose version >nul 2>&1
if %errorlevel%==0 (
    set "COMPOSE_CMD=docker compose"
) else (
    where docker-compose >nul 2>&1
    if %errorlevel%==0 (
        set "COMPOSE_CMD=docker-compose"
    )
)

if "%COMPOSE_CMD%"=="" (
    echo ERRO: Nao foi encontrado "docker compose" nem "docker-compose".
    echo       Instale/atualize o Docker Desktop e tente novamente.
    pause
    exit /b 1
)

echo ============================================
echo   ATUALIZACAO DAS IMAGENS DOCKER - IdiomasBR
echo ============================================
echo.

REM Verifica se Docker esta rodando
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Docker nao esta rodando!
    echo        Inicie o Docker Desktop e tente novamente.
    pause
    exit /b 1
)

echo Docker esta rodando
echo.

REM Menu de opcoes
echo Escolha uma opcao:
echo 1. Atualizar TUDO (Backend + Frontend + DB)
echo 2. Atualizar apenas Backend
echo 3. Atualizar apenas Frontend
echo 4. Reconstruir sem cache (completo)
echo 5. Ver logs dos containers
echo.
echo Dica: voce pode passar a opcao como argumento:
echo       update-docker.bat 2
echo.
set "opcao=%~1"
if /i "%opcao%"=="help" goto ajuda
if "%opcao%"=="" (
    REM Em alguns terminais (ex: execucao via extensoes), nao ha stdin interativo.
    set /p opcao="Digite o numero da opcao: " || (set "opcao=1" & set "NOPAUSE=1")
)
if "%opcao%"=="" set "opcao=1"

if "%opcao%"=="1" goto atualizar_tudo
if "%opcao%"=="2" goto atualizar_backend
if "%opcao%"=="3" goto atualizar_frontend
if "%opcao%"=="4" goto reconstruir_completo
if "%opcao%"=="5" goto ver_logs

echo.
echo ERRO: Opcao invalida!
echo.
echo Use: update-docker.bat help
pause
exit /b 1

:ajuda
echo.
echo Uso:
echo   update-docker.bat ^<opcao^>
echo.
echo Opcoes:
echo   1  Atualizar tudo (build + up)
echo   2  Atualizar apenas backend
echo   3  Atualizar apenas frontend
echo   4  Reconstruir completo sem cache
echo   5  Ver logs
echo.
echo Observacao:
echo   Se voce rodar sem opcao e nao houver entrada interativa, o padrao sera 1.
echo.
if not defined NOPAUSE pause
exit /b 0

:atualizar_tudo
echo.
echo Atualizando todos os servicos...
echo ==================================
echo.

echo Parando containers...
call %COMPOSE_CMD% down

echo Baixando imagens (services com image: ...)...
call %COMPOSE_CMD% pull

echo Reconstruindo imagens...
call %COMPOSE_CMD% build --pull

echo Iniciando servicos...
call %COMPOSE_CMD% up -d

echo.
echo Todos os servicos foram atualizados!
goto fim

:atualizar_backend
echo.
echo Atualizando Backend...
echo ========================
echo.

echo Parando backend...
call %COMPOSE_CMD% stop backend

echo Reconstruindo backend...
call %COMPOSE_CMD% build --pull backend

echo Iniciando backend...
call %COMPOSE_CMD% up -d backend

echo.
echo Backend atualizado!
goto fim

:atualizar_frontend
echo.
echo Atualizando Frontend...
echo =========================
echo.

echo Parando frontend...
call %COMPOSE_CMD% stop frontend

echo Reconstruindo frontend...
call %COMPOSE_CMD% build --pull frontend

echo Iniciando frontend...
call %COMPOSE_CMD% up -d frontend

echo.
echo Frontend atualizado!
goto fim

:reconstruir_completo
echo.
echo Reconstrucao completa (sem cache)...
echo =======================================
echo.

echo Parando containers...
call %COMPOSE_CMD% down

echo Removendo containers antigos...
call %COMPOSE_CMD% rm -f

echo Baixando imagens (services com image: ...)...
call %COMPOSE_CMD% pull

echo Reconstruindo tudo sem cache...
call %COMPOSE_CMD% build --no-cache --pull

echo Iniciando servicos...
call %COMPOSE_CMD% up -d

echo.
echo Reconstrucao completa finalizada!
goto fim

:ver_logs
echo.
echo Logs dos containers
echo =====================
echo.
echo Pressione Ctrl+C para sair
echo.
call %COMPOSE_CMD% logs -f
goto fim

:fim
echo.
echo Status dos containers:
echo ========================
call %COMPOSE_CMD% ps

echo.
echo URLs:
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo Docs API: http://localhost:8000/docs
echo.
echo Atualizacao concluida!
echo.
echo Dica: Para ver os logs em tempo real, execute:
echo       %COMPOSE_CMD% logs -f
echo.
if not defined NOPAUSE pause

popd
endlocal
