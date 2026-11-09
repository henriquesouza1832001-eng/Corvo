import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "./feed";

/** Visão do CELULAR: estado da caixa (coletor 24 h) e botões de controle. Só o token de operador manda comandos; ele fica neste aparelho. */
type Action = "on" | "off" | "restart" | "update" | "reboot";
interface BoxState {
	online: boolean;
	status: { running: boolean; mode: "envia" | "seco"; mem_kb: number | null; disk: string; last_cycle: string; version: string; seen_at: string } | null;
	command: { id: string; action: Action } | null;
	result: { action: Action; ok: boolean; note: string; finished_at: string } | null;
	server_time: string;
}

const TOKEN_KEY = "corvo_admin_token";
const LABEL: Record<Action, string> = { on: "Ligar coleta", off: "Desligar coleta", restart: "Reiniciar coleta", update: "Atualizar versão", reboot: "Reiniciar a caixa" };

function readToken(): string {
	try { return localStorage.getItem(TOKEN_KEY) ?? ""; } catch { return ""; }
}
function ago(iso: string | undefined, now: string): string {
	if (!iso) return "nunca";
	const s = Math.max(0, Math.round((Date.parse(now) - Date.parse(iso)) / 1000));
	return s < 90 ? `${s}s` : s < 5400 ? `${Math.round(s / 60)}min` : `${Math.round(s / 3600)}h`;
}

export function BoxControl() {
	const [token, setToken] = useState(readToken);
	const [draft, setDraft] = useState("");
	const [box, setBox] = useState<BoxState | null>(null);
	const [msg, setMsg] = useState("");
	const [busy, setBusy] = useState(false);
	const timer = useRef<number | undefined>(undefined);

	const load = useCallback(async () => {
		if (!token) return;
		try {
			const r = await fetch(`${API_URL}/api/corvo/box`, { headers: { Authorization: `Bearer ${token}` } });
			if (r.status === 401) { setMsg("Token recusado. Confira o token de operador."); setBox(null); return; }
			if (r.status === 503) { setMsg("O controle ainda não foi ativado no servidor (falta o segredo de operador)."); return; }
			if (!r.ok) { setMsg(`A API respondeu ${r.status}.`); return; }
			setBox((await r.json()) as BoxState);
			setMsg("");
		} catch { setMsg("Sem conexão com a API."); }
	}, [token]);

	useEffect(() => {
		void load();
		const tick = () => { if (!document.hidden) void load(); };
		timer.current = window.setInterval(tick, 8000);
		return () => window.clearInterval(timer.current);
	}, [load]);

	async function send(action: Action) {
		if (action === "reboot" && !window.confirm("Reiniciar a caixa inteira? O coletor volta sozinho em cerca de 3 minutos.")) return;
		setBusy(true);
		try {
			const r = await fetch(`${API_URL}/api/corvo/box/command`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
			setMsg(r.status === 202 ? `Comando "${LABEL[action]}" enviado. A caixa o recebe em até 1 minuto.` : r.status === 409 ? "Já há um comando esperando a caixa. Aguarde." : `Falhou (${r.status}).`);
			await load();
		} catch { setMsg("Sem conexão com a API."); }
		setBusy(false);
	}

	function save() {
		const t = draft.trim();
		if (t.length < 8) return;
		try { localStorage.setItem(TOKEN_KEY, t); } catch { /* sem armazenamento: vale só nesta sessão */ }
		setToken(t); setDraft("");
	}
	function forget() {
		try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignora */ }
		setToken(""); setBox(null); setMsg("");
	}

	if (!token) {
		return (
			<section className="box">
				<h2>Controle da caixa</h2>
				<p className="muted">Cole o token de operador. Ele fica só neste aparelho e nunca é mostrado de novo.</p>
				<input className="box-input" type="password" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="token de operador" />
				<button className="box-btn go" onClick={save} disabled={draft.trim().length < 8}>Salvar e entrar</button>
				{msg && <p className="box-msg">{msg}</p>}
			</section>
		);
	}

	const s = box?.status;
	const now = box?.server_time ?? new Date().toISOString();
	return (
		<section className="box">
			<div className="box-head">
				<h2>Controle da caixa</h2>
				<span className={`pill ${box?.online ? "on" : "demo"}`}>{box ? (box.online ? "ONLINE" : "SEM CONTATO") : "…"}</span>
			</div>
			{s ? (
				<dl className="box-grid">
					<dt>Coletor</dt><dd className={s.running ? "ok" : "bad"}>{s.running ? "LIGADO" : "DESLIGADO"}</dd>
					<dt>Envio</dt><dd>{s.mode === "envia" ? "envia ao banco" : "modo seco (não envia)"}</dd>
					<dt>Memória livre</dt><dd>{s.mem_kb ? `${Math.round(s.mem_kb / 1024)} MB` : "?"}</dd>
					<dt>Disco livre</dt><dd>{s.disk || "?"}</dd>
					<dt>Versão</dt><dd>{s.version || "?"}</dd>
					<dt>Último contato</dt><dd>há {ago(s.seen_at, now)}</dd>
				</dl>
			) : <p className="muted">A caixa ainda não se apresentou.</p>}
			{s?.last_cycle && <p className="box-cycle sm muted">{s.last_cycle}</p>}
			{box?.command && <p className="box-msg">Esperando a caixa executar: <b>{LABEL[box.command.action]}</b></p>}
			{box?.result && <p className={`box-msg ${box.result.ok ? "ok" : "bad"}`}>Último: {LABEL[box.result.action]} → {box.result.ok ? "feito" : "falhou"}{box.result.note ? ` (${box.result.note})` : ""} · há {ago(box.result.finished_at, now)}</p>}
			<div className="box-actions">
				<button className="box-btn go" disabled={busy} onClick={() => send("on")}>Ligar coleta</button>
				<button className="box-btn stop" disabled={busy} onClick={() => send("off")}>Desligar coleta</button>
				<button className="box-btn" disabled={busy} onClick={() => send("restart")}>Reiniciar coleta</button>
				<button className="box-btn" disabled={busy} onClick={() => send("update")}>Atualizar versão</button>
				<button className="box-btn danger" disabled={busy} onClick={() => send("reboot")}>Reiniciar a caixa</button>
			</div>
			{msg && <p className="box-msg">{msg}</p>}
			<button className="box-link" onClick={forget}>Trocar token</button>
		</section>
	);
}
