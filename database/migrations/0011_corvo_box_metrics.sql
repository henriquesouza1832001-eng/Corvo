-- Indicadores por hora da caixa (temperatura, CPU, energia estimada, rede e fluxo pelo portão, por fonte). Idempotente.
-- Uma linha por hora UTC (cerca de 24 escritas por dia); o Worker apaga o que passa de 14 dias e também cria a tabela sozinho.
CREATE TABLE IF NOT EXISTS corvo_box_metrics (
  hour TEXT PRIMARY KEY,   -- AAAA-MM-DDTHH (UTC)
  data TEXT NOT NULL       -- JSON do resumo da hora
);
