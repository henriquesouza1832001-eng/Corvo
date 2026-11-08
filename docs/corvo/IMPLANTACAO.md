# Como rodar a coleta do CORVO

A coleta é o programa `python -m corvo_engine.collect`. Ele lê os feeds do catálogo (`engine/corvo_engine/collect/catalog.json`), descarta o que já viu, passa pelo portão e envia só o aprovado à API. Há dois jeitos de mantê-lo rodando.

## 1. GitHub Actions (hoje)
O workflow `.github/workflows/collect.yml` roda a cada 10 minutos, com a memória de URLs já vistas guardada entre execuções.
- **Precisa de dois segredos no repositório** (sem eles ele pula em verde e não grava nada):
  ```
  gh secret set CORVO_API_URL --body "https://corvo-api.henriquesouza.workers.dev"
  gh secret set CORVO_INGEST_TOKEN
  ```
  O segundo pede o valor: é o mesmo `INGEST_TOKEN` do Worker.
- Só agenda a partir da branch principal (`main`).
- Teste sem gravar: execute o workflow à mão com `push = false` (simulação).

## 2. Servidor com Docker
Pasta `deploy/oracle/`: o serviço `coletor` roda a coleta a cada 10 minutos com a memória guardada num volume.
```
cd deploy/oracle
cp .env.example .env        # CORVO_API_URL e CORVO_INGEST_TOKEN (nunca vão para o Git)
docker compose up -d --build
docker compose logs -f coletor
```

## Teste local (nada é enviado)
```
cd engine
py -m corvo_engine.collect --once --dry-run          # mostra o que o portão decidiu
py -m corvo_engine.collect --once --dry-run --quiet --dump data\corvo_corpus\corpus.jsonl   # guarda cada decisão para análise
```

## Segredos
Os valores ficam fora do Git: no Worker (`wrangler secret put`), no GitHub (segredos do repositório) ou num `.env` local ignorado. Para levar um segredo junto do código, use o git-crypt ([GITCRYPT.md](GITCRYPT.md)).
