@echo off
cd /d E:\Projeto_Idiomas\idiomasbr2026

docker exec idiomasbr-backend sh -c "cd /app && python scripts/update_words_from_csv.py --analyze"

pause
