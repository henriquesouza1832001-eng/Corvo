# Como o CORVO trata e armazena a notícia

Regra central: **o robô avalia antes de gravar qualquer coisa.** Nada vai ao banco sem passar pelo portão, e o que é descartado não deixa texto em lugar nenhum.

## Etapas (engine/corvo_engine)
1. **Coleta** (`collect/`): lê os feeds do catálogo (`collect/catalog.json`), no máximo uma vez a cada 5 min por fonte e 2 conexões por servidor. Só título, link e resumo curto.
2. **Já visto** (`intake/store.py`): se a URL já foi tratada nas últimas 48 h, sai sem nem contar como "recebida". Evita reprocessar e reenviar o mesmo item a cada ciclo.
3. **Portão** (`intake/gate.py`): frescor (6 h), URL repetida, quase-duplicata (mesmo fato em outra fonte), relevância por tema, cota por fonte e pressão do orçamento.
4. **Classificação** (`oracle/publisher.py`): fato (só fonte oficial), reportagem (padrão), rumor, opinião ou previsão de terceiros.
5. **Localização** (`intake/geo.py`): país ou hub citado no título; sem correspondência, não aparece no mapa.
6. **Publicação**: só HOT e BUFFER sobem ao painel; o lote leva também as estatísticas da hora.

## O que fica onde
| Destino da notícia | O que é guardado | Onde | Por quanto tempo |
|---|---|---|---|
| **Descartada** | contador por motivo + código curto da URL (hash), nunca o texto | estatística da hora (banco) e SQLite local do Oracle | 14 dias (contador), 48 h (hash) |
| **BUFFER** (relevância média) | título, link, fonte, tipo, tema, local, relevância | banco do painel | 30 dias |
| **HOT** (relevância alta) | o mesmo que BUFFER | banco do painel | 30 dias |
| Corpo da matéria | **nunca** | só em memória durante o ciclo | – |

## Proteção do banco (ordem de defesa)
1. Portão no Oracle (descarta ~95% do que chega).
2. Pressão: o Oracle lê o consumo do dia no Worker e aperta os cortes (economia: só relevância alta; crítico: só o essencial).
3. Teto duro no Worker (`DAILY_WRITE_LIMIT`): mesmo que o Oracle erre, acima de 60% só entra HOT, acima de 85% só HOT muito relevante, e no limite só estatística.
4. Retenção diária: apaga notícias com mais de 30 dias e estatísticas com mais de 14 dias.

## Medição (primeiro ciclo real, 24 feeds)
818 itens lidos, 0 fontes com falha, **34 aprovados (4%)**. Os pesos de relevância são hipóteses e precisam ser medidos com o tempo (quais temas geram previsão que acerta).

## Limites conhecidos
- Relevância por palavras-chave em inglês e português; outros idiomas passam menos.
- A classificação fato/reportagem/rumor é por regras e erra; por isso o padrão é "reportagem".
- O mapa só mostra países e hubs da tabela de `geo.py`.
- Impacto por ativo (`assets`) ainda vai vazio: depende do motor de previsão.
