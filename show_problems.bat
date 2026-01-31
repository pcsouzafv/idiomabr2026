@echo off
cd /d E:\Projeto_Idiomas\idiomasbr2026
python export_problems.py
type problematic_words.csv | more
