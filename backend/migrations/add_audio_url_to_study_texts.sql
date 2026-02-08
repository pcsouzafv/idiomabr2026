-- Adiciona suporte a áudio nos textos de estudo
-- Permite armazenar um link (URL) para o áudio do texto

ALTER TABLE study_texts
ADD COLUMN IF NOT EXISTS audio_url TEXT;
