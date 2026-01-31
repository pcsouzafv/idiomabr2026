@echo off
REM Script para executar múltiplos lotes de enriquecimento sequencialmente
echo =====================================
echo  ENRIQUECIMENTO EM LOTE - IdiomasBR
echo =====================================
echo.
echo Este script vai executar 3 lotes de 1000 palavras cada
echo Tempo estimado total: ~6-9 minutos
echo.
pause

echo.
echo [LOTE 1/3] Iniciando...
docker exec -i idiomasbr-backend python enrich_words_api.py --limit 1000 --delay 0.15 --commit-every 100
echo.
echo [LOTE 1/3] Concluído!
echo.

echo [LOTE 2/3] Iniciando...
docker exec -i idiomasbr-backend python enrich_words_api.py --limit 1000 --delay 0.15 --commit-every 100
echo.
echo [LOTE 2/3] Concluído!
echo.

echo [LOTE 3/3] Iniciando...
docker exec -i idiomasbr-backend python enrich_words_api.py --limit 1000 --delay 0.15 --commit-every 100
echo.
echo [LOTE 3/3] Concluído!
echo.

echo =====================================
echo  TODOS OS LOTES CONCLUÍDOS!
echo =====================================
echo.
echo Verificando status final...
docker exec -i idiomasbr-backend python -c "from app.core.database import SessionLocal; from app.models.word import Word; from sqlalchemy import func; db = SessionLocal(); total = db.query(func.count(Word.id)).scalar(); missing_word_type = db.query(func.count(Word.id)).filter(Word.word_type == None).scalar(); missing_def_en = db.query(func.count(Word.id)).filter(Word.definition_en == None).scalar(); pct_word_type = ((total - missing_word_type) / total * 100) if total > 0 else 0; pct_def_en = ((total - missing_def_en) / total * 100) if total > 0 else 0; print(f'\nSTATUS FINAL:'); print(f'  Word Type: {pct_word_type:.1f}%% completo ({total - missing_word_type}/{total})'); print(f'  Definition EN: {pct_def_en:.1f}%% completo ({total - missing_def_en}/{total})'); db.close()"
echo.
pause
