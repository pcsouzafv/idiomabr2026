-- Cria tabela de cache para respostas da IA (deduplicação por hash)

CREATE TABLE IF NOT EXISTS ai_cache (
  id SERIAL PRIMARY KEY,
  cache_key VARCHAR(64) NOT NULL UNIQUE,
  scope VARCHAR(64) NOT NULL DEFAULT 'global',
  operation VARCHAR(64) NOT NULL,
  provider VARCHAR(32) NULL,
  model VARCHAR(64) NULL,
  request_json JSONB NOT NULL,
  response_text TEXT NULL,
  response_json JSONB NULL,
  response_bytes BYTEA NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'ok',
  error TEXT NULL,
  hit_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ai_cache_scope_operation ON ai_cache(scope, operation);
CREATE INDEX IF NOT EXISTS ix_ai_cache_created_at ON ai_cache(created_at);
