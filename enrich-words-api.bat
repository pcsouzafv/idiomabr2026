@echo off
echo ========================================
echo  IdiomasBR - Enriquecimento via API
echo ========================================
echo.
echo Este script vai buscar definicoes, sinonimos
echo e exemplos de TODAS as palavras usando APIs
echo gratuitas de dicionario.
echo.
echo APIs usadas:
echo - Free Dictionary API (gratuita)
echo - Datamuse API (gratuita)
echo.

:menu
echo Escolha uma opcao:
echo.
echo [1] Enriquecer 100 palavras (teste)
echo [2] Enriquecer 500 palavras
echo [3] Enriquecer 1000 palavras
echo [4] Enriquecer TODAS as palavras (~25 min)
echo [5] Enriquecer palavras especificas
echo [6] Sair
echo.
set /p choice="Digite o numero da opcao: "

if "%choice%"=="1" goto test100
if "%choice%"=="2" goto batch500
if "%choice%"=="3" goto batch1000
if "%choice%"=="4" goto all
if "%choice%"=="5" goto specific
if "%choice%"=="6" goto end
goto menu

:test100
echo.
echo Enriquecendo 100 palavras para teste...
docker-compose exec -T backend python enrich_words_api.py --limit 100
goto done

:batch500
echo.
echo Enriquecendo 500 palavras...
docker-compose exec -T backend python enrich_words_api.py --limit 500
goto done

:batch1000
echo.
echo Enriquecendo 1000 palavras...
docker-compose exec -T backend python enrich_words_api.py --limit 1000
goto done

:all
echo.
echo ATENCAO: Isso pode levar ~25 minutos!
set /p confirm="Tem certeza? (S/N): "
if /i not "%confirm%"=="S" goto menu
echo.
echo Enriquecendo TODAS as palavras...
docker-compose exec -T backend python enrich_words_api.py
goto done

:specific
echo.
echo Digite as palavras separadas por espaco:
echo Exemplo: happy learn time good
echo.
set /p words="Palavras: "
echo.
echo Enriquecendo: %words%
docker-compose exec -T backend python enrich_words_api.py --words %words%
goto done

:done
echo.
echo ========================================
echo  CONCLUIDO!
echo ========================================
echo.
echo As palavras foram enriquecidas com:
echo - Definicoes em ingles
echo - Tipo gramatical
echo - Sinonimos e antonimos
echo - Exemplos de uso
echo - Colocacoes comuns
echo.
echo Acesse http://localhost:3000 para ver!
echo.
pause
goto end

:end
