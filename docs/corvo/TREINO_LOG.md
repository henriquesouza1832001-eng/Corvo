# Diário de treino de Hugin e Munin

> Uma linha por **rodada** (medir → ensinar → provar → registrar). É a memória do treino: qualquer pessoa ou agente retoma daqui.
> Métricas do Hugin **ponderadas**, medidas com `corvo_gate_eval.py`; banco com `corvo_budget_check.py`. **Lacrado** = conjunto que ninguém olha durante o ajuste.

## Nível atual
| | Nível | Evidência |
|---|---|---|
| 🧠 Hugin | **H2** (meta: H3) | T1: precisão HOT lacrada 1,000 e HOT entre aceitos 0,083; recall 0,800 e keep entre gravadas 0,583 ainda abaixo das metas, com só 15 keep no lacre |
| 🗃️ Munin | **M3** (meta: M4) | 6 cenários sintéticos e guardas de pouca amostra/vazamento testados; nenhuma previsão real publicada ou avaliada |

## Placar
| Métrica | Meta | Linha de base (v3) | Última rodada | Conjunto |
|---|---|---|---|---|
| Precisão do HOT | ≥ 0,85 | 0,632 | 1,000 | lacrado (2 HOT, 15 keep; instável) |
| Recall do keep | ≥ 0,90 | 0,800 | 0,800 | lacrado (15 keep; instável) |
| Keep entre as gravadas | ≥ 0,85 | 0,583 | 0,583 | lacrado / auditoria |
| HOT entre os aceitos | ≤ 0,25 | 0,792 | 0,083 | lacrado |
| Drop gravado | mínimo | 0,125 | 0,125 | lacrado |
| Fusões erradas (dedup) | ≤ 2% | a medir | | pares rotulados |
| Cobertura do mapa / acerto do local | ≥ 85% / ≥ 95% | a medir | | aprovados / amostra |
| Linhas de banco/dia (projeção) | ≤ 5.000 | **484** | 484 | corpus; normal |
| Linhas de banco/dia com 5× volume | ≤ 25.000 | 692 | 692 | corpus; normal |
| Munin: cenários simulados cobertos | ≥ 6 | 2 | 6 | sintético/testes |

## Rodadas
| # | Data | Alavanca (uma por rodada) | Ajuste: antes → depois | **Lacrado**: antes → depois | Banco (linhas/dia) | Resultado | Commit |
|---|---|---|---|---|---|---|---|
| 0 | 2026-11-08 | pré-ajuste v3 (conflito regional, fala de banco central, resumo) | n/d | n/d (ainda sem rótulos) | 486 | mantido | `4df88e6` |
| 1 | 2026-11-08 | T1: corte HOT 0,75/0,85/0,95 → 0,91/0,95/0,95 | fit: P_HOT 0,617→1,000; R_keep 0,540→0,540; keep gravado 0,607→0,607; HOT 0,770→0,082 | lacrado: P_HOT 0,632→1,000; R_keep 0,800→0,800; keep gravado 0,583→0,583; HOT 0,792→0,083 | 484 (5×: 692) | mantido; lacre tem 75 itens e só 15 keep, métricas instáveis; H3 não atingido | `e10d66c` |
| 2 | 2026-11-08 | T8: simulação de orçamento nas três pressões | freio anterior: só normal 484/692 linhas por dia (1×/5×) | n/a (sem ajuste Hugin) | normal 484/692; economia 480/672; crítico 432/432; todos verdes | concluído; nenhuma pressão estoura os limites | `b1c197e` |
| 3 | 2026-11-08 | T12: cenários e invariantes de Munin | 2 cenários (calibrado/exagerado) → 6 (inclui base, conservador, n pequeno e vazamento) | n/a (dados só sintéticos) | n/a | M3 atingido; nenhum acerto real alegado | `61961de` |

| 4 | 2026-11-08 | T2: BUFFER cutoff normal 0.50 to candidate 0.45 (simulation; not applied) | fit: recall_keep 0.176 to 0.471; keep_stored 0.375 to 0.533; drop_stored 0.125 to 0.133 | sealed: recall_keep 0 to 0.571; keep_stored 0 to 0.571; drop_stored 0 to 0; 63 items, only 7 keep | 484/692 | not promoted: sealed set unstable and fit worsened drop_stored; collect another sealed set | — |
| 5 | 2026-11-08 | T12/M6: operational learning protocol (temporal walk-forward, BH q=0.05, n>=30 independent events) | 6 synthetic scenarios rerun; no real forecast outcomes | n/a (no real outcomes) | n/a | protocol clarified; M3 retained, no empirical M4 claim | — |
| 6 | 2026-11-08 | T0: read-only structural audit of local corpus | 906 rows, 904 unique URLs, 2 duplicate rows, 23 sources; current-title gate accepts 86 (7 HOT) | existing fit labels only: recall_keep 0.540; keep_stored 0.607; drop_stored 0.049 | 486/702 | partial: no production/remote DB read; no sealed titles opened | — |
| 7 | 2026-11-08 | T12/Munin: clarify baseline interval as normal approximation to Beta posterior | metrics unchanged; six synthetic scenarios still pass; no real forecasts | n/a | n/a | documentation corrected; M3 retained; interval coverage still needs data validation | — |
| 8 | 2026-11-08 | T3: pair-candidate availability audit on future-only titles | 173 items; 2 cross-source pairs Jaccard>=0.40; 0 at current 0.70; no pairs labeled | n/a (insufficient pair sample; no change) | 476/652 | hold dedup threshold; gather more cross-source pairs | — |

