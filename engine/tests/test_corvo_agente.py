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
        return _ok("feito\n", 1 if args[0] in self.fail else 0)


def test_estado_informa_coletor_modo_e_disco():
    s = agente.estado(FakeRun(), {"CORVO_INGEST_TOKEN": "x"})
    assert s["running"] is True and s["mode"] == "envia" and s["disk"] == "1.9G" and s["version"] == "abc1234"
    assert agente.estado(FakeRun(), {})["mode"] == "seco"


def test_so_executa_acoes_da_lista_fechada():
    run = FakeRun()
    ok, note = agente.executar("rm -rf /", run)
    assert not ok and note == "ação desconhecida" and run.calls == []
    ok, _ = agente.executar("off", run)
    assert ok and run.calls[-1][-1] == "off" and run.calls[-1][0] == "sh"


def test_update_usa_o_comando_atualizar_e_pede_reinicio_do_agente():
    run, posts = FakeRun(), []
    def post(path, body):
        posts.append(body)
        return {"command": {"id": "c1", "action": "update"}} if len(posts) == 1 else {"command": None}
    cmd, ack, sair = agente.ciclo(post, run, {}, None)
    assert cmd["action"] == "update" and ack == {"id": "c1", "ok": True, "note": "feito"} and sair is True
    assert ["sh", agente.CORVO_SH, "atualizar"] in run.calls


def test_reboot_confirma_antes_de_reiniciar_e_informa_falta_de_root():
    posts, order = [], []
    def post(path, body):
        posts.append(body)
        order.append("post")
        return {"command": {"id": "c2", "action": "reboot"}} if len(posts) == 1 else {"command": None}
    run = FakeRun()
    orig = run.__call__
    def tracking(args):
        if args[0] in ("su", "reboot"):
            order.append("reboot")
        return orig(args)
    cmd, ack, _ = agente.ciclo(post, tracking, {}, None)
    assert order.index("reboot") > 1  # o ack já foi enviado (2º post) antes do reboot
    assert posts[1]["ack"]["id"] == "c2"
    sem_root = FakeRun(fail=("su", "reboot"))
    ok, note = agente.executar("reboot", sem_root)
    assert not ok and "root" in note


def test_sem_comando_nao_executa_nada():
    run = FakeRun()
    cmd, ack, sair = agente.ciclo(lambda p, b: {"command": None}, run, {}, None)
    assert cmd is None and ack is None and sair is False
    assert all(c[0] in ("ps", "df", "git") for c in run.calls)
