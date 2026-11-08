# 0010 — Pulso vira CORVO

**Decisão.** O projeto passa a se chamar CORVO (Hugin e Munin, os corvos de Odin). O escopo deixa de ser o monitor do Brasil e passa a ser um radar global de notícias (política, catástrofes, macro, cripto, ações, câmbio) que gera previsões calibradas. Trabalha em par com o MNEME (github.com/th1agx/MNEME): o MNEME decide e mede trades, o CORVO entrega contexto externo e nunca ordens.

**O que mudou.** Pacotes `corvo_engine` e `@corvo/*`, documentação, repositório GitHub (`Corvo`) e o front (`apps/web/src/corvo`, sem câmeras, com dados de demonstração).

**Infra.** Tudo foi renomeado, inclusive a API: Workers `corvo-api` e `corvo-web`, banco D1 `corvo`, KV `CORVO_KV`, variáveis `CORVO_*`. Os recursos antigos (`pulso-api`, `pulso-web`, D1 `pulso`, Turso) continuam existindo na conta Cloudflare, sem uso; apagar fica a critério do dono. O Cron que acionava a coleta brasileira foi desligado e a rota de câmeras removida.

**Pendências.** A lógica de domínio ainda é brasileira (UFs, fontes do INMET, geografia do IBGE). O portão de admissão (`engine/corvo_engine/intake`) ainda não está ligado ao `pipeline.py`. Arquitetura Oracle + Cloudflare: ver `docs/corvo/ARQUITETURA.md`. A UI antiga continua em `apps/web/src/App.tsx`, sem ser montada.
