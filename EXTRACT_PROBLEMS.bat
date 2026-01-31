@echo off
setlocal enabledelayedexpansion
cd /d E:\Projeto_Idiomas\idiomasbr2026

echo Extraindo dados corrompidos do banco...
echo.

python extract_problems.py

if exist database_problems.txt (
    echo.
    echo ✅ Relatório gerado! Conteúdo:
    echo.
    type database_problems.txt
) else (
    echo Erro ao gerar relatório
)

pause
