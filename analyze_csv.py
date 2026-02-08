"""Analisar CSV para identificar campos vazios"""
import pandas as pd

df = pd.read_csv('words_export (3).csv', encoding='utf-8-sig')

print(f"📊 Análise: words_export (3).csv")
print(f"=" * 70)
print(f"Total de linhas: {len(df)}")
print(f"Total de colunas: {len(df.columns)}")
print(f"\nColunas disponíveis:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

if 'example_en' in df.columns and 'example_pt' in df.columns:
    print(f"\n{'='*70}")
    print("🔍 ANÁLISE DE CAMPOS VAZIOS")
    print(f"{'='*70}")
    
    empty_en = df['example_en'].isna() | (df['example_en'].astype(str).str.strip() == '') | (df['example_en'].astype(str).str.strip().str.lower().isin(['nan', 'none', 'null']))
    print(f"\n📝 example_en:")
    print(f"   Vazios: {empty_en.sum()}")
    print(f"   Preenchidos: {(~empty_en).sum()}")
    
    empty_pt = df['example_pt'].isna() | (df['example_pt'].astype(str).str.strip() == '') | (df['example_pt'].astype(str).str.strip().str.lower().isin(['nan', 'none', 'null']))
    print(f"\n📝 example_pt:")
    print(f"   Vazios: {empty_pt.sum()}")
    print(f"   Preenchidos: {(~empty_pt).sum()}")
    
    both_empty = empty_en & empty_pt
    print(f"\n⚠️  Ambos vazios: {both_empty.sum()}")
    print(f"✅ Pelo menos um preenchido: {(~both_empty).sum()}")
    
    if both_empty.sum() > 0:
        print(f"\n📋 Amostra (10 primeiras linhas com ambos vazios):")
        sample_cols = ['id', 'english', 'portuguese', 'level', 'example_en', 'example_pt']
        available_cols = [c for c in sample_cols if c in df.columns]
        print(df[both_empty][available_cols].head(10).to_string(index=False))
        
        # Gerar CSV com linhas que precisam de exemplos
        print(f"\n💾 Gerando CSV com linhas vazias...")
        output_file = 'missing_examples__words_export (3).csv'
        df[both_empty].to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ Arquivo salvo: {output_file} ({both_empty.sum()} linhas)")
else:
    print("\n⚠️  Colunas 'example_en' e/ou 'example_pt' não encontradas!")
