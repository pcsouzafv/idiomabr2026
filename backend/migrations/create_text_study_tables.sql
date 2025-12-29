-- Módulo de Leitura/Escrita: textos e tentativas

CREATE TABLE IF NOT EXISTS study_texts (
  id SERIAL PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  level VARCHAR(8) NOT NULL DEFAULT 'A1',
  content_en TEXT NOT NULL,
  content_pt TEXT NULL,
  tags JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_study_texts_level ON study_texts(level);

CREATE TABLE IF NOT EXISTS study_text_attempts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text_id INTEGER NOT NULL REFERENCES study_texts(id) ON DELETE CASCADE,
  task VARCHAR(32) NOT NULL DEFAULT 'writing',
  user_text TEXT NOT NULL,
  ai_feedback TEXT NULL,
  ai_json JSONB NULL,
  model_used VARCHAR(32) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_study_text_attempts_user_id ON study_text_attempts(user_id);
CREATE INDEX IF NOT EXISTS ix_study_text_attempts_text_id ON study_text_attempts(text_id);
