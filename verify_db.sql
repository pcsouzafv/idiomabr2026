-- Verificação da sincronização do banco
\dt
SELECT COUNT(*) AS total_words FROM words;
SELECT COUNT(*) AS total_users FROM users;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