| 9 | 2026-11-08 | P1 Munin events: conservative 0.30 title overlap; 48h, same topic, complete-link | fit-only challenge: 30 labeled pairs; TP 4, FP 0, FN 8, TN 18 (precision 1.00; recall 0.33) | Hugin sealed n/a (Munin event identity) | 458/day; baseline unchanged | implemented; false merges 0/30 (challenge set, not population estimate); conservative recall remains weak | `a5afa14` |

| 10 | 2026-11-08 | Closed questions + local price resolution rule; exact-symbol routing, 30 prior horizon returns, market-closure annulment | unit tests: 14 passed across event/questions/resolve; synthetic fixture only in tests | no Hugin sealed metric (Munin rules) | baseline unchanged at 458/day | missing/ambiguous prices and unfinished horizons abstain; no market outcome inferred in this block | `08c6a40` |

| 11 | 2026-11-08 | Local walk-forward chain + append-only forecast registry + proof panel | real local corpus/prices: 58 events, 106 questions, 0 forecasts (all n<30), 106 abstentions; 18 resolved outcomes, 2 future-price waits, 86 missing instruments; Brier/base/skill/ECE N/A; open keys report events needed to n=30 | no Hugin sealed metric (Munin backtest) | 458/day; green | no accuracy claim; 18 outcomes are real local resolutions, none had a forecast; registry remains local/untracked | `1112aa9` |

| 12 | 2026-11-08 | T9 collection robustness: reject malformed fetcher payload per source | bad feed returning `None` plus healthy feed: failed source recorded; valid item fetched, sent, and marked once; tests: 5 passed with existing runner tests | no Hugin sealed metric (collection boundary only) | baseline unchanged; budget checked before commit | malformed adapter output is isolated without dropping healthy feeds; no Hugin gate change | `ab2a42c` |

| 13 | 2026-11-08 | Nota8 checkpoint: aggregate Hugin evaluation, no gate adjustment | fit n=225/keep=46; HOT precision 1.000, keep recall 0.540, stored keep 0.607, stored drop 0.049; eval n=75/keep=15; 1.000, 0.800, 0.583, 0.125 respectively (same before/after) | evaluated once, aggregate only; no eval examples opened for rule choice; no new seal (15 eval keep < 40 target) | 458/day; 562 at 5x; green | Hugin H2 unchanged; Munin M3; report checkpoint while external collection continues | ? |

| 14 | 2026-11-08 | Note8 acceptance follow-up: market closure, official-source confirmation, and full proof metrics | FX weekend-window annulment; local feed catalog supplies official-source IDs; registry records source count, confirmation, and resolution rules; panel prints Brier/base/skill/ECE and remaining events per key; targeted tests 18 passed | Hugin sealed unchanged; no eval examples opened | 458/day; freio checked before commit | dashboard metrics remain N/A with zero forecast outcomes; no calibration or success claim | `c98c52d` |

| 15 | 2026-11-08 | Full engine verification after note8 | 1,098 passed, 6 xfailed, 6 failed in `test_failure_injection.py` loopback-name cases | no sealed Hugin change | 458/day; freio green | failures surfaced in untouched `safe_http.py` outside allowed scope; recorded for owner/red-team follow-up | `e06e2d4` |

| 16 | 2026-11-08 | P1 fit iteration: event title threshold 0.30 to 0.25 | same 30 fit-only labeled pairs: TP 4?5, FP 0?0, FN 8?7, TN 18; false merges 0/30; recall 0.333?0.417; directed suite 75 passed | no Hugin sealed metric; Munin event grouping only | 458/day; 562 at 5x; green | real approved corpus: events 58?56, multi-source 5?7; added positive pairs without challenge false merges; low recall remains | `715751a` |

