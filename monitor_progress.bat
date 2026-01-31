@echo off
REM =====================================================
REM  Monitor de Progresso - Enriquecimento
REM =====================================================

:LOOP
cls
echo.
echo ========================================================
echo   MONITOR DE PROGRESSO - IdiomaBR
echo ========================================================
echo.
echo Atualizacao: %date% %time%
echo.

REM Verificar status
docker exec idiomasbr-backend python scripts/update_words_from_csv.py --analyze 2>nul | findstr /C:"Total de palavras" /C:"Palavras completas" /C:"Precisam enriquecimento" /C:"Defini" /C:"Exemplo"

echo.
echo ========================================================
echo.
echo Pressione Ctrl+C para sair ou aguarde 30 segundos...
timeout /t 30 /nobreak > nul

goto LOOP
