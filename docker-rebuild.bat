@echo off
echo ========================================
echo  IdiomasBR - Rebuild Docker Completo
echo ========================================
echo.
echo Este script vai:
echo - Parar containers
echo - Rebuild das imagens (com novas dependencias)
echo - Iniciar containers
echo - Aplicar migracoes
echo - Enriquecer palavras
echo.

set /p confirm="Deseja continuar? (S/N): "
if /i not "%confirm%"=="S" goto end

echo.
echo [1/6] Parando containers...
docker-compose down
if %errorlevel% neq 0 (
    echo AVISO: Containers podem nao estar rodando
)
echo.

echo [2/6] Removendo imagens antigas...
docker-compose rm -f
echo.

echo [3/6] Rebuild das imagens (pode demorar alguns minutos)...
docker-compose build --no-cache
if %errorlevel% neq 0 (
    echo ERRO: Falha ao fazer build das imagens
    pause
    exit /b 1
)
echo.

echo [4/6] Iniciando containers...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERRO: Falha ao iniciar containers
    pause
    exit /b 1
)
echo.

echo [5/6] Aguardando banco de dados inicializar (15s)...
timeout /t 15 /nobreak > nul
echo.

echo [6/6] Aplicando migracoes do banco de dados...
docker cp backend\migrations\add_word_details.sql idiomasbr-postgres:/tmp/
docker-compose exec -T postgres psql -U idiomasbr -d idiomasbr -f /tmp/add_word_details.sql
if %errorlevel% neq 0 (
    echo AVISO: Migracoes podem ja estar aplicadas
)
echo.

echo ========================================
echo  REBUILD CONCLUIDO!
echo ========================================
echo.
echo Containers rodando:
docker-compose ps
echo.
echo URLs de acesso:
echo - Frontend: http://localhost:3000
echo - Backend:  http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo.
echo Proximos passos:
echo 1. Executar: enrich-words.bat (dados locais)
echo 2. OU executar: enrich-words-api.bat (dados completos)
echo.
pause

:end
