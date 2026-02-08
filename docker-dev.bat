@echo off
echo ============================================
echo   IdiomasBR - Docker Start (Desenvolvimento)
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

echo Iniciando containers com hot-reload...
echo Baixando imagens (services com image: ...)...
call %COMPOSE_CMD% -f docker-compose.dev.yml pull

echo Reconstruindo imagens (atualizando base images)...
call %COMPOSE_CMD% -f docker-compose.dev.yml build --pull

call %COMPOSE_CMD% -f docker-compose.dev.yml up

echo.
echo Containers finalizados.
