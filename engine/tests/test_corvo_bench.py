import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.corvo_gate_eval import measure, verdict_of
from benchmarks.corvo_make_sample import split_of

ENGINE = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ENGINE, capture_output=True, text=True, encoding="utf-8")


def test_split_is_stable_per_url_and_roughly_70_30():
    urls = [f"https://x.com/{i}" for i in range(4000)]
    a = [split_of(u, 1) for u in urls]
    assert a == [split_of(u, 1) for u in urls]  # estável: gerar a amostra de novo nunca troca um item de lado
    assert 0.25 < a.count("eval") / len(a) < 0.35
    assert [split_of(u, 2) for u in urls] != a  # outra semente, outra divisão


def test_verdict_of_follows_the_gate():
    assert verdict_of("Fed announces surprise rate cut as inflation cools") == "hot"
    assert verdict_of("Celebrity perfume launch") == "drop"


def test_measure_applies_stratum_weights():
    rows = [
        {"title": "Fed announces surprise rate cut as inflation cools", "label": "keep", "w": 1.0},  # keep aceito (hot)
        {"title": "Celebrity perfume launch", "label": "keep", "w": 10.0},  # keep rejeitado, peso 10: recall tem que cair muito
        {"title": "Celebrity perfume launch", "label": "drop", "w": 10.0},
        {"title": "Earthquake hits Tokyo", "label": "drop", "w": 1.0},  # drop gravado (buffer)
    ]
    r = measure(rows)
    assert r["precisao_hot"] == pytest.approx(1.0)  # Earthquake fica em BUFFER com o corte HOT calibrado
    assert r["recall_keep"] == pytest.approx(1 / 11)  # 1 de peso 1 gravado; 10 de peso perdido
    assert r["keep_descartado"] == pytest.approx(10 / 11)
    assert r["drop_gravado"] == pytest.approx(0.5)
    assert r["hot_entre_aceitos"] == pytest.approx(0.5)


def test_measure_handles_empty_sets():
    r = measure([])
    assert r["precisao_hot"] is None and r["recall_keep"] is None


def test_label_flow_end_to_end(tmp_path):
    sample = tmp_path / "c.sample.jsonl"
    rows = [{"idx": i, "url": f"https://x.com/{i}", "source_id": "s", "title": t, "stratum": "aceito", "w": 1.0, "split": "fit" if i < 2 else "eval"}
            for i, t in enumerate(["Fed announces rate cut as inflation cools", "Celebrity perfume launch", "OPEC agrees oil output cut"])]
    sample.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    shown = run("benchmarks/corvo_label.py", "show", str(sample), "--from", "0", "--count", "3")
    assert "Fed announces" in shown.stdout and "hot" not in shown.stdout.lower().replace("whot", "")  # nunca mostra a decisão do portão
    assert run("benchmarks/corvo_label.py", "apply", str(sample), "--from", "0", "--codes", "KD-").returncode == 0
    assert run("benchmarks/corvo_label.py", "apply", str(sample), "--from", "0", "--codes", "KXD").returncode == 2  # código inválido
    assert run("benchmarks/corvo_label.py", "apply", str(sample), "--from", "2", "--codes", "KK").returncode == 2  # passa do fim
    labels = tmp_path / "c.labels.jsonl"
    got = {json.loads(x)["title"]: json.loads(x)["label"] for x in labels.read_text(encoding="utf-8").splitlines()}
    assert got == {"Fed announces rate cut as inflation cools": "keep", "Celebrity perfume launch": "drop"}  # o "-" pulou o terceiro
    status = run("benchmarks/corvo_label.py", "status", str(sample))
    assert "2/3" in status.stdout
    ev = run("benchmarks/corvo_gate_eval.py", str(labels), "--json")
    out = json.loads(ev.stdout)
    assert out["fit"]["n"] == 2 and out["eval"]["n"] == 0
