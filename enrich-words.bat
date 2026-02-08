@echo off
echo ========================================
echo  IdiomasBR - Enriquecimento de Palavras
echo ========================================
echo.

echo [1/4] Aplicando migração do banco de dados...
docker cp backend\migrations\add_word_details.sql idiomasbr-postgres:/tmp/
docker-compose exec -T postgres psql -U idiomasbr -d idiomasbr -f /tmp/add_word_details.sql
if %errorlevel% neq 0 (
    echo ERRO: Falha ao aplicar migração
    pause
    exit /b 1
)
echo ✓ Migração aplicada com sucesso
echo.

echo [2/4] Enriquecendo palavras existentes...
docker-compose exec -T backend python enrich_words.py
if %errorlevel% neq 0 (
    echo ERRO: Falha ao enriquecer palavras
    pause
    exit /b 1
)
echo ✓ Palavras enriquecidas com sucesso
echo.

echo [3/4] Reiniciando backend...
docker-compose restart backend
if %errorlevel% neq 0 (
    echo ERRO: Falha ao reiniciar backend
    pause
    exit /b 1
)
echo ✓ Backend reiniciado
echo.

echo [4/4] Aguardando backend inicializar (10s)...
timeout /t 10 /nobreak > nul
echo ✓ Processo concluído
echo.

echo ========================================
echo  SUCESSO! Sistema atualizado com:
echo  - Novos campos no banco de dados
echo  - Palavras enriquecidas com exemplos
echo  - Interface melhorada nos flashcards
echo ========================================
echo.
echo Acesse: http://localhost:3000
echo.
pause
