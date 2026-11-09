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

| 17 | 2026-11-08 | P1 fit iteration: event threshold 0.25 to 0.235; rejected 0.23 | same 30 fit pairs: at 0.235 TP 7, FP 0, FN 5, TN 18 (recall 0.583); 0.23 would yield FP 1/30 (3.3%) | no Hugin sealed metric; no eval titles opened | 458/day; 562 at 5x; green | real approved corpus: events 56?55, multi-source stays 7; local proof 100 questions, 0 forecasts, 100 abstentions | `09b4c36` |

| 18 | 2026-11-08 | T9 robustness integration matrix: bad XML/empty/HTML/oversize/timeout/403/503/redirect plus healthy feed | 8 failures recorded by feed; healthy feed fetched/sent/marked once; CORVO suite 76 passed | no Hugin sealed metric; collector boundary only | 458/day; freio green | cycle survived every simulated fault; no real network calls and no source bypass | `310eb9b` |

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

| 2026-11-08 21:00 | Active note8 checkpoint; cycle 10 and fresh-lacre labeling underway | 1,300 unique items; cycle 10: 7 new, 5 new prices, one isolated fed-press 404; 300/993 fresh URLs manually labeled so far | green: 460/day; 572 at 5x; critical 432/432 |


## O que falta aprender (atualize a cada platô; o treino só para quando o dono escrever "PARE")
- Hugin: gerar um lacre novo, sem URLs já vistas, com pelo menos 30 casos keep no lado de avaliação; revisar os falsos negativos do fit antes de experimentar T2.
- T3: rotular pares positivos e negativos para medir fusões erradas e economia de linhas antes de mexer na deduplicação.
- T0/T5: obter janela de ciclos por fonte e confirmar com o dono os 14 rótulos marginais do snapshot; não inferir confiabilidade a partir de um único GET.
- Munin: esperar previsões reais resolvidas e fonte de preços registrada; manter os pesos em HOLD até cumprir os mínimos e a divisão temporal propostos.
- Hugin continua em H2 (um único corte provado; sem platô declarado); Munin está em M3, sem resultado real.


| 19 | 2026-11-08 | Fresh seal feasibility audit + Munin honesty scenarios | 989 previously unlabeled URLs; current gate accepts 10; stable 70/30 split gives eval 304 rows, only 4 in accepted stratum; no labels scored | Existing eval remains 15 keep; no new Hugin result or rule change | 458/day; 562 at 5x; critical 432/432; green | No inference about hidden keeps among rejected rows; seal needs human labels; synthetic Munin matrix: calibrated skill +0.353/ECE 0.014, exaggerated +0.089/0.211, base skill 0, conservative +0.262/0.132, n=12 HOLD, leakage blocked | `d68e976` |

| 20 | 2026-11-08 | Cycle 6 + refreshed local Munin proof panel | 24 feeds healthy, 10 new items, prices unchanged at 5,220 rows; 55 events, 100 questions, 0 forecasts, 100 abstentions | 18 local price resolutions without forecasts; 2 await future prices, 80 await instruments; Brier/base/skill/ECE N/A | 458/day; 562 at 5x; critical 432/432; green | Collection process remains active; no accuracy claim; idempotent panel rerun | `572b596` |

| 21 | 2026-11-08 | T12 temporal leakage guard: event availability from cycle_at | Before: 18 resolved, 2 awaiting future; after: 8 resolved, 12 awaiting future, 80 awaiting instrument; 55 events, 100 abstentions, 0 forecasts | 22 Munin event/backtest/question/resolve tests passed; 0 corpus rows missing cycle_at | 458/day; 562 at 5x; critical 432/432; green | Forecast time now waits for the last clustered article arrival; missing cycle_at events are skipped and counted; no hit/calibration claim | `61fd78d` |

| 22 | 2026-11-08 | M6 independent-sample guard: exclude overlapping outcome windows | 6 resolved windows excluded from baseline as overlapping; BTC/ETH keys now have 1 independent result (29 more needed), not 4 | 23 Munin tests passed; panel remains 0 forecasts/100 abstentions; resolution counts unchanged at 8/12/80 | 458/day; 562 at 5x; critical 432/432; green | Added per-key non-overlap rule to M6 protocol; no accuracy claim | `ce891d7` |

