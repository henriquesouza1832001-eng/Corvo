# CORVO: visão

**Significado.** Hugin (pensamento) e Munin (memória) são os corvos de Odin: sobrevoam os nove reinos e voltam com o que viram. O CORVO lê o mundo (política, catástrofes, macro, cripto, ações, câmbio, commodities) e, aos poucos, aprende a prever o que vem depois, sempre com probabilidade, incerteza, evidências e método.

**Escopo.** O CORVO é independente: coleta, analisa e prevê. Não envia ordens e não depende de nenhum outro sistema para funcionar.

## Fluxo de entrada
```
feeds públicos
  -> coleta (corvo_engine/collect)
  -> memória de já vistos (corvo_engine/intake/store.py)
  -> portão de admissão (corvo_engine/intake/gate.py): relevância para mercado, frescor, duplicata, cota por fonte, pressão
       DROP    descartado: vira só contador e código curto da URL
       FILA    grava (relevância média) e sobe em lote
       GRAVA   grava já (relevância alta)
  -> API (Cloudflare Worker) -> Turso -> painel
```
Os pesos de relevância são hipóteses a medir, não verdade.

## Mais
- Arquitetura e limites de escrita: [ARQUITETURA.md](ARQUITETURA.md).
- Como tratar e guardar cada notícia: [TRATAMENTO_NOTICIAS.md](TRATAMENTO_NOTICIAS.md).
- Como Hugin e Munin viram o preditivo: [PREDITIVO.md](PREDITIVO.md).
- Como rodar a coleta: [IMPLANTACAO.md](IMPLANTACAO.md).
