@echo off
cd /d E:\Projeto_Idiomas\idiomasbr2026

docker cp "words_export (3).csv" idiomasbr-backend:/app/words_export_3.csv
docker cp "corrupted_data.csv" idiomasbr-backend:/app/corrupted_data.csv

docker exec idiomasbr-backend sh -c "cd /app && python scripts/fix_corrupted_from_csv.py --source-csv words_export_3.csv --ids-csv corrupted_data.csv"

pause
