-- Tentativas de áudio (gravação + análise)

CREATE TABLE IF NOT EXISTS audio_attempts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  sentence_id INTEGER NULL REFERENCES sentences(id) ON DELETE SET NULL,
  filename VARCHAR(255) NULL,
  content_type VARCHAR(100) NULL,
  audio_sha256 VARCHAR(64) NOT NULL,
  audio_bytes BYTEA NOT NULL,
  expected_text TEXT NULL,
  transcript TEXT NULL,
  similarity INTEGER NULL,
  ai_feedback TEXT NULL,
  ai_json JSONB NULL,
  model_used VARCHAR(32) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audio_attempts_user_id ON audio_attempts(user_id);
CREATE INDEX IF NOT EXISTS ix_audio_attempts_sentence_id ON audio_attempts(sentence_id);
CREATE INDEX IF NOT EXISTS ix_audio_attempts_audio_sha256 ON audio_attempts(audio_sha256);
