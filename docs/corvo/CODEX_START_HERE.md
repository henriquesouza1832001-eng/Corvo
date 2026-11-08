<div align="center">

# 🐦‍⬛ CODEX · COMECE AQUI
**Treino noturno do CORVO: coleta e triagem de notícias, sem estourar o banco**

`1 página · leia isto, depois o resto na ordem da seção 3`

</div>

## 1. Em 30 segundos
Você vai **medir e ajustar o portão de notícias** do CORVO (Hugin) e **endurecer a bancada de prova** (Munin). Objetivo: **só vai ao banco o que pode mexer em mercado** (cripto, ações, câmbio, juros, commodities e o risco que chega a eles). Você trabalha **local, em `--dry-run`, na branch `hen`**. Nada é enviado a lugar nenhum.

## 2. 🛑 Regra de ouro: não estourar o banco
O banco (Turso, plano grátis) aceita **10 milhões de escritas por mês**. O Worker corta em **300 mil por dia**. O CORVO hoje projeta **~500 linhas por dia**. Seu trabalho **não pode** subir isso.

| O que | Como você garante |
|---|---|
| **Você nunca escreve no banco** | sem `wrangler`, Turso, `gh secret`, nem `POST` na API. Só leitura (GET) do feed, e só se houver rede |
| **Todo commit passa no freio** | `cd engine` e `py benchmarks\corvo_budget_check.py data\corvo_corpus\corpus.jsonl` → precisa dar **"dentro dos limites seguros"** |
| **Limites do freio** | ≤ **5.000** linhas/dia · ≤ **25.000** com 5× o volume · ≤ **12%** do que é lido sendo aceito |
| **Se o freio falhar** | **não commite**. Afrouxou o filtro? Reverta ou aperte de novo. Escreva no relatório o que aconteceu |
| **Afrouxar é a exceção** | subir pesos, baixar cortes (`GateConfig`) ou ligar fonte nova só com **prova no conjunto lacrado** e o freio verde |
| **Dúvida entre gravar e descartar** | sem efeito plausível em preço → **descarte** |

> **Lembrete de custo:** cada notícia gravada = ~2 linhas. Descartada = **zero** linhas e **nenhum texto** guardado (só contador e hash por 48 h).

## 3. Leia nesta ordem
1. Este arquivo.
2. [`CODEX_BRIEF_COLETA.md`](CODEX_BRIEF_COLETA.md) — **ordem de serviço**: regras, fases, tarefas T0 a T12.
3. [`HUGIN_MUNIN_TREINO.md`](HUGIN_MUNIN_TREINO.md) — o que é "certo", métricas e diagramas.
4. `../../engine/AGENTS.md` — as 10 regras curtas (o Codex lê sozinho em `engine/`).

## 4. Os seis primeiros comandos (PowerShell)
```powershell
cd C:\projetos\Pulso
py scripts/corvo_codex_preflight.py                                   # 1. precisa dar PRONTO
cd engine
py benchmarks\corvo_budget_check.py data\corvo_corpus\corpus.jsonl    # 2. linha de base do banco (ANTES de mexer em qualquer coisa)
py benchmarks\corvo_make_sample.py data\corvo_corpus\corpus.jsonl --n 300   # 3. amostra (divisão 70/30 estável por URL)
py benchmarks\corvo_label.py show data\corvo_corpus\corpus.sample.jsonl --from 0 --count 40   # 4. rotule por conteúdo (K/M/D)
py benchmarks\corvo_gate_eval.py data\corvo_corpus\corpus.labels.jsonl            # 5. linha de base de qualidade
py benchmarks\corvo_munin_eval.py --synthetic                          # 6. conheça a bancada de Munin
```

## 5. Prioridade e relógio
`T0 auditar o banco (só com rede)` → `T1 HOT x BUFFER` → `T2 relevância "só mercado"` → `T3 dedup` → `T8 simulação de carga` → `T12 Munin` → `T4 T5 T6 T9 T7`. **Termine bem o que começar.** Registre no relatório o que piorou.

## 6. Entrega (de manhã)
`docs/corvo/RELATORIO_NOITE_<data>.md`, a partir de [`RELATORIO_NOITE_MODELO.md`](RELATORIO_NOITE_MODELO.md). Inclua **sempre** a saída do freio de banco **antes e depois**.

## 7. Pare e escreva no relatório se
um servidor bloquear (403/429) · o freio de banco falhar e você não souber consertar · testes vermelhos que você não entende · algo exigir segredo, deploy, escrita na API ou mudança de contrato · uma permissão for **negada** (**não contorne**).

---

<details>
<summary><b>🧑‍💻 PARA O DONO · roteiro de amanhã (não é para o Codex)</b></summary>

**Ordem sugerida (15 minutos):**
1. **Ler o relatório** `docs/corvo/RELATORIO_NOITE_<data>.md` (resumo de 10 linhas no topo).
2. **Conferir os commits da noite:** `git log --oneline -20` e `git diff --stat origin/hen~N..hen` (nada fora de `engine/`, `docs/corvo/`).
3. **Reproduzir os números** (confiança, não fé):
   ```powershell
   cd C:\projetos\Pulso\engine
   py -m pytest tests/test_intake_gate.py tests/test_oracle_publisher.py tests/test_collect_runner.py tests/test_munin.py tests/test_corvo_bench.py tests/test_corvo_budget.py -q
   py benchmarks\corvo_budget_check.py data\corvo_corpus\corpus.jsonl
   py benchmarks\corvo_gate_eval.py data\corvo_corpus\corpus.labels.jsonl --split eval
   ```
4. **Ver quanto o banco já gastou hoje:**
   ```powershell
   (Invoke-RestMethod https://corvo-api.henriquesouza.workers.dev/api/corvo/feed).budget
   ```
   Deve estar na casa de **centenas de linhas** (limite do dia: 300.000). No painel do Turso: *Usage → Rows written*.
5. **Decidir o merge** do PR #94 (`bash scripts/merge_when_green.sh 94`) só depois de ler o relatório. O `collect.yml` começa a rodar sozinho a cada 10 min depois do merge.

**Freio de emergência (se o banco esquentar):**
| Situação | O que fazer |
|---|---|
| Coleta automática gastando demais | `gh workflow disable "Coleta CORVO"` (religar: `gh workflow enable "Coleta CORVO"`) |
| Quer baixar o teto do dia | `cd apps/worker`, trocar `DAILY_WRITE_LIMIT` no `wrangler.jsonc` (ex.: `50000`) e `npx wrangler deploy` |
| Painel cheio de coisa errada | `POST /api/corvo/purge` com `{"all": true}` e o token de ingestão (apaga notícias e estatísticas, recomeça limpo) |
| Suspeita de vazamento de token | gire `INGEST_TOKEN` e o token do Turso |

**Sinal verde:** freio de banco "dentro dos limites", precisão do HOT ≥ 0,85 e recall ≥ 0,90 **no conjunto lacrado**, e nenhum arquivo fora das pastas permitidas.
</details>
