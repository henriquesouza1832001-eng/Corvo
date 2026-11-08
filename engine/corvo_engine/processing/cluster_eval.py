"""Avaliação quantitativa de clusterização com verdade de terreno (cada sinal traz `truth` = id do acontecimento real).

Métricas por PARES (todos os pares de sinais): `false_merge_rate` = pares de acontecimentos DIFERENTES que ficaram juntos / pares de
acontecimentos diferentes; `false_split_rate` = pares do MESMO acontecimento que ficaram separados / pares do mesmo acontecimento;
`purity` = soma do rótulo majoritário de cada cluster / N. Falsos merges são classificados por tipo (outro lugar, outro dia, assunto
relacionado). `drift` e `resurrection` usam a chegada incremental (rodadas) com o mesmo mecanismo de ids estáveis do pipeline.
Corpus sintético: prova mecânica, não desempenho real.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from itertools import combinations

from ..models import Signal


def _labels(clusters: list, truth: dict[str, str]) -> dict[str, int]:
    out = {}
    for ci, c in enumerate(clusters):
        for s in c.signals:
            out[s.hash] = ci
    return out


def materialize_id(cluster, event_id: str | None) -> str:
    """O id que `events.build_event` daria: o herdado ou "ev-" + hash do sinal mais antigo do grupo (None = história nova)."""
    if event_id:
        return event_id
    first = min(cluster.signals, key=lambda s: s.timestamp)
    return "ev-" + hashlib.sha1(first.hash.encode()).hexdigest()[:12]


def pair_metrics(clusters: list, truth: dict[str, str], kinds: dict[tuple[str, str], str] | None = None) -> dict:
    lab = _labels(clusters, truth)
    hashes = sorted(truth)
    same_t = diff_t = fm = fs = 0
    fm_kinds: Counter[str] = Counter()
    for a, b in combinations(hashes, 2):
        together = lab[a] == lab[b]
        if truth[a] == truth[b]:
            same_t += 1
            fs += not together
        else:
            diff_t += 1
            if together:
                fm += 1
                fm_kinds[(kinds or {}).get(tuple(sorted((truth[a], truth[b]))), "other")] += 1
    by_cluster: dict[int, Counter] = {}
    for h in hashes:
        by_cluster.setdefault(lab[h], Counter())[truth[h]] += 1
    purity = sum(max(c.values()) for c in by_cluster.values()) / len(hashes) if hashes else 0.0
    return {"items": len(hashes), "clusters": len(clusters), "true_events": len(set(truth.values())),
            "false_merge_rate": round(fm / diff_t, 5) if diff_t else 0.0, "false_split_rate": round(fs / same_t, 5) if same_t else 0.0,
            "false_merges": fm, "false_splits": fs, "false_merge_kinds": dict(fm_kinds), "purity": round(purity, 4)}


def drift_and_resurrection(rounds: list[list[Signal]], truth: dict[str, str], cluster_fn, assign_fn) -> dict:
    """Chegada incremental: a cada rodada entra um lote; os ids vêm de `assign_fn(clusters, prior_ids)` (como o pipeline).
    Por acontecimento real mede o CONJUNTO de ids ativos a cada rodada: `id_losses` = ids que existiam e SUMIRAM enquanto o acontecimento
    continua (fusão de fragmentos: o evento antigo some do mapa); `resurrections` = id que sumiu e VOLTOU depois. Fragmentos simultâneos
    (vários ids ao mesmo tempo) são `fragmentation`, medido à parte."""
    prior: dict[str, str] = {}
    seen: list[Signal] = []
    history: dict[str, list[set[str]]] = {}
    for batch in rounds:
        seen = seen + list(batch)
        clusters = cluster_fn(seen)
        ids = assign_fn(clusters, prior)
        now_ids: dict[str, set[str]] = {}
        for c, eid0 in zip(clusters, ids):
            eid = materialize_id(c, eid0)
            for s in c.signals:
                prior[s.hash] = eid
                now_ids.setdefault(truth[s.hash], set()).add(eid)
        for ev, cur in now_ids.items():
            history.setdefault(ev, []).append(cur)
    losses = resurrections = 0
    for sets in history.values():
        ever: set[str] = set()
        for prev, cur in zip([set()] + sets, sets):
            losses += len(prev - cur)
            resurrections += len((cur - prev) & ever)
            ever |= cur
    peak = {ev: max(len(x) for x in sets) for ev, sets in history.items()}
    return {"events": len(history), "id_losses": losses, "resurrections": resurrections,
            "fragmentation_max": max(peak.values()) if peak else 0, "events_fragmented": sum(1 for v in peak.values() if v > 1)}
