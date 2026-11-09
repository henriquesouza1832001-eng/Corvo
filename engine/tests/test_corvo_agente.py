import subprocess

from corvo_engine.collect import agente


def _ok(stdout="", code=0):
    return subprocess.CompletedProcess([], code, stdout, "")


class FakeRun:
    def __init__(self, fail=()):
        self.calls, self.fail = [], set(fail)

    def __call__(self, args):
        self.calls.append(list(args))
        if args[0] == "ps":
            return _ok("u0 1 sh deploy/box/run.sh\n")
        if args[0] == "df":
            return _ok("Filesystem Size Used Avail Use% Mounted\n/dev/x 4.1G 2.2G 1.9G 54% /data\n")
        if args[0] == "git":
            return _ok("abc1234\n")
        if args[0] == "uptime":
            return _ok("up 3 min\n")
        return _ok("feito\n", 1 if args[0] in self.fail else 0)


def test_estado_informa_coletor_modo_disco_e_intervalo():
    s = agente.estado(FakeRun(), {"CORVO_INGEST_TOKEN": "x", "CORVO_INTERVALO": "600"})
    assert s["running"] is True and s["mode"] == "envia" and s["disk"] == "1.9G" and s["version"] == "abc1234" and s["interval_s"] == 600
    assert agente.estado(FakeRun(), {})["mode"] == "seco"


def test_modo_seco_nao_precisa_apagar_o_token():
    assert agente.modo({"CORVO_INGEST_TOKEN": "x", "CORVO_MODO": "seco"}) == "seco"
    assert agente.modo({"CORVO_INGEST_TOKEN": "x", "CORVO_MODO": "envia"}) == "envia"
    assert agente.modo({"CORVO_MODO": "envia"}) == "seco"  # sem token nunca envia


def test_so_executa_acoes_da_lista_fechada():
    run = FakeRun()
    ok, note, _ = agente.executar("rm -rf /", run)
    assert not ok and note == "ação desconhecida" and run.calls == []
    ok, _, _ = agente.executar("off", run)
    assert ok and run.calls[-1][-1] == "off" and run.calls[-1][0] == "sh"


def test_intervalo_valida_o_argumento_de_novo_na_caixa():
    run = FakeRun()
    for ruim in (None, 10, 99999, "900", True):
        ok, note, _ = agente.executar("intervalo", run, ruim)
        assert not ok and "inválido" in note
    assert run.calls == []
    ok, _, _ = agente.executar("intervalo", run, 900)
    assert ok and run.calls[-1] == ["sh", agente.CORVO_SH, "intervalo", "900"]


def test_diag_e_logs_devolvem_texto_sem_chamar_o_shell_de_controle():
    run = FakeRun()
    ok, _, out = agente.executar("diag", run, env={"CORVO_INGEST_TOKEN": "x"})
    assert ok and "coletor: LIGADO" in out and "memória livre" in out
    ok, _, out = agente.executar("logs", run)
    assert ok and "caixa.log" in out
    assert all(c[0] in ("ps", "df", "git", "uptime") for c in run.calls)  # nenhum corvo.sh foi chamado


def test_saida_longa_e_cortada():
    assert len(agente._cap("x" * 10_000)) <= agente.OUT_MAX


def test_update_usa_atualizar_e_pede_reinicio_do_agente():
    run, posts = FakeRun(), []
    def post(path, body):
        posts.append(body)
        return {"command": {"id": "c1", "action": "update", "arg": None}} if len(posts) == 1 else {"command": None}
    cmd, ack, sair = agente.ciclo(post, run, {}, None)
    assert cmd["action"] == "update" and ack["id"] == "c1" and ack["ok"] is True and sair is True
    assert ["sh", agente.CORVO_SH, "atualizar"] in run.calls


def test_reboot_confirma_antes_de_reiniciar_e_informa_falta_de_root():
    posts, order = [], []
    def post(path, body):
        posts.append(body)
        order.append("post")
        return {"command": {"id": "c2", "action": "reboot", "arg": None}} if len(posts) == 1 else {"command": None}
    run = FakeRun()
    orig = run.__call__
    def tracking(args):
        if args[0] in ("su", "reboot"):
            order.append("reboot")
        return orig(args)
    agente.ciclo(post, tracking, {}, None)
    assert order.index("reboot") > 1  # o ack já foi enviado (2º post) antes do reboot
    assert posts[1]["ack"]["id"] == "c2"
    ok, _, _ = agente.executar("reboot", FakeRun(fail=("su", "reboot")))
    assert not ok


