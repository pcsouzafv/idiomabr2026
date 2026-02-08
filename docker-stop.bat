@echo off
echo ============================================
echo   IdiomasBR - Docker Stop
echo ============================================
echo.

echo Parando containers de producao...
docker-compose down

echo Parando containers de desenvolvimento...
docker-compose -f docker-compose.dev.yml down

echo.
echo Todos os containers foram parados.
