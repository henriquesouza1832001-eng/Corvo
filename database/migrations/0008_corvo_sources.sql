-- Notícias recebidas por fonte em cada hora (JSON {fonte: quantidade}); alimenta o painel de fontes ativas.
ALTER TABLE corvo_gate_stats ADD COLUMN sources TEXT NOT NULL DEFAULT '{}';
