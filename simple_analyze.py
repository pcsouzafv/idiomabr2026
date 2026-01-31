import pandas as pd

df = pd.read_csv('words_export (3).csv', encoding='utf-8-sig')

with open('analysis_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Total de linhas: {len(df)}\n")
    f.write(f"Total de colunas: {len(df.columns)}\n\n")
    
    f.write("Colunas:\n")
    for col in df.columns:
        f.write(f"  - {col}\n")
    
    if 'example_en' in df.columns and 'example_pt' in df.columns:
        empty_en = df['example_en'].isna() | (df['example_en'].astype(str).str.strip() == '')
        empty_pt = df['example_pt'].isna() | (df['example_pt'].astype(str).str.strip() == '')
        both_empty = empty_en & empty_pt
        
        f.write(f"\nexample_en vazios: {empty_en.sum()}\n")
        f.write(f"example_pt vazios: {empty_pt.sum()}\n")
        f.write(f"Ambos vazios: {both_empty.sum()}\n")
        f.write(f"Pelo menos um preenchido: {(~both_empty).sum()}\n")
        
        if both_empty.sum() > 0:
            df[both_empty].to_csv('missing_examples__words_export (3).csv', index=False, encoding='utf-8-sig')
            f.write(f"\nArquivo gerado: missing_examples__words_export (3).csv\n")

print("Análise concluída! Veja analysis_output.txt")
