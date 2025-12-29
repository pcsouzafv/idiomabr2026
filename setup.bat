@echo off
echo ========================================
echo    IdiomasBR - Setup Inicial
echo ========================================
echo.

echo [1/4] Criando ambiente virtual Python...
cd backend
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/4] Instalando dependencias do backend...
pip install -r requirements.txt

echo.
echo [3/4] Criando palavras de exemplo...
python import_words.py

echo.
echo [4/4] Instalando dependencias do frontend...
cd ..\frontend
call npm install

echo.
echo ========================================
echo    Setup concluido!
echo ========================================
echo.
echo Para iniciar:
echo.
echo 1. Backend (terminal 1):
echo    cd backend
echo    venv\Scripts\activate
echo    uvicorn app.main:app --reload
echo.
echo 2. Frontend (terminal 2):
echo    cd frontend
echo    npm run dev
echo.
echo Acesse: http://localhost:3000
echo ========================================
pause
