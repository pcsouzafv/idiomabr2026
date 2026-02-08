@echo off
echo ============================================
echo   IdiomasBR - Docker Start (Producao)
echo ============================================
echo.

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

REM Copiar arquivo de ambiente se nao existir
if not exist ".env" (
    echo Criando arquivo .env a partir de .env.docker...
    copy .env.docker .env
)

echo Iniciando containers...
echo Baixando imagens (services com image: ...)...
call %COMPOSE_CMD% pull

echo Reconstruindo imagens (atualizando base images)...
call %COMPOSE_CMD% build --pull

call %COMPOSE_CMD% up -d

echo.
echo ============================================
echo   Containers iniciados com sucesso!
echo ============================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo   Para ver logs: %COMPOSE_CMD% logs -f
echo   Para parar:    %COMPOSE_CMD% down
echo ============================================
