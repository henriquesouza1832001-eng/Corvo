# Recon — campanha de inteligência (Claude A)

> Escrito ANTES de editar, em 2026-10-04, a partir do código e dos documentos do repositório. Só contém fatos medidos ou lidos; onde não há número, está escrito. `HEAD` = `4e85be1`; Engine: **598 testes passando** (`cd engine && py -m pytest -q`, ~30–60 s).

## 1. Fontes lidas
`AGENTS.md`, `.agents/` (quadro de coordenação), `docs/maturity/PLATFORM_MATURITY.md`, `docs/reliability/BACKEND_TOTAL_RED_TEAM.md`, `docs/engineering/{FALTA_FAZER,FORECAST_V2_ENGINEERING,ENGINE_V2_PLAN,RELIABILITY_LAB}.md`, `docs/CURRENT_ENGINE_STATE.md`, `docs/SCORING.md`, `engine/tests/reliability/*`, `engine/tests/golden/*`.

## 2. Inventário de módulos (onde mexer)
| Área | Arquivo(s) | Estado |
|---|---|---|
| Sentinela | `research/sentinel.py` (gatilho, estado, dedup de investigações), `radar.py` | em produção em SHADOW (`SENTINEL`) |
| Proveniência / cópias | `research/validator.py::_origins` (Jaccard de tokens do título ≥ 0,8), `processing/normalizer.py` (URL canônica, hash do título), `scoring/confidence_v2.py` | só o título decide "mesma origem"; **sem** cascatas medidas (RT-008) |
| Clustering | `processing/clustering.py` (Jaccard título + janela 12 h + trava de UF), `processing/cluster_refine.py` (flag `CLUSTER_REFINE`, OFF), `intelligence/event_fingerprint.py` | sem métricas de false merge/split (RT-008) |
| Geo | `processing/geo.py` (V1, em produção), `processing/geo_v2.py` (flag `GEO_V2`, OFF), `tests/golden/geo_cases.json` (14 casos) | corpus editorial pequeno |
| Baseline | `baseline.py` (EWMA + `seasonal_baseline`: dia da semana×hora → hora → INSUFICIENTE), `intelligence/seasonal` embutido, `intelligence/context_engine.py` (feriado = domingo; flag `CONTEXT_ENGINE`, OFF) | **sem** fallback hierárquico por escopo (cidade→UF→país) e sem metadados de fallback |
| Anomalia | `anomaly.py`, `intelligence/anomaly_v2.py` (mediana/MAD, score separado de confiança) | V2 OFF |
| Confiança / severidade | `scoring/confidence.py` (V1, produção), `confidence_v2.py`, `severity_v2.py` (OFF) | V2 ainda não consome cobertura/frescor |
| Frescor / cobertura | `source_freshness.py` (FRESH/STALE/EMPTY/QUIET/UNKNOWN; `SOURCE_FRESHNESS` SHADOW), `forecast_v2_features.sensor_coverage` | **não propagado** para Sentinela, confiança nem anomalia |
| Contradição | `research/validator.py::find_contradictions` (4 pares de afirmações) → `DISPUTED` | estados `SUPPORTED/UNCONFIRMED/DISPUTED` **não existem** como saída explícita; sem "negação oficial" |
| Forecast | `forecast.py` (V1), `forecast_v2.py` (shadow), `forecast_v2_features.py`, `forecast_v2_model.py`, `calibration.py`, `forecast_scopes.py`, `validation/*` (Codex) | `INSUFFICIENT_DATA`/abstenção existem; **não há comparação** base-rate × sazonal × anomalia × V1 × V2 |
| Valor de sensor | `intelligence/sensor_reliability.py` (Wilson) | sem framework de valor marginal por família |

## 3. Flags (estado efetivo por padrão)
Ligadas em SHADOW: `HISTORY_OBSERVATIONS`, `FORECAST_REGISTRY`, `SENTINEL`, `SOURCE_FRESHNESS`. **Todas as demais OFF**: `SEASONAL_BASELINE_V2`, `ANOMALY_V2`, `CLUSTER_REFINE`, `SEMANTIC_CLUSTERING`, `GEO_V2`, `CONFIDENCE_V2`, `SEVERITY_V2`, `PULSE_V2`, `NATIONAL_PULSE_V2`, `DRIVER_VALIDATOR`, `EVENT_ESCALATION`, `FORECAST_V2_SHADOW`, `CONTEXT_ENGINE`. Esta campanha **não liga nenhuma**.

## 4. RT-003 reproduzido (antes de qualquer edição)
`engine/tests/reliability/test_sentinel_normal_day.py` passa **caracterizando o defeito**: 30 sinais/15 min com baseline de 120/h (exatamente o normal), três classes de fonte (NEWS_HIGH, NEWS_REGIONAL, SOCIAL), anomalia 0 em todos os candidatos ⇒ o Sentinela abre **2 investigações** (`BR/WEATHER` e `UF:MG/WEATHER`), `reasons = ("3 tipos de fonte",)`.
**Causa-raiz (lida em `sentinel.should_investigate`):** o gatilho `source_type_count >= 3 and signal_count >= 3` é independente da anomalia; "diversidade de tipos" dispara mesmo com atividade esperada. O mesmo vale para `official_signal`: qualquer sinal de classe OFFICIAL (inclusive boletim de rotina de agência) abre investigação. Não é questão de limiar, é que o gatilho mede atividade/diversidade bruta, não **inesperado**. O teste não será alterado para passar: a expectativa dele é que mude quando o defeito for corrigido, como o próprio docstring diz.

## 5. Lacunas confirmadas (vão ser fechadas ou marcadas)
1. Gatilho sem noção de inesperado (RT-003).
2. Proveniência: a regra "mesma origem" é só Jaccard de título; reformulação, agência, blog→jornal, social→social, tracking de URL e reaparecimento de notícia antiga **não são medidos** (RT-008).
3. Clustering sem corpus quantitativo (false merge/split/drift/resurrection).
4. Geo: corpus de 14 manchetes; sem `false_precision_rate` por tipo de ambiguidade.
5. Baseline sem fallback hierárquico explícito e sem metadados (`fallback_level`, `sample_size`).
6. Contexto limitado a feriado (flag OFF); sem expectedness (rush, fim de semana, evento programado).
7. Cobertura/frescor não chegam à confiança, à anomalia nem ao Sentinela.
8. Contradição sem estados explícitos nem negação oficial.
9. Sem comparação formal de previsores nem comparação com taxa-base/sazonal.
10. Sem benchmark de desempenho (100–100k) e sem fuzz temporal por campo.

## 6. Limites declarados
- Produção: 20 previsões resolvidas, **0 positivos** (medição do Codex, 2026-10-03). Qualquer métrica preditiva desta campanha é `INSUFFICIENT_DATA`; nada é calibrado ou ajustado com esse N.
- Todo corpus desta campanha é **sintético ou editorial**: prova mecânica e propriedades, **não** desempenho real (marcado `HARNESS_VERIFIED`, nunca `PRODUCTION_VERIFIED`).
- Sem embeddings/LLM: só se uma medição provar que regras determinísticas não bastam.