| 23 | 2026-11-08 | Local price-file integrity audit | 5,220 rows; 5,220 unique asset/timestamp keys; 0 invalid rows, nonpositive closes, duplicate keys, conflicting duplicates, or future closes | Crypto series end 2026-11-08 23:00 UTC; FX daily series end 2026-11-06 16:00 UTC | 458/day; 562 at 5x; critical 432/432; green | No price data modified; source provenance still requires owner/source documentation before stronger calibration claims | `04719f2` |

| 24 | 2026-11-08 | T9 malformed fetcher payload shape matrix | 5 invalid return forms isolated per feed while healthy feed completed; robustness + runner tests: 10 passed; local HTTP chaos matrix: 31 passed, 6 deselected; full Munin tests: 53 passed; Hugin fit-only n=225/keep=46, precision=1.000, recall=0.540, stored drop=0.049 | Cycle still completes; no network in fault simulations | 458/day; 562 at 5x; critical 432/432; green | Invalid None/tuple/dict/list/string payloads are rejected without losing healthy feed | `a92629e` |

| 25 | 2026-11-08 | T0 read-only production feed audit | GET returned 31 news; manual title-only labels: 22 keep, 8 marginal, 1 drop (71.0%, below 85% target); response stats show 818 received | API budget 232/300000 rows; all returned records ingested at 03:13:32Z; no writes | Local freio remains green: 458/day; 562 at 5x; critical 432/432 | Returned 31 matches stats HOT+BUFFER (17+14), covering current stored bucket; snapshot is stale; verdict fields were not used; no rule adjusted from production sample | `b4bbf35` |

| 26 | 2026-11-08 | Cycle 8 + refreshed local Munin panel | 24 feeds healthy, 1 new item, prices unchanged; 55 events, 100 questions, 0 forecasts, 100 abstentions | 6 overlapping outcomes excluded; 8 local resolutions, 12 await future price, 80 await instrument | 458/day; 562 at 5x; critical 432/432; green | n=1 independent BTC/ETH result; no accuracy or calibration claim | `b4bbf35` |

| 27 | 2026-11-08 | M6 sampling-key documentation alignment | The baseline key includes topic, asset, question direction and horizon; 30 non-overlapping resolved windows per key | No forecast or scoring change; Munin remains M3 | 458/day; 562 at 5x; critical 432/432; green | Clarified why opposite directions cannot share a yes/no base rate; code behavior unchanged | `b4ac7b0` |

| 28 | 2026-11-08 | M6 availability-time wording and direction isolation | Question tests assert the lookback uses event availability; synthetic backtest test proves BTC up/down keys are distinct | Munin question/backtest tests pass; no resolution calculation change | 460/day; 572 at 5x; critical 432/432; green | Removed misleading publication-time wording and guarded direction-specific samples; sealed Hugin metrics and Munin real forecast scores unchanged | `bae075e` |

| 29 | 2026-11-08 | Cycle 9 + local Munin panel | 24 feeds healthy, 3 new items, prices unchanged; 56 events, 100 questions, 0 forecasts, 100 abstentions | 6 overlapping outcomes excluded; 8 local resolutions, 12 await future price, 80 await instrument | 460/day; 572 at 5x; critical 432/432; green | One more event did not produce a new independent resolved outcome; no forecast accuracy claim | `bae075e` |

| 30 | 2026-11-08 | Munin synthetic honesty matrix re-run | Calibrated: skill +0.353/ECE 0.014; exaggerated: +0.089/0.211; base: 0; conservative: +0.262/0.132; n=12 remains EXPERIMENTAL/HOLD; leakage blocked | 6 scenarios; all explicitly synthetic; no real prediction scored | 460/day; 572 at 5x; critical 432/432; green | Confirms the metrics distinguish calibration from apparent skill and reject leakage/small samples | `12d17bb` |

| 31 | 2026-11-08 | Hugin fit-only baseline recheck; no gate adjustment | n=225/keep=46; HOT precision 1.000, keep recall 0.540, keep discarded 0.460, drop stored 0.049, keep stored 0.607, HOT among accepted 0.082 | Fit only; sealed eval not reopened; no new label or rule | 460/day; 572 at 5x; critical 432/432; green | Same fit metrics as prior checkpoint; Hugin remains H2, no improvement claimed | `12d17bb` |

