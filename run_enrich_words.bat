@echo off
setlocal enabledelayedexpansion

REM Runs bulk word enrichment inside the backend container.
REM Avoids copy/paste issues in terminals.

if "%DELAY%"=="" set "DELAY=0.3"
if "%COMMIT_EVERY%"=="" set "COMMIT_EVERY=50"

echo Starting required containers...
docker compose up -d postgres backend
if errorlevel 1 goto :fail

set "LIMIT_ARG="
if not "%LIMIT%"=="" set "LIMIT_ARG=--limit %LIMIT%"

echo.
echo Running enrichment:
echo   python enrich_words_api.py %LIMIT_ARG% --delay %DELAY% --commit-every %COMMIT_EVERY%
echo.

docker compose exec backend python enrich_words_api.py %LIMIT_ARG% --delay %DELAY% --commit-every %COMMIT_EVERY%
if errorlevel 1 goto :fail

echo.
echo Done.
exit /b 0

:fail
echo.
echo ERROR: enrichment run failed.
echo Tip: verify containers with: docker compose ps
exit /b 1
