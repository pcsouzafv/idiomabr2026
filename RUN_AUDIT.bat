@echo off
cd /d E:\Projeto_Idiomas\idiomasbr2026
echo Executando auditoria do banco...
echo.
python audit_database.py
echo.
echo ========================================
echo Resultados salvos em: audit_results.json
echo ========================================
pause
