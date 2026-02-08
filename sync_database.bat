@echo off
REM Script Windows para sincronização de banco de dados
REM Wrapper para sync_database.sh

echo ========================================
echo   SINCRONIZACAO DE BANCO - GCP
echo ========================================
echo.

REM Verificar se bash está disponível
where bash >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: bash nao encontrado. Instale Git for Windows.
    echo https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Menu de opções
echo Escolha uma opcao:
echo.
echo 1) Aplicar migracoes (seguro - nao remove dados)
echo 2) Importar palavras dos CSVs (seguro - adiciona dados)
echo 3) Restauracao completa (CUIDADO - apaga tudo)
echo 4) Exportar banco de producao
echo 5) Comparar esquemas
echo 6) Ajuda
echo.

set /p OPCAO="Digite o numero da opcao: "

if "%OPCAO%"=="1" (
    bash sync_database.sh migrations
) else if "%OPCAO%"=="2" (
    bash sync_database.sh seed-words
) else if "%OPCAO%"=="3" (
    echo.
    echo ==========================================
    echo   ATENCAO: RESTAURACAO COMPLETA
    echo ==========================================
    echo   Isso vai APAGAR todos os dados!
    echo.
    set /p CONFIRM="Tem certeza? (digite SIM): "
    if /i "%CONFIRM%"=="SIM" (
        bash sync_database.sh full-restore
    ) else (
        echo Operacao cancelada.
    )
) else if "%OPCAO%"=="4" (
    bash sync_database.sh export-prod
) else if "%OPCAO%"=="5" (
    bash sync_database.sh compare
) else if "%OPCAO%"=="6" (
    bash sync_database.sh --help
) else (
    echo Opcao invalida!
)

echo.
pause
