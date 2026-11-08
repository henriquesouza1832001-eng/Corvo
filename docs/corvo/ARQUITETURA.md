# Arquitetura do CORVO

```text
 feeds públicos            coletor (Python)                       Cloudflare                       painel
 ┌──────────────┐   ┌────────────────────────────┐  HTTPS   ┌──────────────────────────┐   ┌─────────────┐
 │ bancos       │   │ corvo_engine.collect       │ ───────▶ │ corvo-api (Worker/Hono)  │──▶│ corvo-web   │
 │ centrais,    │──▶│  já visto? → portão (Hugin)│  POST    │  Turso (banco)           │   │ (React)     │
 │ agências,    │   │  → classifica → localiza   │  ingest  │  KV (cache do feed, 60 s)│   └─────────────┘
 │ imprensa,    │   └──────────────▲─────────────┘          └─────────────┬────────────┘     GET /feed
 │ cripto       │                  └──── GET /api/corvo/pressure ─────────┘
 └──────────────┘
```

**Quem faz o quê.** O coletor roda a cada 10 minutos (GitHub Actions ou um servidor com Docker, ver [IMPLANTACAO.md](IMPLANTACAO.md)). A API só grava o que o portão aprovou e as estatísticas da hora. O painel só lê.

## Controle de carga (o ponto central)
O banco tem limite de escritas. Por isso, em ordem de defesa:
1. **Portão (Hugin)** no coletor: descarta duplicata, quase-duplicata, notícia velha, assunto fora de mercado e excesso por fonte. Descarte vira só contador por motivo (uma linha por hora).
2. **Pressão:** o coletor lê o consumo do dia (`GET /api/corvo/pressure`: normal, economia, crítico) e aperta os cortes.
3. **Teto duro na API** (`DAILY_WRITE_LIMIT`, hoje 300 mil linhas/dia): acima de 60% só entra o que é "grava já"; acima de 85% só o muito relevante; no limite, só estatística.
4. **Retenção diária:** notícias com mais de 30 dias e estatísticas com mais de 14 dias são apagadas.

Hoje o ritmo projetado é de cerca de 500 linhas por dia (`engine/benchmarks/corvo_budget_check.py`).

## API (corvo-api)
| Rota | Quem usa | O que faz |
|---|---|---|
| `POST /api/corvo/ingest` | coletor (token) | grava notícias aprovadas, estatísticas da hora (soma por hora) e previsões. Recusa previsão sem método, ou com probabilidade fora do intervalo, e notícia descartada |
| `GET /api/corvo/pressure` | coletor (token) | consumo do dia e modo (normal, economia, crítico) |
| `GET /api/corvo/feed` | painel (público) | notícias, estatísticas das últimas 24 h, previsões e orçamento; cache de KV |
| `POST /api/corvo/purge` | dono (token) | apaga notícias e estatísticas (tudo ou por prazo) |

## Recursos no Cloudflare
Worker `corvo-api` (banco Turso, cache KV `CORVO_KV`) e Worker `corvo-web` (painel estático), em `*.henriquesouza.workers.dev`. Segredos do Worker: `INGEST_TOKEN`, `TURSO_URL`, `TURSO_TOKEN` (nunca no repositório). Subdomínio próprio: depende de um domínio na Cloudflare; basta acrescentar `routes: [{ pattern: "painel.SEU-DOMINIO", custom_domain: true }]` em `apps/web/wrangler.jsonc` e incluir a origem em `ALLOWED_ORIGINS`.