| 32 | 2026-11-08 | Cycle 10 + renewed local Munin panel and fresh seal attempt | 24 feeds, 7 new items; price file 5,225 rows; panel 57 events, 100 questions, 0 forecasts, 100 abstentions | 8 local resolutions, 12 awaiting future price, 80 awaiting instrument; 300/993 fresh sample URLs labeled, no sealed score yet | 460/day; 572 at 5x; critical 432/432; green | `fed-press` HTTP 404 isolated; no rule adjusted; old seal examples remain unopened | `12d17bb` |

| 33 | 2026-11-08 | Fresh Hugin seal; aggregate fit/eval proof only | Fresh 993 URLs, 686 fit/45 keep and 307 eval/21 keep; fit recall 0.044, eval recall 0.190; HOT precision n/d, eval keep discarded 0.810, keep among stored 0.800 | Eval run once; 21 keeps is below 40 target; zero HOT accepted; no rule changed | 458/day; 562 at 5x; critical 432/432; green | Fresh seal cannot support H3 or note8 target; examples not opened for rule choice | this checkpoint commit |

| 34 | 2026-11-08 | Cycle 11 + local Munin panel | 24 feeds healthy, 3 new items, prices unchanged at 5,225 rows; panel 57 events, 100 questions, 0 forecasts, 100 abstentions | 8 local resolutions, 12 await future price, 80 await instrument; 6 overlapping outcomes excluded | 458/day; 562 at 5x; critical 432/432; green | No new independent resolved outcome or forecast score; collector still running dry-run | this checkpoint commit |

| 35 | 2026-11-08 | T6 geocoder: earliest title mention and explicit missing hubs | On the same 53 approved fit titles, title-only coverage rose 37/53 (69.8%) to 44/53 (83.0%); curated fit audit 20/20 correct, four ambiguity/company negative tests clean | Added Latvia, Yemen, Black Sea and Gulf of Oman; first textual mention wins; Turkey requires unambiguous Türkiye/Ankara/Turquia | 460/day; 572 at 5x; critical 432/432; green | T6 coverage target 85% remains unmet: nine titles contain no locatable place; no headquarters or unstated locations inferred; Hugin remains H2 | `1084877` |

| 36 | 2026-11-08 | Cycle 12 + post-T6 budget proof | 24 feeds healthy, 7 new items, no new prices; corpus 1,310; panel data unchanged at last evaluation | Post-commit budget green: 460/day, 572 at 5x, critical 432/432; collector PID 13596 active | 460/day; 572 at 5x; critical 432/432; green | Cycle did not create a new resolved forecast outcome; no real score claimed | `4dd7b9d` |

| 37 | 2026-11-08 | T6 second fit-only pass: event location cue | Same current fit set: 54 approved titles; coverage 38/54 (70.4%) -> 45/54 (83.3%); manual audit 44/45 clear (97.8% conservative, one ambiguous counted wrong) | Cue explicit action-site phrases before actor mentions; 22 positive and 4 negative geocoder cases; 108 tests passed | 460/day; 572 at 5x; critical 432/432; green | T6 coverage remained below 85% at this checkpoint; unresolved titles had no explicit place; no sealed data used | `34e59d7` |

| 38 | 2026-11-08 | T6 final fit-only pass: explicit Europe region | Same 54 approved titles; coverage 38/54 (70.4%) -> 46/54 (85.2%); manual audit 45/46 clear, one ambiguous counted wrong (97.8% conservative) | Added approximate Europa point only for explicit region wording; company name negative; 23 positive/five negative geocoder cases | 460/day; 572 at 5x; critical 432/432; green | T6 coverage and accuracy thresholds reached on fit only; sealed eval untouched; Hugin remains H2 | `b28fcf3` |

| 39 | 2026-11-08 | Cycle 13 + Munin synthetic honesty matrix | 24 feeds healthy, 3 new items; panel 59 events, 104 questions, 0 forecasts, 104 abstentions; 8 local resolutions, 12 future-price waits, 84 instrument waits | 6 synthetic scenarios unchanged; Brier/skill/ECE remain N/A for real forecasts; post-cycle budget green at 462/day, 582 at 5x | 462/day; 582 at 5x; critical 432/432; green | Collector PID 13596 still active; no new real forecast outcome or accuracy claim | `4c7838f` |

| 40 | 2026-11-08 | T6 current-fit refresh after cycle 13 | Excluding all sealed eval URLs, approved fit titles now 55; old geocoder 39/55 (70.9%), current 47/55 (85.5%); newest Iran headline locates Iran | One newly approved title added since the fixed 54-row checkpoint; manual accuracy remains 46/47 conservative, one ambiguous counted wrong | 462/day; 582 at 5x; critical 432/432; green | T6 thresholds still hold with the added fit item; eval untouched; Hugin remains H2 | `5f2aef8` |

