import pandas as pd
import sys

try:
    df = pd.read_csv('words_export (3).csv', encoding='utf-8-sig')
    
    result = {
        'total_rows': len(df),
        'total_cols': len(df.columns),
        'columns': list(df.columns),
        'has_example_en': 'example_en' in df.columns,
        'has_example_pt': 'example_pt' in df.columns
    }
    
    if result['has_example_en'] and result['has_example_pt']:
        empty_en = df['example_en'].isna() | (df['example_en'].astype(str).str.strip() == '') | (df['example_en'].astype(str).str.strip().str.lower().isin(['nan', 'none', 'null']))
        empty_pt = df['example_pt'].isna() | (df['example_pt'].astype(str).str.strip() == '') | (df['example_pt'].astype(str).str.strip().str.lower().isin(['nan', 'none', 'null']))
        both_empty = empty_en & empty_pt
        
        result['empty_en'] = int(empty_en.sum())
        result['empty_pt'] = int(empty_pt.sum())
        result['both_empty'] = int(both_empty.sum())
        result['filled'] = int((~both_empty).sum())
        
        # Salvar amostra
        if both_empty.sum() > 0:
            sample = df[both_empty][['id', 'english', 'portuguese', 'level']].head(10)
            result['sample'] = sample.to_dict('records')
            
            # Salvar CSV com vazios
            output_file = 'missing_examples__words_export (3).csv'
            df[both_empty].to_csv(output_file, index=False, encoding='utf-8-sig')
            result['output_file'] = output_file
    
    # Salvar resultado
    import json
    with open('analysis_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("OK")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