def test_ack_leva_a_saida_do_diagnostico():
    run = FakeRun()
    def post(path, body):
        return {"command": {"id": "c3", "action": "diag", "arg": None}}
    _, ack, _ = agente.ciclo(post, run, {"CORVO_INGEST_TOKEN": "x"}, None)
    assert ack["ok"] and "coletor:" in ack["output"]


def test_sem_comando_nao_executa_nada():
    run = FakeRun()
    cmd, ack, sair = agente.ciclo(lambda p, b: {"command": None}, run, {}, None)
    assert cmd is None and ack is None and sair is False
    assert all(c[0] in ("ps", "df", "git") for c in run.calls)


def test_rede_testa_api_internet_e_fonte(monkeypatch):
    monkeypatch.setattr(agente, "_tempo_ms", lambda url, timeout=10: f"12 ms ({url[:20]})")
    ok, _, out = agente.executar("rede", FakeRun(), env={"CORVO_API_URL": "https://exemplo.dev"})
    assert ok and "API do CORVO" in out and "internet" in out and "fonte (Fed)" in out and "https://exemplo.dev"[:20] in out


def test_fontes_resume_falhas_por_fonte(tmp_path, monkeypatch):
    log = tmp_path / "caixa.log"
    ciclos = ['{"feeds": 27, "feeds_failed": {"bbc": "x", "g1": "y"}, "new": 1}', '{"feeds": 27, "feeds_failed": {"bbc": "x"}, "new": 2}', '{"feeds": 27, "feeds_failed": {}, "new": 0}', "linha qualquer sem json"]
    log.write_text("\n".join(ciclos), encoding="utf-8")
    monkeypatch.setattr(agente, "LOG", log)
    ok, _, out = agente.executar("fontes", FakeRun())
    assert ok and "3 ciclos" in out and "bbc: 2" in out and "g1: 1" in out
    log.write_text('{"feeds": 27, "feeds_failed": {}}', encoding="utf-8")
    assert "nenhuma falha" in agente.executar("fontes", FakeRun())[2]
    log.write_text("", encoding="utf-8")
    assert "nenhum ciclo" in agente.executar("fontes", FakeRun())[2]


def test_comandos_de_shell_novos_chamam_so_o_corvo_sh():
    for acao in ("ciclo", "precos", "limpar"):
        run = FakeRun()
        ok, _, out = agente.executar(acao, run)
        assert ok and run.calls == [["sh", agente.CORVO_SH, acao]] and out == "feito"


def test_reiniciar_agente_confirma_e_pede_saida():
    posts = []
    def post(path, body):
        posts.append(body)
        return {"command": {"id": "c9", "action": "agente", "arg": None}}
    cmd, ack, sair = agente.ciclo(post, FakeRun(), {}, None)
    assert ack["ok"] and sair is True


def test_temperatura_aparece_no_estado_mesmo_sem_leitura(monkeypatch):
    monkeypatch.setattr(agente, "_temp_c", lambda: 47.5)
    assert agente.estado(FakeRun(), {})["temp_c"] == 47.5
    monkeypatch.setattr(agente, "_temp_c", lambda: None)
    assert agente.estado(FakeRun(), {})["temp_c"] is None


class RunSemColetor(FakeRun):
    """ps sem o run.sh: o coletor caiu."""
    def __call__(self, args):
        if args[0] == "ps":
            self.calls.append(list(args))
            return _ok("u0 1 sh deploy/box/agente.sh\n")
        return super().__call__(args)


def _sem_parado(monkeypatch, tmp_path):
    monkeypatch.setattr(agente, "PARADO", tmp_path / ".parado")
    monkeypatch.setattr(agente, "_ULTIMA_LIMPEZA", [0.0])


def test_religa_o_coletor_so_depois_de_tres_quedas_seguidas(monkeypatch, tmp_path):
    _sem_parado(monkeypatch, tmp_path)
    run, mem = RunSemColetor(), {}
    assert agente.guardas(run, mem, livre_mb=2000) == [] and agente.guardas(run, mem, livre_mb=2000) == []
    assert agente.guardas(run, mem, livre_mb=2000) == ["coletor caiu: religado"]
    assert ["sh", agente.CORVO_SH, "on"] in run.calls and mem["quedas"] == 0