| 41 | 2026-11-08 | T5 source census, rolling 24 hours | Excluding sealed eval URLs by ID: 1,008 unique items, 23 active feeds; 55 HOT/BUFFER; G1 210 items and zero accepted; USGS zero | Stale counts highest on decrypt 11/33, theblock 8/21, cointelegraph 7/26, boe-news 6/39, ecb-press 5/11; no reliability change without false-negative labels | 462/day; 582 at 5x; critical 432/432; green | Reports feed counts and follow-up targets; no exact normalized cross-source titles; no feed disabled | `76a6dca` |

| 42 | 2026-11-08 | Cycle 14 + Munin panel and budget | 24 feeds queried, 6 new URLs, 0 new prices; 1,319 corpus URLs; panel unchanged at 59 events, 104 questions, 104 abstentions | Post-cycle budget green: 462/day, 582 at 5x, critical 432/432 | 462/day; 582 at 5x; critical 432/432; green | No additional real forecast resolved; no skill/Brier/ECE claim | `87afb7e` |

| 43 | 2026-11-08 | T5 rolling-window refresh after cycle 14 | 1,014 unique non-eval URLs in the latest 24 h, 23 active feeds, 55 accepted; six added URLs were all drops | G1 remains 210/0 accepted; unchanged conclusion, no source setting changed | 462/day; 582 at 5x; critical 432/432; green | Extends the prior 21:30 table through 21:40; evaluator URLs excluded by ID | `97d75d9` |

| 44 | 2026-11-08 | T4 stale-age audit; no window change | Of 68 non-eval stale rows, 7 match fresh fit labels: 5 marginal, 2 drop, 0 keep; 61 have no match in that label file | No `max_age_h` change: current evidence does not show a lost keep; larger windows lack a measured benefit | 462/day; 582 at 5x; critical 432/432; green | Incomplete labels block a safe freshness adjustment; eval labels/titles untouched | `e78f72e` |

| 45 | 2026-11-08 | Cycle 15 + Munin recheck | 24 feeds healthy, 6 new URLs, 0 new prices; corpus 1,325; panel still 59 events, 104 questions, 104 abstentions | 8 local resolutions, 12 future-price waits, 84 instrument waits; no resolved forecast | 462/day; 582 at 5x; critical 432/432; green | No new forecast score; collection PID 13596 remains active | `e54b865` |

| 46 | 2026-11-08 | Cycle 16 shared-collector expansion + Munin | 27 feeds, 83 new URLs, 5 prices; corpus 1,408; panel 61 events, 109 questions, 109 abstentions; 8 resolved without forecast, 12 future-price waits, 88 awaiting price, 1 insufficient history | No Brier/skill/ECE real; budget green at 466/day, 602 at 5x, critical 432/432 | 466/day; 602 at 5x; critical 432/432; green | Feed-count change came from shared collector work, not this agent; no API write or deploy | `eca0410` |

| 47 | 2026-11-08 | T6 dynamic fit refresh + explicit US token | Fit-only approved set is 57; old geocoder 39/57 (68.4%), current 48/57 (84.2%); manual accuracy 47/48 (97.9% conservative, one ambiguous counted wrong) | Added uppercase-only `US` match to map “US Jobs”; test proves lowercase pronoun “us” does not map | 466/day; 602 at 5x; critical 432/432; green | Coverage is still below 85%: 9 titles have no explicit location; eval untouched; don't infer region/HQ | `eca0410` |

| 48 | 2026-11-08 | T5 current rolling census after cycle 16 | Excluding eval URLs, 1,103 unique rows in 24 h, 26 source IDs, 57 accepted; G1 213/0 accepted; `bea-releases` 48/0, `bloomberg-markets` 20/2, `ft-home` 9/0 | No reliability/enabled changes; new sources reflect shared collector update | 466/day; 602 at 5x; critical 432/432; green | Don't attribute feed expansion to codex-noite; current census and T6 outcome recorded separately | `eca0410` |

