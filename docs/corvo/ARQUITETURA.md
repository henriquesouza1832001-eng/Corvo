# Arquitetura do CORVO

```
 fontes (RSS, feeds oficiais)           Oracle A1 (cérebro)                      Cloudflare (só o painel)
 ┌──────────────┐   .jsonl    ┌─────────────────────────────────┐  HTTPS   ┌────────────────────────────┐
 │ MNEME        │ ──────────▶ │ corvo_engine.oracle              │ ───────▶ │ corvo-api (Worker + Hono)  │
 │ noticias.py  │   /inbox    │  IntakeGate -> OraclePublisher   │  POST    │  D1 corvo  +  KV (cache)   │
 └──────────────┘             │  (dedup, relevância, cota, pressão)│ ingest  └─────────────┬──────────────┘
                              └───────────────▲─────────────────┘                        │ GET /api/corvo/feed
                                              └── GET /api/corvo/pressure ───────────────┤
                                                                                    ┌────▼─────────────┐
                                                                                    │ corvo-web (painel)│
                                                                                    └──────────────────┘
```

**Papéis.** O Oracle é a base: coleta, decide, guarda o histórico grande e roda o motor. O Cloudflare só mostra: D1 guarda o que o painel exibe e KV guarda o instantâneo do feed por 60 s. Nada de ordem de trade passa por aqui.

**Controle de carga (o ponto central).** O D1 grátis aceita 100 mil linhas por dia. Por isso:
1. O portão (`corvo_engine/intake/gate.py`) descarta duplicata, quase-duplicata, notícia velha, assunto fora do escopo e excesso por fonte. Descartes viram só contadores por motivo (uma linha por hora em `corvo_gate_stats`).
2. Só HOT e BUFFER viram linha em `corvo_news`.
3. O Worker soma as linhas gravadas em `write_budget`; o Oracle lê a pressão em `GET /api/corvo/pressure` (normal, economia, crítico) e aperta os cortes. Se não conseguir ler, assume economia.

## API (corvo-api)

| Rota | Quem | O que faz |
|---|---|---|
| `POST /api/corvo/ingest` | Oracle (Bearer `INGEST_TOKEN`) | grava notícias aprovadas, estatísticas do portão e previsões. Recusa previsão sem método ou com probabilidade fora do intervalo, e notícia descartada |
| `GET /api/corvo/pressure` | Oracle | modo do orçamento de escrita |
| `GET /api/corvo/feed` | painel (público) | feed, estatísticas das últimas 24 h, previsões e orçamento; cache de KV |

## Recursos no Cloudflare

Worker `corvo-api` (D1 `corvo`, KV `CORVO_KV`), Worker `corvo-web` (painel estático). URLs provisórias em `*.henriquesouza.workers.dev`.
Subdomínio próprio: depende de um domínio na Cloudflare; basta acrescentar `routes: [{ pattern: "painel.SEU-DOMINIO", custom_domain: true }]` em `apps/web/wrangler.jsonc` e incluir a origem em `ALLOWED_ORIGINS`.
