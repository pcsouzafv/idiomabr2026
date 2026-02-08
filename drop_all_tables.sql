-- Script para dropar todas as tabelas
-- Executa como superuser ou owner do schema

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Grant permissões
GRANT ALL ON SCHEMA public TO idiomasbr;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
