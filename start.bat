@echo off
echo ========================================
echo    IdiomasBR - Iniciando Servidores
echo ========================================

echo Iniciando Backend (API)...
start "IdiomasBR Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak > nul

echo Iniciando Frontend (Next.js)...
start "IdiomasBR Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo Servidores iniciados!
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo ========================================
