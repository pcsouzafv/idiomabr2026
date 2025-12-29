@echo off
echo ============================================
echo   IdiomasBR - Importar Palavras (Docker)
echo ============================================
echo.

echo Importando palavras de exemplo...
docker-compose exec backend python import_words.py

echo.
echo Palavras importadas com sucesso!
