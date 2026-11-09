import json

from corvo_engine.collect import governador as g
from corvo_engine.collect import metricas as m

# ---------- governador ----------

def _roda(est, temps, mem=500_000, t0=10_000.0, passo=20.0, cfg=None):
    ult = g.Decisao(est.tier)
    for i, t in enumerate(temps):
        ult = g.decidir(est, t, mem, t0 + i * passo, cfg)
        if ult.motivo:
            est.tier, est.ultima_mudanca = ult.tier, t0 + i * passo
    return ult


def test_teto_e_85_por_cento_do_limite():
    assert g.Cfg().teto_c == 68.0
    assert g.Cfg(limite_c=70).teto_c == 59.5


def test_sobe_uma_camada_quando_ha_folga_e_so_depois_de_uma_janela_cheia():
    est = g.Estado()
    for i in range(11):  # janela ainda curta: não decide
        assert g.decidir(est, 50.0, 500_000, 10_000.0 + i * 20).motivo == ""
    d = g.decidir(est, 50.0, 500_000, 10_000.0 + 11 * 20)
    assert d.tier == 1 and "subiu" in d.motivo


def test_nao_sobe_de_novo_antes_de_30_minutos():
    est = g.Estado()
    _roda(est, [50.0] * 12)
    assert est.tier == 1
    d = g.decidir(est, 50.0, 500_000, est.ultima_mudanca + 600)
    assert d.motivo == "" and est.tier == 1
    d = g.decidir(est, 50.0, 500_000, est.ultima_mudanca + 1900)
    assert d.tier == 2


def test_para_de_subir_no_maximo_de_camadas():
    est = g.Estado(tier=2)
    _roda(est, [50.0] * 30, t0=100_000.0)
    assert est.tier == 2


def test_nao_sobe_perto_do_teto():
    est = g.Estado()
    _roda(est, [66.0] * 40)  # abaixo do teto de 68, mas sem folga de 4 °C
    assert est.tier == 0


def test_desce_quando_a_mediana_chega_ao_teto():
    est = g.Estado(tier=2)
    d = _roda(est, [69.0] * 9)
    assert est.tier == 1 and "teto" in d.motivo


def test_desce_com_memoria_baixa_e_nao_sobe_sem_memoria():
    est = g.Estado(tier=2)
    _roda(est, [50.0] * 9, mem=100_000)
    assert est.tier == 1
    est2 = g.Estado()
    _roda(est2, [50.0] * 40, mem=200_000)  # memória abaixo do mínimo para subir
    assert est2.tier == 0


def test_emergencia_volta_a_camada_zero():
    est = g.Estado(tier=2)
    d = g.decidir(est, 77.0, 500_000, 1.0)
    assert d.tier == 0 and "emergência" in d.motivo and not d.parar


def test_no_limite_por_tres_leituras_pede_para_desligar():
    est = g.Estado(tier=0)
    assert not g.decidir(est, 80.5, 500_000, 1.0).parar
    assert not g.decidir(est, 81.0, 500_000, 2.0).parar
    assert g.decidir(est, 81.0, 500_000, 3.0).parar
    est2 = g.Estado()
    g.decidir(est2, 80.5, 1, 1.0); g.decidir(est2, 60.0, 500_000, 2.0)  # uma leitura fria zera a contagem
    assert est2.no_limite == 0


def test_sem_leitura_de_temperatura_nao_muda_nada():
    est = g.Estado(tier=1)
    assert g.decidir(est, None, 500_000, 1.0) == g.Decisao(1)


# ---------- métricas ----------

def test_potencia_estimada_pela_cpu():
    assert m.potencia_w(0) == 2.5 and m.potencia_w(100) == 6.0 and m.potencia_w(50) == 4.25
    assert m.potencia_w(250) == 6.0 and m.potencia_w(-5) == 2.5 and m.potencia_w(None) is None


def test_le_rede_somando_interfaces_menos_a_local(tmp_path):
    p = tmp_path / "dev"
    p.write_text("Inter-|   Receive\n face |bytes\n    lo: 999 0 0 0 0 0 0 0 999 0 0 0 0 0 0 0\n wlan0: 1000 5 0 0 0 0 0 0 400 3 0 0 0 0 0 0\n eth0: 50 1 0 0 0 0 0 0 20 1 0 0 0 0 0 0\n")
    assert m.ler_rede(str(p)) == (1050, 420)
    assert m.ler_rede(str(tmp_path / "nao_existe")) is None


