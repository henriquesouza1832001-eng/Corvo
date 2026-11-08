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

## O que falta aprender (atualize a cada platô; o treino só para quando o dono escrever "PARE")
- Hugin: gerar um lacre novo, sem URLs já vistas, com pelo menos 30 casos keep no lado de avaliação; revisar os falsos negativos do fit antes de experimentar T2.
- T3: rotular pares positivos e negativos para medir fusões erradas e economia de linhas antes de mexer na deduplicação.
- T0/T5: obter janela de ciclos por fonte e confirmar com o dono os 14 rótulos marginais do snapshot; não inferir confiabilidade a partir de um único GET.
- Munin: esperar previsões reais resolvidas e fonte de preços registrada; manter os pesos em HOLD até cumprir os mínimos e a divisão temporal propostos.
- Hugin continua em H2 (um único corte provado; sem platô declarado); Munin está em M3, sem resultado real.
