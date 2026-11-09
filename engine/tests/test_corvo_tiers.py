import json

import pytest

from corvo_engine.collect.feeds import CATALOG_PATH, load_catalog


def test_sem_variavel_so_o_nucleo_como_sempre(monkeypatch):
    monkeypatch.delenv("CORVO_TIER", raising=False)
    nucleo = load_catalog()
    assert nucleo and all(int(f.get("tier", 0)) == 0 for f in nucleo)


def test_camadas_sao_cumulativas(monkeypatch):
    monkeypatch.delenv("CORVO_TIER", raising=False)
    n0, n1, n2 = (len(load_catalog(tier=t)) for t in (0, 1, 2))
    assert n0 < n1 < n2
    assert {f["id"] for f in load_catalog(tier=0)} <= {f["id"] for f in load_catalog(tier=1)} <= {f["id"] for f in load_catalog(tier=2)}


def test_variavel_de_ambiente_escolhe_a_camada(monkeypatch):
    monkeypatch.setenv("CORVO_TIER", "1")
    assert len(load_catalog()) == len(load_catalog(tier=1))
    monkeypatch.setenv("CORVO_TIER", "lixo")  # valor inválido nunca derruba a coleta: cai no núcleo
    assert len(load_catalog()) == len(load_catalog(tier=0))


def test_catalogo_tem_ids_unicos_e_campos_obrigatorios():
    feeds = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["feeds"]
    ids = [f["id"] for f in feeds]
    assert len(ids) == len(set(ids))
    for f in feeds:
        assert f["url"].startswith(("http://", "https://")) and 0 < f["reliability"] <= 1 and f["max_age_h"] > 0, f["id"]
        assert int(f.get("tier", 0)) in (0, 1, 2), f["id"]


@pytest.mark.parametrize("tier,minimo", [(1, 8), (2, 19)])
def test_cada_camada_traz_as_fontes_novas(tier, minimo):
    extras = [f for f in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["feeds"] if int(f.get("tier", 0)) == tier]
    assert len(extras) >= minimo - (8 if tier == 2 else 0)
    if tier == 1:
        assert all(f["official"] for f in extras)  # a camada 1 é só fonte oficial