def test_medidor_calcula_cpu_taxas_de_rede_e_ignora_contador_zerado():
    estado = iter([((0, 100), (1000, 100)), ((50, 200), (11000, 1100)), ((60, 300), (200, 40))])
    atual = {}
    med2 = m.Medidor(ler_rede_fn=lambda: atual["rede"], ler_cpu_fn=lambda: atual["cpu"], carga_fn=lambda: 0.2, ociosa=2.0, maxima=6.0)
    atual["cpu"], atual["rede"] = next(estado)
    a1 = med2.amostra(0.0)
    assert a1["cpu_pct"] is None and a1["rx_bps"] is None  # primeira amostra: sem taxa
    atual["cpu"], atual["rede"] = next(estado)
    a2 = med2.amostra(10.0)
    assert a2["cpu_pct"] == 50.0 and a2["rx_bps"] == 1000 and a2["tx_bps"] == 100 and a2["power_w"] == 4.0
    atual["cpu"], atual["rede"] = next(estado)
    a3 = med2.amostra(20.0)
    assert a3["rx_bps"] == 0 and a3["tx_bps"] == 0  # o contador zerou (reinício): nunca vira taxa negativa


def test_acumulador_fecha_a_hora_com_energia_rede_e_temperatura():
    ac = m.Acumulador()
    h0 = 1_000_000_000 - (1_000_000_000 % 3600)  # início de uma hora UTC
    assert ac.registrar(h0 + 10, {"cpu_pct": 10, "power_w": 3.0, "rx_bytes": 1000, "tx_bytes": 100}, 50.0, 400_000) is None
    assert ac.registrar(h0 + 20, {"cpu_pct": 30, "power_w": 4.0, "rx_bytes": 3000, "tx_bytes": 300}, 54.0, 380_000) is None
    fechada = ac.registrar(h0 + 3600 + 5, {"cpu_pct": 0, "power_w": 2.5, "rx_bytes": 9000, "tx_bytes": 900}, 51.0, 390_000, extra={"cycles": 6})
    assert fechada["hour"] == m.hora_de(h0 + 10) and fechada["samples"] == 2
    assert fechada["temp_avg"] == 52.0 and fechada["temp_max"] == 54.0 and fechada["cpu_avg"] == 20.0
    assert fechada["rx_bytes"] == 2000 and fechada["tx_bytes"] == 200 and fechada["mem_min_kb"] == 380_000
    assert fechada["energy_wh"] == round(4.0 * 10 / 3600, 3) and fechada["cycles"] == 6
    nova = ac.resumo()
    assert nova["samples"] == 1  # a hora seguinte começou do zero


def test_fluxo_da_hora_le_o_log_e_o_corpus(tmp_path):
    log, corpus = tmp_path / "caixa.log", tmp_path / "corpus.jsonl"
    ciclo = lambda n, f: json.dumps({"feeds": 46, "feeds_failed": f, "fetched": 900, "new": n, "sent_news": 2, "api": {"ok": True, "written": 3}})
    log.write_text("\n".join(["2026-11-09T02:00:05Z ciclo", ciclo(5, {}), "2026-11-09T02:05:05Z ciclo", ciclo(7, {"bbc": "x"}), "2026-11-09T03:00:05Z ciclo", ciclo(99, {}), "lixo"]), encoding="utf-8")
    linhas = [{"cycle_at": "2026-11-09T02:00:05", "source_id": "cnbc", "verdict": "hot", "reason": "relevant"},
              {"cycle_at": "2026-11-09T02:05:05", "source_id": "cnbc", "verdict": "drop", "reason": "irrelevant"},
              {"cycle_at": "2026-11-09T02:05:05", "source_id": "dw", "verdict": "buffer", "reason": "relevant"},
              {"cycle_at": "2026-11-09T03:01:00", "source_id": "dw", "verdict": "hot", "reason": "relevant"}]
    corpus.write_text("\n".join(json.dumps(x) for x in linhas) + "\nlixo\n", encoding="utf-8")
    f = m.fluxo_da_hora("2026-11-09T02", log, corpus)
    assert f["cycles"] == 2 and f["new"] == 12 and f["sent"] == 4 and f["written"] == 6 and f["feeds"] == 46 and f["feeds_failed"] == 1
    assert (f["hot"], f["buffer"], f["dropped"]) == (1, 1, 1) and f["reasons"] == {"irrelevant": 1}
    assert f["sources"]["cnbc"] == [2, 1] and f["sources"]["dw"] == [1, 1]
    assert m.fluxo_da_hora("2026-11-09T09", log, corpus)["cycles"] == 0
