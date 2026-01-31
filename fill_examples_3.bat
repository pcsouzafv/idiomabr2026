@echo off
REM Copiar arquivo para container
docker cp "missing_examples__words_export (3).csv" idiomasbr-backend:/app/missing_examples_3.csv

REM Executar preenchimento com IA
docker exec idiomasbr-backend sh -c "cd /app && python scripts/fill_missing_examples_ai.py --in-csv missing_examples_3.csv --out-csv words_export_examples_filled_3.csv --provider auto --delay 0.0 --resume"

REM Copiar resultado de volta
docker cp idiomasbr-backend:/app/words_export_examples_filled_3.csv "words_export_examples_filled_3.csv"

echo.
echo Preenchimento concluído!
echo Arquivo disponível: words_export_examples_filled_3.csv
