-- Orçamento diário de escrita do D1 (ver docs/decisions/0008). Idempotente: igual a database/pending/0005_write_budget.sql.
CREATE TABLE IF NOT EXISTS write_budget (
  day  TEXT PRIMARY KEY,
  rows INTEGER NOT NULL DEFAULT 0
);
