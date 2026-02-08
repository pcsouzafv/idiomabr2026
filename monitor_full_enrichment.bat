@echo off
:: Monitor Full Enrichment Progress
:: Atualiza a cada 30 segundos

:loop
cls
echo ========================================
echo   MONITORAMENTO - ENRIQUECIMENTO TOTAL
echo ========================================
echo.
echo Data/Hora: %date% %time%
echo.

docker exec -i idiomasbr-backend python -c "from app.core.database import SessionLocal; from app.models.word import Word; from sqlalchemy import func; db = SessionLocal(); total = db.query(func.count(Word.id)).scalar(); missing_ipa = db.query(func.count(Word.id)).filter(Word.ipa == None).scalar(); missing_word_type = db.query(func.count(Word.id)).filter(Word.word_type == None).scalar(); missing_def_en = db.query(func.count(Word.id)).filter(Word.definition_en == None).scalar(); missing_def_pt = db.query(func.count(Word.id)).filter(Word.definition_pt == None).scalar(); missing_ex_en = db.query(func.count(Word.id)).filter(Word.example_en == None).scalar(); missing_ex_pt = db.query(func.count(Word.id)).filter(Word.example_pt == None).scalar(); pct_ipa = ((total - missing_ipa) / total * 100) if total > 0 else 0; pct_word_type = ((total - missing_word_type) / total * 100) if total > 0 else 0; pct_def_en = ((total - missing_def_en) / total * 100) if total > 0 else 0; pct_def_pt = ((total - missing_def_pt) / total * 100) if total > 0 else 0; pct_ex_en = ((total - missing_ex_en) / total * 100) if total > 0 else 0; pct_ex_pt = ((total - missing_ex_pt) / total * 100) if total > 0 else 0; print(f'Total: {total:,} palavras'); print(f''); print(f'IPA: {total - missing_ipa:,}/{total:,} ({pct_ipa:.1f}%%) - Faltam {missing_ipa:,}'); print(f'Word Type: {total - missing_word_type:,}/{total:,} ({pct_word_type:.1f}%%) - Faltam {missing_word_type:,}'); print(f'Definition EN: {total - missing_def_en:,}/{total:,} ({pct_def_en:.1f}%%) - Faltam {missing_def_en:,}'); print(f'Definition PT: {total - missing_def_pt:,}/{total:,} ({pct_def_pt:.1f}%%) - Faltam {missing_def_pt:,}'); print(f'Example EN: {total - missing_ex_en:,}/{total:,} ({pct_ex_en:.1f}%%) - Faltam {missing_ex_en:,}'); print(f'Example PT: {total - missing_ex_pt:,}/{total:,} ({pct_ex_pt:.1f}%%) - Faltam {missing_ex_pt:,}'); db.close()"

echo.
echo ========================================
echo Aguardando 30 segundos...
echo Pressione Ctrl+C para sair
echo ========================================
timeout /t 30 /nobreak > nul
goto loop
