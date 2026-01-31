"""
Script para corrigir CSV com dados corrompidos no campo level
"""
import pandas as pd
import sys

def fix_corrupted_csv(input_csv: str, output_csv: str):
    """Corrige linhas com level inválido (> 10 chars)"""
    print(f"📖 Lendo {input_csv}...")
    df = pd.read_csv(input_csv, encoding='utf-8-sig')
    
    print(f"Total de linhas: {len(df)}")
    
    # Identificar linhas problemáticas
    problematic = df['level'].fillna('').str.len() > 10
    num_problematic = problematic.sum()
    
    print(f"⚠️  Linhas com level inválido: {num_problematic}")
    
    if num_problematic == 0:
        print("✅ CSV já está correto!")
        return
    
    # Mostrar exemplos antes
    print("\n🔍 Exemplos de linhas problemáticas (ANTES):")
    print(df[problematic][['id', 'english', 'level', 'portuguese']].head(10).to_string())
    
    # Corrigir: definir level como 'A1' para linhas problemáticas
    # (preservando os outros campos)
    df.loc[problematic, 'level'] = 'A1'
    
    # Mostrar exemplos depois
    print("\n✅ Exemplos após correção (DEPOIS):")
    print(df[problematic][['id', 'english', 'level', 'portuguese']].head(10).to_string())
    
    # Salvar
    print(f"\n💾 Salvando CSV corrigido em {output_csv}...")
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print(f"✅ CSV corrigido salvo! {num_problematic} linhas ajustadas.")
    print(f"📊 Total de linhas no arquivo final: {len(df)}")

if __name__ == '__main__':
    input_file = 'words_export_examples_filled__words_export (1).csv'
    output_file = 'words_export_examples_filled__FIXED.csv'
    
    try:
        fix_corrupted_csv(input_file, output_file)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
