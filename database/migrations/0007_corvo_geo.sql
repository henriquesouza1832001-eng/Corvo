-- Posição geográfica da notícia (para o mapa-múndi do painel). Opcional: sem localização reconhecida, fica nulo e não aparece no mapa.
ALTER TABLE corvo_news ADD COLUMN lat REAL;
ALTER TABLE corvo_news ADD COLUMN lon REAL;
ALTER TABLE corvo_news ADD COLUMN region TEXT;
