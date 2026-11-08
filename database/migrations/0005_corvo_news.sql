-- CORVO: notícias que passaram pelo portão de admissão (Oracle), estatísticas do portão e previsões.
-- O Oracle é a base; aqui fica só o que o painel precisa mostrar (ver docs/corvo/ARQUITETURA.md).

CREATE TABLE IF NOT EXISTS corvo_news (
  item_id      TEXT PRIMARY KEY,
  source_id    TEXT NOT NULL,
  source_reliability REAL NOT NULL,
  title        TEXT NOT NULL,
  url          TEXT,
  published_at TEXT NOT NULL,
  ingested_at  TEXT NOT NULL,
  verdict      TEXT NOT NULL CHECK (verdict IN ('hot','buffer')),
  reason       TEXT NOT NULL,
  relevance    REAL NOT NULL,
  kind         TEXT NOT NULL,
  topics       TEXT NOT NULL DEFAULT '[]',
  assets       TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_corvo_news_time ON corvo_news(published_at DESC);

-- Um balde por hora: quantas notícias chegaram e o que o portão decidiu (inclui descartadas, que não têm linha em corvo_news).
CREATE TABLE IF NOT EXISTS corvo_gate_stats (
  bucket     TEXT PRIMARY KEY,
  pressure   TEXT NOT NULL,
  received   INTEGER NOT NULL,
  hot        INTEGER NOT NULL,
  buffer     INTEGER NOT NULL,
  dropped    INTEGER NOT NULL,
  reasons    TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS corvo_forecasts (
  forecast_id TEXT PRIMARY KEY,
  question    TEXT NOT NULL,
  probability REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
  interval_low  REAL NOT NULL,
  interval_high REAL NOT NULL,
  evidences   INTEGER NOT NULL,
  sources     INTEGER NOT NULL,
  method      TEXT NOT NULL,
  horizon     TEXT NOT NULL,
  status      TEXT NOT NULL CHECK (status IN ('aberta','calibrando','resolvida')),
  updated_at  TEXT NOT NULL
);
