@echo off
cd /d E:\Projeto_Idiomas\idiomasbr2026

docker cp "words_export_examples_filled_3.csv" idiomasbr-backend:/app/words_export_examples_filled_3.csv

docker exec idiomasbr-backend sh -c "cd /app && python scripts/update_words_from_csv.py --import --csv-path words_export_examples_filled_3.csv --apply"

pause
