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
