@echo off
REM Script rápido de deploy para Windows
REM Usa timestamp automático para garantir atualização

echo ========================================
echo   DEPLOY RAPIDO PARA GCP
echo ========================================
echo.

REM Verificar se bash está disponível (Git Bash)
where bash >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: bash nao encontrado. Instale Git for Windows.
    echo https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Configurações padrão
set PROJECT_ID=idiomasbr
set REGION=us-central1
set DB_INSTANCE_NAME=idiomasbr-db

REM Perguntar se quer validar primeiro
echo Deseja validar antes de fazer deploy? (s/n)
set /p VALIDATE="> "

if /i "%VALIDATE%"=="s" (
    echo.
    echo Executando validacao...
    bash validate_deploy.sh
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo Validacao falhou. Corrija os erros antes de continuar.
        pause
        exit /b 1
    )
    echo.
    echo Pressione qualquer tecla para continuar com o deploy...
    pause >nul
)

echo.
echo Iniciando deploy...
echo Projeto: %PROJECT_ID%
echo Regiao: %REGION%
echo.

REM Executar deploy com timestamp
bash -c "export PROJECT_ID=%PROJECT_ID% && export REGION=%REGION% && export DB_INSTANCE_NAME=%DB_INSTANCE_NAME% && export IMAGE_TAG=v$(date +%%Y%%m%%d-%%H%%M%%S) && bash ./deploy_gcp.sh"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   DEPLOY CONCLUIDO COM SUCESSO!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo   DEPLOY FALHOU!
    echo ========================================
)

pause