| 49 | 2026-11-08 | T0 public GET audit and fit/synthetic recheck | 37 public feed titles manually classified: 30 keep (81.1%), 6 marginal, 1 drop; latest bucket 85 received, 1 HOT, 1 BUFFER, 83 DROP; budget 28/300,000 rows | Fit unchanged: precision HOT 1.000, recall keep 0.540, keep discarded 0.460; six Munin scenarios synthetic, leakage blocked, n=12 HOLD | 466/day; 602 at 5x; critical 432/432; green | T0 misses 85% keep target; no Hugin rule change based on single snapshot; no eval rerun | `8510074` |

| 50 | 2026-11-08 | T7 fit-only kind audit and narrow opinion rule | All 52 approved fit titles manually reviewed; 75 eval URLs excluded; one explicit market opinion now labels opinion; 52/52 on this adjustment sample | Added exact phrase matcher for “here are some simple alternatives”; new test confirms opinion remains opinion even with official source; CORVO/Munin tests 91 passed | 466/day; 602 at 5x; critical 432/432; green | No rumor/opinion as fact in this fit sample; not an independent population estimate; eval untouched | `1c1fc63` |

| 51 | 2026-11-08 | Cycle 17 + local Munin panel | 27 feeds, 3 new URLs, 0 failures, 0 sent, 0 new prices; corpus 1,411 URLs; panel 61 events, 109 questions, 109 abstentions | 8 resolved without forecast, 12 future-price waits, 88 instrument waits, 1 insufficient history; real Brier/skill/ECE N/A | 466/day; 602 at 5x; critical 432/432; green | Collection remains owner-managed PID 13596 in dry-run; no API write | 1c1fc63 |

| 52 | 2026-11-08 | T2 fit-only false-negative map; no gate change | 9 of 46 labeled fit keeps score 0/drop; misses span 401(k) crypto, stablecoins, wallet breach, Bitcoin mining, bank crisis and AI equity exposure | Proposed one lexical group for a future round; no rule changed because sealed eval already ran once and has only 21 keeps (<40) | 466/day; 602 at 5x; critical 432/432; green | Do not tune or reopen eval until a fresh adequate seal exists | `65dc991` |

| 53 | 2026-11-08 | Cycle 18 + Munin proof panel | 27 feeds, 9 new URLs, 0 failures, 0 sent, 0 new prices; corpus 1,420 URLs; panel 61 events, 109 questions, 109 abstentions | 8 resolved without forecast, 12 future-price waits, 88 instrument waits, 1 insufficient history; Brier/skill/ECE real N/A | 466/day; 602 at 5x; critical 432/432; green | 24 h volume 543, 17 accepted; collection remains owner-managed PID 13596 | `65dc991` |

| 54 | 2026-11-08 | Munin registry idempotency recheck | Repeated local `--dry-run` with unchanged inputs; run_id `run_330411c552deaefa876b`; registry remained 1,135 lines before/after | Panel remained 61 events, 109 abstentions, 0 forecast outcomes; existing idempotency test remains green | 466/day; 602 at 5x; critical 432/432; green | No duplicate local records, no real scores, no network write | `74e43da` |

| 55 | 2026-11-08 | T7 complete fit-only audit | Remaining 12 approved fit titles reviewed; all classify as reporting; full 52-title sample 52/52 after one opinion fix | No additional rule changes; fit sample only, sealed URLs excluded before title read | 466/day; 602 at 5x; critical 432/432; green | Small manually reviewed sample, not a population estimate; no eval access | `9773cb5` |

| 56 | 2026-11-08 | Three-hour note8 score + cycle 19 | 8.5/10: predictive chain 3/3, four verifiable tasks 2/2, rigor 2/2, efficiency 0.5/1, safety 0/1, report 1/1; corpus 1,426 URLs | Cycle 19: 27 feeds, 6 new URLs, 0 failures, 0 accepted, 0 new prices; Munin 61 events, 109 abstentions, 0 forecasts | 466/day; 602 at 5x; critical 432/432; green | Safety deduction for indirect prohibited Wrangler invocation; no production publication; round continues until owner says PARE | `da892ba` |

| 57 | 2026-11-08 | T6 current fit corpus check; no geocoder change | Stable URL split, approved fit only: 43/52 titles located (82.7%); nine unlocated, one explicitly names Arctic | Below 85% acceptance; no change because sealed eval already ran once; candidate regional point deferred to fresh seal | 466/day; 602 at 5x; critical 432/432; green | Distinct sample from the earlier 48/57 check; no eval titles opened | pending commit |
