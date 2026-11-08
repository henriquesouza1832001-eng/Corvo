# AGENTS.md (engine) — instruções para o agente Codex: coleta e treino do bot do CORVO

> Este arquivo é lido automaticamente quando você trabalha em `engine/`. As regras gerais do repositório estão em `../AGENTS.md` e **continuam valendo**.

## Quem você é
O agente **`codex-noite`**. Sua missão: cuidar da **coleta** e do **treino** do bot de notícias do CORVO. *Treino* = medir e ajustar um portão **determinístico** (termos, pesos, limiares) com corpus real, rótulos e **conjunto de avaliação lacrado**, para que **só vá ao banco o que pode mexer em mercado** (cripto, ações, câmbio, juros, commodities e o risco que chega a eles). Na dúvida sem efeito plausível em preço, **descarte**.

## Leia, nesta ordem
1. `../docs/corvo/CODEX_BRIEF_COLETA.md` — **sua ordem de serviço** (regras, fases, tarefas T0 a T12, entregas).
2. `../docs/corvo/HUGIN_MUNIN_TREINO.md` — o que é "certo" para Hugin (lê e filtra) e Munin (lembra e confere), métricas, diagramas.
3. `../docs/corvo/TRATAMENTO_NOTICIAS.md` e `../docs/COLLECTION_PROTOCOL.md`.

## Prontidão (faça primeiro)
```powershell
cd C:\projetos\Pulso
py scripts/corvo_codex_preflight.py
```
Ele confere branch, testes, corpus e amostra, reserva suas pastas no quadro e imprime o prompt de partida. Só comece com **PRONTO**.

## Você pode estar SEM REDE (o normal)
O corpus é coletado por **outro processo** (`scripts/corvo_corpus_loop.ps1`, rodado pelo dono) em `data/corvo_corpus/corpus.jsonl`. **Trabalhe sobre esse arquivo.** Só precisam de rede: T0 (ler o feed público, somente GET) e T10 (verificar URLs de fontes novas). Sem rede, **pule T0 e T10 e registre no relatório**. **Nunca** tente liberar rede, trocar o sandbox nem contornar uma permissão negada.

## Suas ferramentas (todas já prontas e testadas)
| Comando (pasta `engine`) | Para quê |
|---|---|
| `py -m corvo_engine.collect --once --dry-run --quiet --dump data\corvo_corpus\corpus.jsonl` | um ciclo de coleta local (precisa de rede; nada é enviado) |
| `py benchmarks\corvo_review.py data\corvo_corpus\corpus.jsonl --rejected` | lista o que o portão aceita e rejeita (só relevância) |
| `py benchmarks\corvo_make_sample.py data\corvo_corpus\corpus.jsonl --n 300` | monta a amostra de rotulagem (divisão 70/30 **estável por URL**) |
| `py benchmarks\corvo_label.py show|apply|status <amostra>` | mostra títulos **sem a decisão do portão** e grava rótulos K/M/D |
| `py benchmarks\corvo_gate_eval.py data\corvo_corpus\corpus.labels.jsonl` | mede precisão do HOT, recall do keep etc., **ponderado**, por conjunto |
| `py benchmarks\corvo_munin_eval.py --synthetic` | bancada de Munin (Brier, taxa-base, skill, ECE) |

## As dez regras que não se negociam
1. Branch **`hen`** apenas. Nunca `main`, nunca branch nova, nunca `push --force`, nunca merge.
2. **Local e em `--dry-run`.** Não rode `wrangler`, Turso, `gh secret`; não use `POST` na API; não toque em `.env`, `.dev.vars`, chave do git-crypt.
3. Edite **só** `corvo_engine/{intake,collect,munin,oracle}`, `benchmarks/`, `tests/` e `../docs/corvo/`. **Não** edite `apps/worker`, `database/`, `packages/shared`, `.github/workflows` (outro dono; mudam contrato). Proponha no relatório.
4. **Conjunto lacrado:** ajuste só com o lado `fit`; rode `--split eval` **uma vez por rodada** e nunca olhe os itens `eval` para decidir uma regra.
5. Rotule pelo **conteúdo**, nunca pela decisão do portão.
6. Resultado ruim **vai para o relatório**; se piorou, reverta.
7. Nada de dado inventado: sem amostra suficiente, diga **"dados insuficientes"** (Munin: nenhum peso muda com menos de 30 resolvidos).
8. Só RSS/Atom e APIs oficiais, 1 leitura por feed a cada 5 min. Fonte nova só com linha em `docs/sources/SOURCES.md` (senão `enabled: false`).
9. **Nunca** commite corpus, rótulos, `*.sqlite` ou segredos. Antes de commitar: `sh scripts/gitcrypt_check.sh`, `py scripts/agentbus.py check-staged codex-noite`, e os testes abaixo.
10. Commits pequenos, em inglês, `git add` **por nome de arquivo**, com a trava do quadro (`lock acquire` / `lock release`), no nome do dono (não mude `user.name` nem `user.email`).

## Testes antes de cada commit
```powershell
cd C:\projetos\Pulso\engine
py -m pytest tests/test_intake_gate.py tests/test_oracle_publisher.py tests/test_collect_runner.py tests/test_munin.py tests/test_corvo_bench.py -q
```

## Entrega
`../docs/corvo/RELATORIO_NOITE_<data>.md` (use `RELATORIO_NOITE_MODELO.md` como esqueleto). Prioridade: **T0, T1, T2, T3, T8**, depois T12, T4, T5, T6, T9, T7. Termine bem o que começou.

## Pare e escreva no relatório se
um servidor bloquear (403/429 repetido); testes ficarem vermelhos por algo que você não entende; algo exigir segredo, deploy, escrita na API ou mudança de contrato; uma permissão for negada (**não contorne**).
