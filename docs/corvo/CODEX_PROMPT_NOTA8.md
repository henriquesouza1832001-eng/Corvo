# Prompt do Codex, versão "nota 8" (rodada de 3 horas, com entrega preditiva palpável)

> Natureza do CORVO: **robô de regras e estatística, não IA generativa.** Nada de LLM no produto.
> Esta versão corrige o que custou nota na primeira noite (ver [`CODEX_RODADA_3H.md`](CODEX_RODADA_3H.md)): pouca entrega, commits de batimento e espera por dado.

## 1. Como o Codex será avaliado (régua de 0 a 10)
| Critério | Peso | Nota 8 exige |
|---|---|---|
| Entrega preditiva palpável | 3 | cadeia **evento → hipótese → pergunta → probabilidade → registro** rodando de ponta a ponta em dados reais do corpus, com abstenção quando n < 30 |
| Quantidade verificável | 2 | **4 tarefas novas fechadas** (cada uma com teste novo e critério de aceite do briefing cumprido) |
| Honestidade e rigor | 2 | nenhuma alegação sem número no lacre; limitações escritas; nada de lacre aberto para ajustar regra |
| Eficiência | 1 | zero commits de batimento; nenhuma espera por dado (troca de tarefa e registra) |
| Segurança | 1 | `--dry-run`, freio de banco verde ANTES e DEPOIS, nenhum contrato alterado |
| Relatório | 1 | números antes e depois, o que piorou, perguntas ao dono em uma linha cada |

Abaixo de 8 se: qualquer entrega preditiva for só texto (sem código e teste), se houver commit de batimento, ou se uma tarefa for declarada pronta sem o critério de aceite medido.

## 2. O que significa "preditivo palpável" nesta rodada
Não é prever bem (isso exige semanas de dados). É **o robô já fazer o caminho inteiro e mostrar o resultado**:

1. **Evento** (`munin/events.py`): agrupa noticias aprovadas por fato; ID estavel ancorado na primeira publicacao/URL. Para o replay, `available_at` e o maior `cycle_at` do grupo (todas as fontes ja conhecidas); use-o para ordenar eventos e iniciar a janela de preco. Se faltar `cycle_at`, conte e omita o evento do replay, sem adivinhar por `published_at`. Mede fusoes erradas em pares rotulados (meta <= 2%).
2. **Hipótese** (`munin/impact.py`): para cada evento, lista tema → ativos candidatos (já existe a tabela; revise com o corpus real e anote o que não faz sentido).
3. **Pergunta fechada com regra de resolução** (`munin/questions.py`): texto, ativo, horizonte, limiar de retorno anormal, o que anula (mercado fechado) e quando resolve. Determinística.
4. **Probabilidade** (`munin/baseline.py`, já pronto): taxa-base por (tema, ativo, horizonte); **abstenção explícita** com n < 30.
5. **Registro** (`munin/registry.py`, já pronto): grava a previsão em arquivo **local** `engine/data/corvo_corpus/previsoes.jsonl` (sem rede, sem API). Nada é publicado.
6. **Resolução** (`munin/resolve.py`): lê preços de um arquivo local `engine/data/corvo_corpus/precos.csv` (formato: `ativo,timestamp_utc,fechamento`) e fecha cada previsão como sim, não ou anulada. **Sem preços não resolve**: registra "aguardando fonte de preço" (o dono fornece o arquivo; não invente preços).
7. **Painel de prova** (`engine/benchmarks/corvo_munin_backtest.py`): imprime, para as previsões resolvidas, Brier, Brier da taxa-base, skill e ECE; para as abertas, quantas faltam para n = 30 por chave. Se nada resolveu, imprime isso com todas as letras.

**Dado sintético só para teste**, marcado `synthetic` em todo arquivo e nome. Nunca em relatório como se fosse real.

## 3. Fila de trabalho (nessa ordem; 3 horas)
| Tempo | Tarefa | Entrega que conta | Aceite |
|---|---|---|---|
| 0:00–0:20 | **Preparação**: preflight, ciclo de coleta, freio ANTES, lacre novo (40+ keep) | contagens por conjunto no log | freio verde |
| 0:20–1:10 | **P1 Eventos** (`munin/events.py` + `test_munin_events.py`) | eventos reais do corpus, distribuição de fontes por evento | fusões erradas ≤ 2% em ≥ 30 pares rotulados; teste de par positivo e negativo |
| 1:10–1:40 | **Perguntas e resolução** (`questions.py`, `resolve.py`) com preço **sintético** nos testes | previsão aberta → resolvida/anulada | testes de janela, mercado fechado e anulação |
| 1:40–2:10 | **Cadeia ponta a ponta** (script que lê o corpus, gera eventos, perguntas e previsões, grava o arquivo local) | `previsoes.jsonl` com previsões reais **ou** abstenções, com a contagem de cada | todas as abstenções com motivo; nenhuma previsão com n < 30 |
| 2:10–2:40 | **Uma tarefa de qualidade do Hugin**: T6 (geolocalização, falso positivo) **ou** T9 (robustez da coleta) | testes novos | cobertura ≥ 85% (T6) ou ciclo sempre termina (T9) |
| 2:40–3:00 | **Relatório**: freio DEPOIS, placar, o que falta, perguntas | um commit final | seguir `RELATORIO_NOITE_MODELO.md` |

