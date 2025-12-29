@echo off
echo Conectando ao Cloud SQL e populando banco de dados...
echo.

gcloud beta sql connect idiomasbr-db --user=idiomasbr --database=idiomasbr

echo.
echo Agora execute os seguintes comandos SQL:
echo.
echo INSERT INTO words (english, ipa, portuguese, level, tags, created_at, updated_at)
echo VALUES
echo ('hello', 'həˈloʊ', 'olá', 'A1', 'saudação', NOW(), NOW()),
echo ('goodbye', 'ɡʊdˈbaɪ', 'adeus', 'A1', 'saudação', NOW(), NOW()),
echo ('thank you', 'θæŋk juː', 'obrigado', 'A1', 'saudação', NOW(), NOW()),
echo ('please', 'pliːz', 'por favor', 'A1', 'saudação', NOW(), NOW()),
echo ('water', 'ˈwɔːtər', 'água', 'A1', 'comida', NOW(), NOW())
echo ON CONFLICT (english) DO NOTHING;
echo.
