-- Centro de comando da caixa (coletor 24 h): estado e fila de comandos, 100% no banco (sem KV). Idempotente.
-- O Worker também cria estas tabelas sozinho na primeira chamada (apps/worker/src/routes/corvo-box.ts), então rodar esta migration é opcional.
CREATE TABLE IF NOT EXISTS corvo_box_state (
  id      INTEGER PRIMARY KEY CHECK (id = 1),
  status  TEXT NOT NULL,
  seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS corvo_box_cmd (
  id          TEXT PRIMARY KEY,
  action      TEXT NOT NULL,
  arg         INTEGER,
  issued_at   TEXT NOT NULL,
  state       TEXT NOT NULL DEFAULT 'pending',
  ok          INTEGER,
  note        TEXT,
  output      TEXT,
  finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_corvo_box_cmd_issued ON corvo_box_cmd(issued_at);
