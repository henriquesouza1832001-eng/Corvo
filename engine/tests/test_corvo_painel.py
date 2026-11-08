from datetime import datetime, timezone

from corvo_engine.collect.painel import render

AGORA = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
FEED = {
    "pressure": "normal",
    "budget": {"used": 300, "limit": 300000},
    "news": [
        {"title": "Fed holds rates", "verdict": "hot", "region": "EUA", "published_at": "2026-11-08T11:30:00Z", "ingested_at": "2026-11-08T11:40:00Z"},
        {"title": "x" * 400, "verdict": "buffer", "region": None, "published_at": "2026-11-08T09:00:00Z", "ingested_at": "2026-11-08T09:10:00Z"},
    ],
}


def test_render_mostra_pressao_orcamento_e_noticias_mais_novas_primeiro():
    out = render(FEED, largura=80, agora=AGORA, cor=False)
    assert "pressão: normal" in out and "300/300000" in out
    assert out.index("Fed holds rates") < out.index("xxxx")
    assert "GRAVA" in out and "FILA" in out and "30min" in out


def test_titulo_longo_cabe_na_largura():
    assert all(len(linha) <= 80 for linha in render(FEED, largura=80, agora=AGORA, cor=False).splitlines())


def test_feed_vazio_e_dito_com_clareza():
    out = render({"pressure": "normal", "budget": {"used": 0, "limit": 100}, "news": []}, agora=AGORA, cor=False)
    assert "vazio" in out and "nenhum" in out
