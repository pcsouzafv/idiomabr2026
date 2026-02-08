@echo off
REM Quick check and setup for AI enrichment

echo ========================================
echo VERIFICACAO DE CONFIGURACAO DE IA
echo ========================================
echo.

REM Check if .env exists
if exist backend\.env (
    echo [OK] Arquivo backend\.env encontrado
    echo.
    echo Verificando configuracoes...
    echo.
    
    findstr /C:"OPENAI_API_KEY=" backend\.env >nul
    if %errorlevel%==0 (
        echo [OK] OPENAI_API_KEY configurado
    ) else (
        echo [!] OPENAI_API_KEY NAO configurado
    )
    
    findstr /C:"DEEPSEEK_API_KEY=" backend\.env >nul
    if %errorlevel%==0 (
        echo [OK] DEEPSEEK_API_KEY configurado
    ) else (
        echo [!] DEEPSEEK_API_KEY NAO configurado
    )
    
    findstr /C:"DATABASE_URL=" backend\.env >nul
    if %errorlevel%==0 (
        echo [OK] DATABASE_URL configurado
    ) else (
        echo [!] DATABASE_URL NAO configurado
    )
) else (
    echo [ERRO] Arquivo backend\.env NAO encontrado!
    echo.
    echo Criando arquivo .env a partir do .env.example...
    if exist backend\.env.example (
        copy backend\.env.example backend\.env
        echo.
        echo [OK] Arquivo backend\.env criado!
        echo Por favor, edite backend\.env e adicione suas chaves de API:
        echo   - OPENAI_API_KEY=sk-...
        echo   - DEEPSEEK_API_KEY=sk-...
        echo.
        notepad backend\.env
    ) else (
        echo [ERRO] backend\.env.example nao encontrado!
    )
)

echo.
echo ========================================
echo.
echo Para usar o sistema de enriquecimento:
echo 1. Configure pelo menos UMA chave de API no backend\.env:
echo    - OPENAI_API_KEY=sk-... (recomendado)
echo    - DEEPSEEK_API_KEY=sk-... (alternativa mais barata)
echo.
echo 2. Execute: enrich_ai.bat
echo.
echo Documentacao completa: AI_ENRICHMENT_GUIDE.md
echo ========================================
echo.
pause
