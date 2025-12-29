-- Script para limpar banco antes de restaurar
-- Remove todas as tabelas do schema public

-- Desabilitar checks de foreign key temporariamente
SET session_replication_role = 'replica';

-- Dropar todas as tabelas (CASCADE para remover dependências)
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;

-- Reabilitar checks
SET session_replication_role = 'origin';

-- Grant permissões
GRANT ALL ON SCHEMA public TO idiomasbr;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