def test_nao_religa_o_que_o_dono_desligou(monkeypatch, tmp_path):
    _sem_parado(monkeypatch, tmp_path)
    (tmp_path / ".parado").write_text("")
    run, mem = RunSemColetor(), {}
    for _ in range(10):
        assert agente.guardas(run, mem, livre_mb=2000) == []
    assert ["sh", agente.CORVO_SH, "on"] not in run.calls


def test_coletor_ligado_zera_a_contagem_de_quedas(monkeypatch, tmp_path):
    _sem_parado(monkeypatch, tmp_path)
    mem = {"quedas": 2}
    assert agente.guardas(FakeRun(), mem, livre_mb=2000) == [] and mem["quedas"] == 0


def test_disco_apertado_limpa_uma_vez_por_hora(monkeypatch, tmp_path):
    _sem_parado(monkeypatch, tmp_path)
    run = FakeRun()
    assert "limpeza feita" in agente.guardas(run, {}, livre_mb=250, agora=10_000.0)[0]
    assert agente.guardas(run, {}, livre_mb=250, agora=10_100.0) == []  # mesma hora: não repete
    assert agente.guardas(run, {}, livre_mb=250, agora=14_000.0) != []  # passou 1 h
    assert run.calls.count(["sh", agente.CORVO_SH, "limpar"]) == 2


def test_disco_quase_cheio_desliga_o_coletor(monkeypatch, tmp_path):
    _sem_parado(monkeypatch, tmp_path)
    run = FakeRun()
    feitas = agente.guardas(run, {}, livre_mb=80, agora=1.0)
    assert any("desligado por segurança" in f for f in feitas) and ["sh", agente.CORVO_SH, "off"] in run.calls
    assert agente.guardas(FakeRun(), {}, livre_mb=2000) == []  # disco folgado: nada a fazer


def test_ciclo_leva_os_indicadores_ao_vivo_e_o_resumo_da_hora_uma_vez():
    corpos = []
    def post(path, body):
        corpos.append(body)
        return {"command": None}
    live = {"cpu_pct": 12.5, "power_w": 2.9, "rx_bytes": 1000, "tx_bytes": 50, "rx_bps": None}
    hora = {"hour": "2026-11-09T02", "energy_wh": 3.1}
    agente.ciclo(post, FakeRun(), {}, None, live, hora)
    assert corpos[0]["status"]["cpu_pct"] == 12.5 and corpos[0]["status"]["power_w"] == 2.9
    assert "rx_bps" not in corpos[0]["status"]  # campo sem leitura não vai
    assert corpos[0]["metrics_hour"] == hora
    agente.ciclo(post, FakeRun(), {}, None, live, None)
    assert "metrics_hour" not in corpos[1]


def test_tier_e_governador_validam_o_argumento_de_novo_na_caixa():
    for acao in ("tier", "governador"):
        for ruim in (None, -1, 3 if acao == "tier" else 2, "1", True):
            ok, note, _ = agente.executar(acao, FakeRun(), ruim)
            assert not ok and "inválido" in note, (acao, ruim)
    run = FakeRun()
    ok, _, _ = agente.executar("tier", run, 2)
    assert ok and run.calls[-1] == ["sh", agente.CORVO_SH, "tier", "2"]
    ok, _, _ = agente.executar("governador", run, 0)
    assert ok and run.calls[-1] == ["sh", agente.CORVO_SH, "governador", "0"]


def test_estado_informa_camada_governador_e_teto_termico():
    s = agente.estado(FakeRun(), {"CORVO_TIER": "1", "CORVO_TEMP_LIMITE": "70"})
    assert s["tier"] == 1 and s["governor"] == 1 and s["temp_limit_c"] == 70.0 and s["temp_ceiling_c"] == 59.5
    s = agente.estado(FakeRun(), {"CORVO_GOVERNADOR": "0", "CORVO_TIER": "9"})
    assert s["governor"] == 0 and s["tier"] == 2 and s["temp_limit_c"] == 80.0


def test_horario_da_ultima_mudanca_de_camada_sobrevive_ao_reinicio():
    assert agente._tier_desde({"CORVO_TIER_T": "1762650000"}) == 1762650000.0
    assert agente._tier_desde({}) == 0.0 and agente._tier_desde({"CORVO_TIER_T": "lixo"}) == 0.0