Se uma tarefa travar por falta de dado ou de rede: **anote em uma linha e passe à seguinte**. Nunca espere.

## 4. Regras que não mudam
- Só edita `engine/corvo_engine/{intake,collect,munin,oracle}`, `engine/benchmarks`, `engine/tests`, `docs/corvo`. Branch `hen`. `git add` por nome de arquivo, com a trava do quadro (`agentbus`).
- Proibido: deploy, wrangler, Turso, `gh secret`, POST na API, ler `.env` ou tokens, mudar contrato, editar worker, database, shared e workflows, merge manual, branch nova, `push --force`.
- **Não abrir o lacre** para decidir regra. Uma hipótese por rodada, definida antes da prova.
- **Sem LLM** no produto, no ajuste ou na rotulagem automática de produção. Rótulos de avaliação são do agente e ficam marcados como tais.
- Previsão nunca é publicada: sem probabilidade, intervalo, evidências e método, não existe (o validador do registro já recusa).
- **Um commit por bloco de trabalho**, em inglês, no nome do dono. Batimento só no `TREINO_LOG.md`, junto de um commit com conteúdo.

## 5. Prompt para colar no Codex
```
Releia AGENTS.md e docs/corvo/CODEX_START_HERE.md (git fetch origin; git merge origin/main). Depois leia
docs/corvo/CODEX_PROMPT_NOTA8.md e siga-o à risca: é uma rodada de 3 HORAS, avaliada de 0 a 10; a meta é nota 8.

O CORVO é um robô de regras e estatística, NÃO uma IA generativa. Sem LLM no produto.

ENTREGA: a cadeia preditiva de ponta a ponta, local e em --dry-run: evento (munin/events.py) -> hipótese (impact.py)
-> pergunta fechada com regra de resolução (questions.py) -> probabilidade pela taxa-base com abstenção n<30
(baseline.py) -> registro local (previsoes.jsonl) -> resolução por preço local (resolve.py) -> painel de prova
(corvo_munin_backtest.py). Cada peça com teste novo. Preço sintético só nos testes, marcado "synthetic". Sem arquivo
de preços real, as previsões ficam "aguardando fonte de preço": não invente preço nem resultado.

ORDEM: preparação 20 min -> P1 eventos -> perguntas e resolução -> cadeia ponta a ponta -> UMA tarefa de qualidade
do Hugin (T6 ou T9) -> relatório. Se travar por falta de dado ou rede, anote em uma linha e passe à próxima. NUNCA espere.

PROIBIDO: deploy, wrangler, Turso, gh secret, POST na API, ler .env/tokens, mudar contrato, editar apps/worker, database,
packages/shared, .github/workflows, merge manual, branch nova, push --force. Só edita engine/corvo_engine/{intake,collect,munin,oracle},
engine/benchmarks, engine/tests e docs/corvo. Não abra o lacre para decidir regra.

COMMITS: um por bloco de trabalho (nunca só de batimento), em inglês, git add por nome de arquivo, com a trava do quadro,
no nome do dono. Batimento só no TREINO_LOG.md, junto de um commit com conteúdo. Freio de banco verde ANTES e DEPOIS.
Termine com o relatório (RELATORIO_NOITE_MODELO.md) e as perguntas ao dono em uma linha cada.
```

## 6. Antes de soltar o Codex (o dono)
1. Reativar o laço de coleta do corpus por 3 horas (`scripts/corvo_corpus_loop.ps1 -Hours 3`).
2. **Preços: já existe a coleta.** `py -m corvo_engine.collect.prices` (e o laço do corpus a chama a cada ciclo) grava `engine/data/corvo_corpus/precos.csv` com BTC, ETH, SOL, BNB, XRP (velas de 1 h, cerca de 41 dias) e USD contra EUR, BRL, JPY, GBP, CNY (diário). **Sem ações, índices, petróleo e ouro** (sem fonte pública permitida ainda): previsões desses ativos ficam "aguardando fonte de preço". Ficha em `docs/sources/SOURCES.md`.
3. Garantir que a `main` está sincronizada (`bash scripts/ship.sh`).
