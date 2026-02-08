@echo off
echo Verificando status dos containers...
docker ps -a | findstr idiomas

echo.
echo Verificando logs do PostgreSQL...
docker logs idiomasbr-postgres | tail -50

echo.
echo Tentando conectar ao backend...
curl -s http://localhost:8000/health

echo.
echo Se o PostgreSQL não está respondendo, execute:
echo docker-compose restart
pause
