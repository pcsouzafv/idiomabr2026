@echo off
echo ============================================
echo   IdiomasBR - Docker Start (Producao)
echo ============================================
echo.

REM Copiar arquivo de ambiente se nao existir
if not exist ".env" (
    echo Criando arquivo .env a partir de .env.docker...
    copy .env.docker .env
)

echo Iniciando containers...
docker-compose up --build -d

echo.
echo ============================================
echo   Containers iniciados com sucesso!
echo ============================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo   Para ver logs: docker-compose logs -f
echo   Para parar:    docker-compose down
echo ============================================
