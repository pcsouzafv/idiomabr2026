@echo off
setlocal enabledelayedexpansion

REM Backup + migration for words schema (safe: only adds columns)
REM You can override defaults by setting POSTGRES_USER / POSTGRES_DB before running.

if "%POSTGRES_USER%"=="" set "POSTGRES_USER=idiomasbr"
if "%POSTGRES_DB%"=="" set "POSTGRES_DB=idiomasbr"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"

if not exist backups\db mkdir backups\db

echo [1/3] Starting postgres container...
docker compose up -d postgres
if errorlevel 1 goto :fail

echo [2/3] Creating backup backups\db\%POSTGRES_DB%_backup_%TS%.sql ...
docker compose exec -T postgres pg_dump -U %POSTGRES_USER% -d %POSTGRES_DB% > backups\db\%POSTGRES_DB%_backup_%TS%.sql
if errorlevel 1 goto :fail

echo [3/3] Applying migration backend\migrations\add_word_details.sql ...
type backend\migrations\add_word_details.sql | docker compose exec -T postgres psql -U %POSTGRES_USER% -d %POSTGRES_DB%
if errorlevel 1 goto :fail

echo.
echo Done. Backup saved to backups\db\%POSTGRES_DB%_backup_%TS%.sql
exit /b 0

:fail
echo.
echo ERROR: backup/migration failed.
echo - Check that postgres is healthy: docker compose ps
echo - Try connecting: docker compose exec postgres psql -U %POSTGRES_USER% -d %POSTGRES_DB%
exit /b 1
