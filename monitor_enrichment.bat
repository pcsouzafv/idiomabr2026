@echo off
REM Script para monitorar o progresso do enriquecimento do banco de dados
echo =====================================
echo  MONITOR DE ENRIQUECIMENTO - IdiomasBR
echo =====================================
echo.

:loop
docker exec -i idiomasbr-backend python -c "from app.core.database import SessionLocal; from app.models.word import Word; from sqlalchemy import func; import datetime; db = SessionLocal(); total = db.query(func.count(Word.id)).scalar(); missing_ipa = db.query(func.count(Word.id)).filter(Word.ipa == None).scalar(); missing_word_type = db.query(func.count(Word.id)).filter(Word.word_type == None).scalar(); missing_def_en = db.query(func.count(Word.id)).filter(Word.definition_en == None).scalar(); missing_def_pt = db.query(func.count(Word.id)).filter(Word.definition_pt == None).scalar(); missing_ex_sentences = db.query(func.count(Word.id)).filter(Word.example_sentences == None).scalar(); now = datetime.datetime.now().strftime('%%H:%%M:%%S'); pct_word_type = ((total - missing_word_type) / total * 100) if total > 0 else 0; pct_def_en = ((total - missing_def_en) / total * 100) if total > 0 else 0; print(f'[{now}] Word Type: {pct_word_type:.1f}%% | Def EN: {pct_def_en:.1f}%% | Faltam: {missing_word_type + missing_def_en}'); db.close()"

timeout /t 30 /nobreak >nul
goto loop
