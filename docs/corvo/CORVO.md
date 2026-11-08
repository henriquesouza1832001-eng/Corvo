# CORVO (rascunho, sem commit)

**Significado.** Em referência a Hugin (pensamento) e Munin (memória), os corvos de Odin que sobrevoam os nove reinos e voltam com o que viram. O CORVO lê o mundo (política, catástrofes, macro, cripto, ações, câmbio, commodities) e devolve previsões calibradas, sempre com probabilidade, incerteza e evidências.

**Relação com o MNEME.** MNEME é o trader (decide e mede). CORVO é o olho externo (notícia -> evento -> ativos afetados -> previsão). O CORVO entrega ao MNEME contexto com hora, validade e origem, no "ritmo assíncrono" do Product Charter do MNEME. Nunca ordens.

## Fluxo de entrada (controle de carga)

```
coletores (RSS, GDELT, oficiais)
  -> IntakeGate (engine/pulso_engine/intake/gate.py): frescor, duplicata, quase-duplicata, relevância, cota por fonte
       DROP    descartado, motivo contado
       BUFFER  fica no buffer local (Oracle: SQLite/Postgres) e sobe agregado em lote
       HOT     grava já (D1 + repassa ao MNEME)
  <- Pressure espelha o modo do orçamento do D1 (normal / economia / crítico)
```

- O banco grande e barato é o da Oracle (142 GB livres). O D1 (100 mil linhas/dia) recebe só o que o portão aprova.
- Os pesos de relevância são hipóteses a medir (ablation), não verdade.

## Mais

- Arquitetura (Oracle = base, Cloudflare = painel): [ARQUITETURA.md](ARQUITETURA.md).
- Subir junto do MNEME: [MNEME_INTEGRACAO.md](MNEME_INTEGRACAO.md).
