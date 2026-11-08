"""Bancada de prova de Munin: mede uma lista de previsões resolvidas (Brier, taxa-base, skill, calibração, intervalo).

Uso (pasta engine):
    py benchmarks\\corvo_munin_eval.py --synthetic              # cobre seis cenários simulados, inclusive vazamento e pouca amostra
    py benchmarks\\corvo_munin_eval.py resolvidas.jsonl         # uma previsão por linha: {"p":0.7,"y":1,"lo":0.6,"hi":0.8}
    py benchmarks\\corvo_munin_eval.py resolvidas.jsonl --base-rate 0.32   # taxa-base de um período ANTERIOR (sem olhar o futuro)

Com menos de 100 resolvidas o estado é EXPERIMENTAL e a bancada avisa: amostra pequena não prova nada.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corvo_engine.munin import (  # noqa: E402
    base_rate_brier, bin_interval_coverage, brier, calibration_table, ece, forecast_status, skill,
)
from corvo_engine.munin.leakage import LeakageError, assert_point_in_time  # noqa: E402


def report(name: str, ps: list[float], ys: list[int], los: list[float] | None = None, his: list[float] | None = None, base_rate: float | None = None) -> None:
    n = len(ps)
    e = ece(ps, ys)
    sk = skill(ps, ys, base_rate)
    print(f"\n== {name}  (n={n}, taxa de acerto do evento {sum(ys) / n:.1%})")
    print(f"   Brier           {brier(ps, ys):.4f}")
    print(f"   Brier taxa-base {base_rate_brier(ys, base_rate):.4f}   <- a régua")
    print(f"   Skill           {'n/d' if sk is None else f'{sk:+.3f}'}   (<= 0: não vale nada)")
    print(f"   ECE             {e:.4f}   (<= 0,05 para confiar)")
    if los and his:
        cov = bin_interval_coverage(ps, ys, los, his)
        print(f"   Cobertura do intervalo por faixa  {cov:.0%}" if cov == cov else "   Cobertura do intervalo: amostra pequena por faixa")
    print(f"   Calibração      {forecast_status(n, e)}")
    if sk is not None and sk <= 0:
        print("   Skill não positivo: não há ganho sobre a taxa-base.")
    if n < 100:
        print("   AVISO: menos de 100 resolvidas. Amostra pequena não prova nada.")
    print("   faixa      n    prevê   real")
    for b in calibration_table(ps, ys):
        print(f"   {b.lo:.1f}-{b.hi:.1f} {b.n:5d}  {b.mean_p:5.2f}  {b.freq:5.2f}")


def run_synthetic() -> None:
    """Run deterministic teaching cases; none represents a real CORVO forecast."""
    rng = random.Random(7)
    truth = [rng.random() for _ in range(3000)]
    ys = [1 if rng.random() < t else 0 for t in truth]
    report("previsor CALIBRADO (simulado)", truth, ys)
    report("previsor EXAGERADO (simulado)", [0.97 if t > 0.5 else 0.03 for t in truth], ys)
    report("previsor TAXA-BASE (simulado; base anterior=0,50)", [0.5] * len(ys), ys, base_rate=0.5)
    cautious = [0.5 + 0.5 * (p - 0.5) for p in truth]
    report("previsor CONSERVADOR (simulado)", cautious, ys, base_rate=0.5)

    small_n = 12
    report("previsor com POUCA AMOSTRA (simulado)", truth[:small_n], ys[:small_n], base_rate=0.5)
    print(f"   Atualização de pesos: HOLD ({small_n} < 30 resolvidas por tema/fonte).")

    forecast_at = "2026-11-08T10:00:00Z"
    future_rows = [{"ingested_at": "2026-11-08T10:01:00Z", "future_outcome": 1}]
    try:
        assert_point_in_time(future_rows, forecast_at)
    except LeakageError as exc:
        print("\n== previsor COM VAZAMENTO (simulado) ==")
        print(f"   BLOQUEADO antes da pontuação: {exc}")
    else:
        raise AssertionError("a bancada aceitou uma feature recebida depois do corte temporal")
    print("\nCENÁRIOS SIMULADOS: 6; todos sintéticos, nenhuma previsão real avaliada.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--base-rate", type=float, default=None)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.synthetic:
        run_synthetic()
        return 0
    if not args.file:
        print(__doc__)
        return 2
    rows = [json.loads(line) for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip()]
    ps, ys = [float(r["p"]) for r in rows], [int(r["y"]) for r in rows]
    los = [float(r["lo"]) for r in rows] if rows and "lo" in rows[0] else None
    his = [float(r["hi"]) for r in rows] if rows and "hi" in rows[0] else None
    report(Path(args.file).name, ps, ys, los, his, args.base_rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