| 17 | 2026-11-08 | P1 fit iteration: event threshold 0.25 to 0.235; rejected 0.23 | same 30 fit pairs: at 0.235 TP 7, FP 0, FN 5, TN 18 (recall 0.583); 0.23 would yield FP 1/30 (3.3%) | no Hugin sealed metric; no eval titles opened | 458/day; 562 at 5x; green | real approved corpus: events 56?55, multi-source stays 7; local proof 100 questions, 0 forecasts, 100 abstentions | pending |

**Resultado** = `mantido` · `revertido` · `platô` (duas rodadas seguidas sem melhorar o lacrado: **trocar de alavanca ou de tarefa e registrar o que falta**; o treino só para quando o dono pedir).

## Batimentos (uma linha por hora; é assim que o dono vê que o treino não parou)
| Hora | Rodada | Fazendo agora | Corpus (itens únicos) | Freio de banco |
|---|---|---|---|---|
| 2026-11-08 11:13 | continuous collection + T2 proof; 0.45 cutoff not applied | 1,185 unique items (scratch corpus) | green: 484/day; 692 at 5x |
| 2026-11-08 11:53 | collection cycle 7 + local T0 audit; M6 safeguards recorded | 1,229 unique items (scratch corpus); 904 official local URLs | green: scratch 484/day; 692 at 5x; official local 486/day; 702 at 5x |
| 2026-11-08 12:53 | collection cycle 13 + budget checkpoint; Munin interval approximation documented | 1,289 unique items (scratch corpus) | green: normal/economy 480/day; 672 at 5x; critical 432/432 |
| 2026-11-08 13:53 | collection cycle 19 + T3 pair-availability audit | 1,336 unique items (scratch corpus) | green: normal/economy 476/day; 652 at 5x; critical 432/432 |
| 2026-11-08 14:53 | continuous collection, cycle 25; all 24 feeds healthy | 1,387 unique items (scratch corpus) | green: normal/economy 474/day; 642 at 5x; critical 432/432 |
| 2026-11-08 15:53 | continuous collection, cycle 31; all 24 feeds healthy | 1,439 unique items (scratch corpus) | green: normal/economy 470/day; 622 at 5x; critical 432/432 |
| 2026-11-08 16:53 | continuous collection, cycle 37; all 24 feeds healthy | 1,471 unique items (scratch corpus) | green: normal/economy 468/day; 612 at 5x; critical 432/432 |
| 2026-11-08 17:42 | owner `PARE`; stopped after cycle 41 at 17:33 | 1,500 unique items (scratch corpus) | green: normal/economy 470/day; 622 at 5x; critical 432/432 |
| 2026-11-08 18:10 | resumed collection cycles 42–44; stopped at owner `PARE` | 1,514 unique items (scratch corpus); +14 since 17:42 | green: normal/economy 470/day; 622 at 5x; critical 432/432 |
| 2026-11-08 18:31 | resumed cycles 45–46; owner `PARE`, stopped after cycle 46 | 1,528 unique items (scratch corpus); +14 since 18:10 | green: normal/economy 470/day; 622 at 5x; critical 432/432 |

| 2026-11-08 19:54 | note8 Munin event-to-price chain + T9 robustness; external collection cycles 1-3 still active | 1,265 unique items (local corpus); 24 feeds queried, 1 HTTP 404 isolated | green: normal/economy 458/day; 562 at 5x; critical 432/432 |

| 2026-11-08 20:00 | nota8 acceptance follow-up: market-closure cancellation + full scoring panel; external collection cycle 4 active | 1,267 unique items (local corpus); 24 feeds, 2 new items; prices 5,220 rows | green baseline: normal/economy 458/day; 562 at 5x; critical 432/432 |

| 2026-11-08 20:10 | P1 fit-only event threshold 0.25 proof + refreshed Munin panel; external collection cycle 5 active | 1,278 unique items; cycle 5: 11 received, 24 feeds healthy; prices 5,220 rows | green: normal/economy 458/day; 562 at 5x; critical 432/432 |

## O que falta aprender (atualize a cada platô; o treino só para quando o dono escrever "PARE")
- Hugin: gerar um lacre novo, sem URLs já vistas, com pelo menos 30 casos keep no lado de avaliação; revisar os falsos negativos do fit antes de experimentar T2.
- T3: rotular pares positivos e negativos para medir fusões erradas e economia de linhas antes de mexer na deduplicação.
- T0/T5: obter janela de ciclos por fonte e confirmar com o dono os 14 rótulos marginais do snapshot; não inferir confiabilidade a partir de um único GET.
- Munin: esperar previsões reais resolvidas e fonte de preços registrada; manter os pesos em HOLD até cumprir os mínimos e a divisão temporal propostos.
- Hugin continua em H2 (um único corte provado; sem platô declarado); Munin está em M3, sem resultado real.
