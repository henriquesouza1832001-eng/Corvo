# 0010 — Pulso vira CORVO

**Decisão.** O projeto passa a se chamar CORVO (Hugin e Munin, os corvos de Odin). O escopo deixa de ser o monitor do Brasil e passa a ser um radar global de notícias (política, catástrofes, macro, cripto, ações, câmbio) que gera previsões calibradas. Trabalha em par com o MNEME (github.com/th1agx/MNEME): o MNEME decide e mede trades, o CORVO entrega contexto externo e nunca ordens.

**O que mudou.** Pacotes `corvo_engine` e `@corvo/*`, documentação, repositório GitHub (`Corvo`) e o front (`apps/web/src/corvo`, sem câmeras, com dados de demonstração).

**O que NÃO mudou (de propósito).** Recursos já implantados: Workers `pulso-api` e `pulso-web`, banco D1 `pulso`, tabelas `_pulso_*` e segredos `PULSO_*`. Renomear quebraria o deploy e os dados; migrar fica para uma etapa própria.

**Pendências.** A lógica de domínio ainda é brasileira (UFs, fontes do INMET, geografia do IBGE). O portão de admissão (`engine/corvo_engine/intake`) ainda não está ligado ao `pipeline.py`. A UI antiga continua em `apps/web/src/App.tsx`, sem ser montada.
