@echo off
echo ========================================
echo  EXPORTACAO E MIGRACAO DE DADOS
echo ========================================
echo.

echo [1/4] Verificando container local...
docker ps --filter "name=idiomasbr-postgres"

echo.
echo [2/4] Exportando dados do banco local...
docker exec idiomasbr-postgres pg_dump -U idiomasbr -d idiomasbr --clean --if-exists > dump_local.sql

if %ERRORLEVEL% NEQ 0 (
    echo ERRO ao exportar dados!
    pause
    exit /b 1
)

echo.
echo [3/4] Dados exportados para dump_local.sql
dir dump_local.sql

echo.
echo [4/4] Pressione qualquer tecla para continuar com a importacao para o Cloud...
pause

echo.
echo Pronto! Agora vou importar para o Cloud SQL...
