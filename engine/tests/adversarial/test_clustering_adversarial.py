"""RT-008/clustering: métricas quantitativas com verdade de terreno. Os números são a LINHA DE BASE MEDIDA (regressão): não são desempenho real.

Limitações conhecidas do V1 que este corpus expõe (e que NÃO foram escondidas): relatos do mesmo acontecimento com redações muito diferentes
quase nunca se juntam (false_split alto), e modelos de título parecidos de acontecimentos distintos NO MESMO ESTADO se juntam (blackout em
São Paulo x Campinas) ou na mesma janela de 12 h (dois acidentes na mesma rodovia).
"""
from datetime import timedelta

from pulso_engine.pipeline import assign_event_ids
from pulso_engine.processing.cluster_eval import drift_and_resurrection, materialize_id, pair_metrics
from pulso_engine.processing.cluster_refine import refine_clusters
from pulso_engine.processing.clustering import cluster_signals
from tests.adversarial.cluster_corpus import corpus

SIGS, TRUTH, KINDS = corpus()


def v1():
    return pair_metrics(cluster_signals(SIGS), TRUTH, KINDS)


def refined():
    return pair_metrics(refine_clusters(cluster_signals(SIGS)), TRUTH, KINDS)


def test_v1_baseline_is_recorded_and_must_not_get_worse():
    m = v1()
    assert m["items"] == 54 and m["true_events"] == 9
    assert m["false_merge_rate"] <= 0.0093 and m["false_split_rate"] <= 0.9556 and m["purity"] >= 0.7778
    # as junções erradas do V1 são de dois tipos, ambos documentados
    assert set(m["false_merge_kinds"]) <= {"related_distinct", "cross_location"}


def test_cross_state_or_cross_day_events_are_never_merged_by_v1():
    kinds = v1()["false_merge_kinds"]
    assert "cross_time" not in kinds  # mesmo lugar em outro dia (> janela de 12 h): nunca junta
    lab = {s.hash: i for i, c in enumerate(cluster_signals(SIGS)) for s in c.signals}
    assert not any(lab[a.hash] == lab[b.hash] for a in SIGS for b in SIGS if TRUTH[a.hash] == "flood_bh" and TRUTH[b.hash] == "flood_recife")  # PE x MG


def test_refinement_reduces_false_splits_within_a_bounded_false_merge_budget():
    a, b = v1(), refined()
    assert b["false_split_rate"] < a["false_split_rate"] - 0.2  # ganho real medido
    assert b["false_merge_rate"] <= 0.02  # teto de falso merge: se estourar, o refino NÃO pode ser promovido
    assert b["purity"] >= a["purity"]
    assert "cross_time" not in b["false_merge_kinds"]


def test_known_limitation_is_documented_not_hidden():
    kinds = refined()["false_merge_kinds"]
    assert kinds.get("cross_location", 0) > 0 or v1()["false_merge_kinds"].get("cross_location", 0) > 0  # modelos iguais, lugares diferentes do MESMO estado


def rounds():
    ordered = sorted(SIGS, key=lambda s: s.timestamp)
    return [ordered[i:i + 9] for i in range(0, len(ordered), 9)]


def test_id_drift_and_resurrection_under_incremental_arrival():
    r = drift_and_resurrection(rounds(), TRUTH, cluster_signals, assign_event_ids)
    assert r["events"] == 9 and r["resurrections"] == 0  # um id que sumiu nunca volta
    assert r["events_fragmented"] >= 1 and r["id_losses"] >= 0  # fragmentação e perdas de id são MEDIDAS (relatório de maturidade)


def test_old_event_does_not_resurrect_after_the_window():
    """O mesmo lugar/assunto 26 h depois é OUTRO acontecimento (não ressuscita o id antigo)."""
    clusters = cluster_signals(SIGS)
    ids = assign_event_ids(clusters, {})
    by_event = {}
    for c, eid in zip(clusters, ids):
        for s in c.signals:
            by_event.setdefault(TRUTH[s.hash], set()).add(materialize_id(c, eid))
    assert not (by_event["flood_bh"] & by_event["flood_bh_next_day"])
