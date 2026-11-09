import { useCallback, useEffect, useState } from "react";
import { adminFetch, ago } from "./admin";
import { TokenGate } from "./TokenGate";

/** Centro de comando da caixa (coletor 24 h). Só o token de operador manda comandos; tudo é registrado no banco. */
type Action = "on" | "off" | "restart" | "update" | "reboot" | "diag" | "logs" | "seco" | "envio" | "intervalo";
interface Cmd { id: string; action: Action; arg: number | null; state: "pending" | "done" | "expired"; ok: number | null; note: string | null; issued_at: string; finished_at: string | null; has_output: number }
interface BoxState {
	online: boolean;
	status: { running: boolean; mode: "envia" | "seco"; mem_kb: number | null; disk: string; last_cycle: string; version: string; seen_at: string; interval_s?: number | null } | null;
	pending: { id: string; action: Action; arg: number | null; issued_at: string } | null;
	history: Cmd[];
	server_time: string;
}
const LABEL: Record<Action, string> = { on: "Ligar coleta", off: "Desligar coleta", restart: "Reiniciar coleta", update: "Atualizar versão", reboot: "Reiniciar a caixa", diag: "Diagnóstico", logs: "Ver log", seco: "Modo seco", envio: "Modo envio", intervalo: "Intervalo" };

function Inner({ token, forget }: { token: string; forget: () => void }) {
	const [box, setBox] = useState<BoxState | null>(null);
	const [msg, setMsg] = useState("");
	const [busy, setBusy] = useState(false);
	const [secs, setSecs] = useState("900");
	const [view, setView] = useState<{ title: string; text: string } | null>(null);

	const load = useCallback(async () => {
		const r = await adminFetch<BoxState>(token, "/api/corvo/box");
		if (r.ok) { setBox(r.data); setMsg(""); } else setMsg(r.message);
	}, [token]);
	useEffect(() => {
		void load();
		const t = window.setInterval(() => { if (!document.hidden) void load(); }, 6000);
		return () => window.clearInterval(t);
	}, [load]);

	async function send(action: Action, arg?: number) {
		if (action === "reboot" && !window.confirm("Reiniciar a caixa inteira? O coletor volta sozinho em cerca de 3 minutos.")) return;
		setBusy(true);
		const r = await adminFetch<{ id: string }>(token, "/api/corvo/box/command", { method: "POST", body: arg === undefined ? { action } : { action, arg } });
		setMsg(r.ok ? `"${LABEL[action]}" enviado. A caixa o busca em até 20 s.` : r.message);
		await load();
		setBusy(false);
	}
	async function open(c: Cmd) {
		const r = await adminFetch<{ output: string | null; note: string | null }>(token, `/api/corvo/box/command/${c.id}`);
		setView({ title: `${LABEL[c.action]} · ${c.finished_at ?? ""}`, text: r.ok ? (r.data.output || r.data.note || "(sem saída)") : r.message });
	}

	const s = box?.status;
	const now = box?.server_time ?? new Date().toISOString();
	const n = Number(secs);
	return (
		<section className="box">
			<div className="box-head">
				<h2>Caixa</h2>
				<span className={`pill ${box?.online ? "on" : "demo"}`}>{box ? (box.online ? "ONLINE" : "SEM CONTATO") : "…"}</span>
			</div>
			{s ? (
				<dl className="box-grid">
					<dt>Coletor</dt><dd className={s.running ? "ok" : "bad"}>{s.running ? "LIGADO" : "DESLIGADO"}</dd>
					<dt>Envio</dt><dd>{s.mode === "envia" ? "envia ao banco" : "modo seco (não envia)"}</dd>
					<dt>Intervalo</dt><dd>{s.interval_s ? `${s.interval_s} s` : "?"}</dd>
					<dt>Memória livre</dt><dd>{s.mem_kb ? `${Math.round(s.mem_kb / 1024)} MB` : "?"}</dd>
					<dt>Disco livre</dt><dd>{s.disk || "?"}</dd>
					<dt>Versão</dt><dd>{s.version || "?"}</dd>
					<dt>Último contato</dt><dd>há {ago(s.seen_at, now)}</dd>
				</dl>
			) : <p className="muted">A caixa ainda não se apresentou.</p>}
			{s?.last_cycle && <p className="box-cycle sm muted">{s.last_cycle}</p>}
			{box?.pending && <p className="box-msg">Esperando a caixa executar: <b>{LABEL[box.pending.action]}</b></p>}

			<h3 className="box-sub">Coleta</h3>
			<div className="box-actions">
				<button className="box-btn go" disabled={busy} onClick={() => send("on")}>Ligar coleta</button>
				<button className="box-btn stop" disabled={busy} onClick={() => send("off")}>Desligar coleta</button>
				<button className="box-btn" disabled={busy} onClick={() => send("restart")}>Reiniciar coleta</button>
				<button className="box-btn" disabled={busy} onClick={() => send("update")}>Atualizar versão</button>
			</div>
			<h3 className="box-sub">Verificar</h3>
			<div className="box-actions">
				<button className="box-btn" disabled={busy} onClick={() => send("diag")}>Diagnóstico</button>
				<button className="box-btn" disabled={busy} onClick={() => send("logs")}>Ver log</button>
			</div>
			<h3 className="box-sub">Modo e ritmo</h3>
			<div className="box-actions">
				<button className="box-btn" disabled={busy} onClick={() => send("seco")}>Modo seco</button>
				<button className="box-btn" disabled={busy} onClick={() => send("envio")}>Modo envio</button>
				<input className="box-input" inputMode="numeric" value={secs} onChange={(e) => setSecs(e.target.value.replace(/\D/g, ""))} aria-label="segundos entre ciclos" />
				<button className="box-btn" disabled={busy || n < 300 || n > 3600} onClick={() => send("intervalo", n)}>Definir intervalo (300 a 3600 s)</button>
			</div>
			<h3 className="box-sub">Energia</h3>
			<div className="box-actions"><button className="box-btn danger" disabled={busy} onClick={() => send("reboot")}>Reiniciar a caixa</button></div>

			{msg && <p className="box-msg">{msg}</p>}
			{view && <div className="box-out"><div className="box-head"><b className="sm">{view.title}</b><button className="box-link" onClick={() => setView(null)}>fechar</button></div><pre>{view.text}</pre></div>}

			<h3 className="box-sub">Histórico</h3>
			<ul className="box-hist">
				{(box?.history ?? []).map((c) => (
					<li key={c.id} className={c.state === "done" ? (c.ok ? "ok" : "bad") : "muted"}>
						<span>{LABEL[c.action]}{c.arg ? ` ${c.arg}s` : ""}</span>
						<span className="sm">{c.state === "done" ? (c.ok ? "feito" : "falhou") : c.state === "pending" ? "esperando" : "expirou"}{c.note ? ` · ${c.note}` : ""} · há {ago(c.issued_at, now)}</span>
						{c.has_output ? <button className="box-link" onClick={() => void open(c)}>ver saída</button> : null}
					</li>
				))}
				{box && box.history.length === 0 && <li className="muted">nenhum comando ainda</li>}
			</ul>
			<button className="box-link" onClick={forget}>Trocar token</button>
		</section>
	);
}

export function BoxControl() {
	return <TokenGate title="Caixa">{(token, forget) => <Inner token={token} forget={forget} />}</TokenGate>;
}
