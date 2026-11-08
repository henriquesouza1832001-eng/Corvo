# Preparação para subir junto do MNEME (sem ligar a conexão)

O que está pronto neste repositório e o que falta para entrar no repositório do MNEME (`th1agx/MNEME`). **Nada foi enviado ao repositório do MNEME.**

## Pronto
- `engine/corvo_engine/intake/` — portão de admissão (puro Python, sem rede).
- `engine/corvo_engine/oracle/` — publicador + CLI `python -m corvo_engine.oracle itens.jsonl`.
- `deploy/oracle/` — `compose.yaml`, `Dockerfile`, `loop.sh`, `.env.example`. O serviço lê `/inbox/*.jsonl` a cada minuto.
- Cloudflare: API `corvo-api` e painel `corvo-web` no ar, banco vazio (o painel mostra "demonstração" até chegar o primeiro lote).

## Contrato de entrada (uma linha por notícia)
`{"source_id","url","title","published_at","text","source_reliability"}` — é o que o `robo/mneme/noticias.py` do MNEME já tem de dados; falta só um pequeno adaptador do lado deles que escreva esse `.jsonl` em `inbox/`.

## Como ligar (quando você mandar)
1. No repositório do MNEME, adicionar `corvo/` como subárvore (ou submódulo) com `engine/corvo_engine` e `deploy/oracle`. Usar a branch de colaboração do MNEME e abrir PR; não commitar `.env`.
2. Na A1: `cp deploy/oracle/.env.example deploy/oracle/.env`, colar o token (o mesmo do segredo `INGEST_TOKEN` do Worker) e `docker compose up -d --build`.
3. Fazer o MNEME gravar o `.jsonl` em `deploy/oracle/inbox/`.
4. Abrir o painel e conferir que o selo mudou de "demonstração" para "ao vivo".

## Regras herdadas do MNEME que o CORVO respeita
Texto externo é dado, nunca instrução; na dúvida, "reportagem" e não "fato"; a LLM não envia ordens; custo zero; sem chaves nem IPs no repositório público.

## Ainda não existe
Impacto por ativo (hoje `assets` vai vazio), previsões reais (a tabela existe, ninguém publica nela), fontes globais documentadas em `docs/sources/SOURCES.md`, e o adaptador do lado do MNEME.
