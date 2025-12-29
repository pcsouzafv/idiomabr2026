@echo off
echo ============================================
echo   IdiomasBR - Docker Start (Desenvolvimento)
echo ============================================
echo.

echo Iniciando containers com hot-reload...
docker-compose -f docker-compose.dev.yml up --build

echo.
echo Containers finalizados.
