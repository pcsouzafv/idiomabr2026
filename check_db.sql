
-- Verificar tabela words
SELECT COUNT(*) as total_words FROM words;

-- Verificar example_en e example_pt vazios  
SELECT 
    (SELECT COUNT(*) FROM words WHERE example_en IS NULL OR example_en = '') as empty_example_en,
    (SELECT COUNT(*) FROM words WHERE example_pt IS NULL OR example_pt = '') as empty_example_pt;

-- Mostrar alguns registros com problemas
SELECT id, english, portuguese, 
       example_en, example_pt,
       LENGTH(COALESCE(level, '')) as level_len
FROM words 
WHERE example_en IS NULL OR example_en = '' OR example_pt IS NULL OR example_pt = ''
LIMIT 20;
