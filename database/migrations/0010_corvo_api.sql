-- API de leitura do CORVO para consumidores externos: chave por cliente, plano e limite diário. Idempotente.
-- O Worker também cria estas tabelas sozinho na primeira chamada (apps/worker/src/routes/corvo-v1.ts), então rodar esta migration é opcional.
-- A chave nunca é guardada: só o SHA-256 dela (key_hash). Cada chamada válida soma 1 linha em corvo_api_usage.
CREATE TABLE IF NOT EXISTS corvo_api_key (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  plan        TEXT NOT NULL,
  key_hash    TEXT NOT NULL UNIQUE,
  daily_limit INTEGER NOT NULL,
  delay_s     INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL,
  revoked_at  TEXT
);
CREATE TABLE IF NOT EXISTS corvo_api_usage (
  key_id TEXT NOT NULL,
  day    TEXT NOT NULL,
  n      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (key_id, day)
);
CREATE INDEX IF NOT EXISTS idx_corvo_news_ingested ON corvo_news(ingested_at, item_id);
