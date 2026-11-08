# Diário de treino de Hugin e Munin

> Uma linha por **rodada** (medir → ensinar → provar → registrar). É a memória do treino: qualquer pessoa ou agente retoma daqui.
> Métricas do Hugin **ponderadas**, medidas com `corvo_gate_eval.py`; banco com `corvo_budget_check.py`. **Lacrado** = conjunto que ninguém olha durante o ajuste.

## Nível atual
| | Nível | Evidência |
|---|---|---|
| 🧠 Hugin | **H2** (meta: H3) | T1 elevou precisão HOT lacrada para 1,000 e baixou HOT entre aceitos para 0,083; recall 0,800 e keep entre gravadas 0,583 ainda abaixo das metas, com só 15 keep no lacre |
| 🗃️ Munin | **M2** (meta: M3) | bancada testada (18 testes); cenários simulados básicos (calibrado x exagerado) |

## Placar
| Métrica | Meta | Linha de base (v3) | Última rodada | Conjunto |
|---|---|---|---|---|
| Precisão do HOT | ≥ 0,85 | a medir | | lacrado |
| Recall do keep | ≥ 0,90 | a medir | | lacrado |
| Keep entre as gravadas | ≥ 0,85 | 0,62 (otimista) | | lacrado / auditoria |
| HOT entre os aceitos | ≤ 0,25 | ~0,75 | 0,083 | lacrado |
| Drop gravado | mínimo | a medir | | lacrado |
| Fusões erradas (dedup) | ≤ 2% | a medir | | pares rotulados |
| Cobertura do mapa / acerto do local | ≥ 85% / ≥ 95% | a medir | | aprovados / amostra |
| Linhas de banco/dia (projeção) | ≤ 5.000 | **~490** | 484 | corpus |
| Linhas de banco/dia com 5× volume | ≤ 25.000 | ~710 | 692 | corpus |
| Munin: cenários simulados cobertos | ≥ 6 | 2 | | testes |

## Rodadas
| # | Data | Alavanca (uma por rodada) | Ajuste: antes → depois | **Lacrado**: antes → depois | Banco (linhas/dia) | Resultado | Commit |
|---|---|---|---|---|---|---|---|
| 0 | 2026-11-08 | pré-ajuste v3 (conflito regional, fala de banco central, resumo) | n/d | n/d (ainda sem rótulos) | 486 | mantido | `4df88e6` |
| 1 | 2026-11-08 | T1: corte HOT 0,75/0,85/0,95 → 0,91/0,95/0,95 | fit: P_HOT 0,617→1,000; R_keep 0,540→0,540; keep gravado 0,607→0,607; HOT 0,770→0,082 | lacrado: P_HOT 0,632→1,000; R_keep 0,800→0,800; keep gravado 0,583→0,583; HOT 0,792→0,083 | 484 (5×: 692) | mantido; lacre tem 75 itens e só 15 keep, métricas instáveis; H3 não atingido | `e10d66c` |
| 2 | 2026-11-08 | T8: simulação de orçamento nas três pressões | freio anterior: só normal 484/692 linhas por dia (1×/5×) | n/a (sem ajuste Hugin) | normal 484/692; economia 480/672; crítico 432/432; todos verdes | concluído; nenhuma pressão estoura os limites | `pendente` |

**Resultado** = `mantido` · `revertido` · `platô` (duas rodadas seguidas sem melhorar o lacrado: parar e registrar o que falta).

## O que falta aprender (preencha ao parar)
-
