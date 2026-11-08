# Diário de treino de Hugin e Munin

> Uma linha por **rodada** (medir → ensinar → provar → registrar). É a memória do treino: qualquer pessoa ou agente retoma daqui.
> Métricas do Hugin **ponderadas**, medidas com `corvo_gate_eval.py`; banco com `corvo_budget_check.py`. **Lacrado** = conjunto que ninguém olha durante o ajuste.

## Nível atual
| | Nível | Evidência |
|---|---|---|
| 🧠 Hugin | **H2** (meta: H3) | pré-ajuste v3; auditoria dos 52 gravados: keep 35% → 62% (otimista, ajustado olhando esses itens) |
| 🗃️ Munin | **M2** (meta: M3) | bancada testada (18 testes); cenários simulados básicos (calibrado x exagerado) |

## Placar
| Métrica | Meta | Linha de base (v3) | Última rodada | Conjunto |
|---|---|---|---|---|
| Precisão do HOT | ≥ 0,85 | a medir | | lacrado |
| Recall do keep | ≥ 0,90 | a medir | | lacrado |
| Keep entre as gravadas | ≥ 0,85 | 0,62 (otimista) | | lacrado / auditoria |
| HOT entre os aceitos | ≤ 0,25 | ~0,75 | | corpus |
| Drop gravado | mínimo | a medir | | lacrado |
| Fusões erradas (dedup) | ≤ 2% | a medir | | pares rotulados |
| Cobertura do mapa / acerto do local | ≥ 85% / ≥ 95% | a medir | | aprovados / amostra |
| Linhas de banco/dia (projeção) | ≤ 5.000 | **~490** | | corpus |
| Linhas de banco/dia com 5× volume | ≤ 25.000 | ~710 | | corpus |
| Munin: cenários simulados cobertos | ≥ 6 | 2 | | testes |

## Rodadas
| # | Data | Alavanca (uma por rodada) | Ajuste: antes → depois | **Lacrado**: antes → depois | Banco (linhas/dia) | Resultado | Commit |
|---|---|---|---|---|---|---|---|
| 0 | 2026-11-08 | pré-ajuste v3 (conflito regional, fala de banco central, resumo) | n/d | n/d (ainda sem rótulos) | 486 | mantido | `4df88e6` |
| 1 | | | | | | | |

**Resultado** = `mantido` · `revertido` · `platô` (duas rodadas seguidas sem melhorar o lacrado: parar e registrar o que falta).

## O que falta aprender (preencha ao parar)
-
