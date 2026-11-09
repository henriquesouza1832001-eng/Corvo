import { useCallback, useEffect, useState, type ReactNode } from "react";
import { adminFetch, ago } from "./admin";
import { TokenGate } from "./TokenGate";

interface Diag {
	worker: { ok: boolean; time: string };
	db: { backend: string; ping_ms: number };
	budget: { used: number; limit: number; percent: number; pressure: "normal" | "economy" | "critical" };
	feed: { news_total: number; news_24h: number; newest_ingest: string | null; newest_age_s: number | null; stats_newest: string | null };
	kv_feed_cache: boolean;
}
interface BoxLite {
	online: boolean;
	status: { running: boolean; mode: string; seen_at: string; prices_last?: string; corpus_items?: number | null; errors_recent?: number | null } | null;
	server_time: string;
}
type Tone = "ok" | "warn" | "bad";

function Card({ title, tone, children }: { title: string; tone?: Tone; children: ReactNode }) {
	return <div className={`sys-card ${tone ?? ""}`}><h3>{title}</h3>{children}</div>;
}

function Inner({ token, forget }: { token: string; forget: () => void }) {
	const [d, setD] = useState<Diag | null>(null);
	const [b, setB] = useState<BoxLite | null>(null);
	const [msg, setMsg] = useState("");
	const [days, setDays] = useState("30");
	async function purge(body: { older_than_days: number } | { all: true }, aviso: string) {
		if (!window.confirm(aviso)) return;
		if ("all" in body && window.prompt('Isto apaga TODAS as notícias e estatísticas do painel. Digite APAGAR para confirmar.') !== "APAGAR") return;
		const r = await adminFetch<{ deleted: { news: number; stats: number } }>(token, "/api/corvo/purge", { method: "POST", body });
		setMsg(r.ok ? `Limpo: ${r.data.deleted.news} notícias e ${r.data.deleted.stats} estatísticas apagadas.` : r.message);
		void load();
	}
	const load = useCallback(async () => {
		const [rd, rb] = await Promise.all([adminFetch<Diag>(token, "/api/corvo/diag"), adminFetch<BoxLite>(token, "/api/corvo/box")]);
		if (rd.ok) { setD(rd.data); setMsg(""); } else setMsg(rd.message);
		if (rb.ok) setB(rb.data);
	}, [token]);
	useEffect(() => {
		void load();
		const t = window.setInterval(() => { if (!document.hidden) void load(); }, 15000);
		return () => window.clearInterval(t);
	}, [load]);

	const age = d?.feed.newest_age_s ?? null;
	const feedTone: Tone = age === null ? "bad" : age < 3600 ? "ok" : age < 21600 ? "warn" : "bad";
	const s = b?.status;
	const nowIso = d?.worker.time ?? new Date().toISOString();
	return (
		<section className="ctl">
			<div className="box-head"><h2>Sistema</h2><button className="box-link" onClick={() => void load()}>Atualizar</button></div>
			{msg && <p className="box-msg">{msg}</p>}
			<div className="sys-grid">
				<Card title="Worker" tone={d?.worker.ok ? "ok" : "bad"}><b>{d?.worker.ok ? "NO AR" : "?"}</b><span className="muted sm">{d ? new Date(d.worker.time).toLocaleTimeString() : ""}</span></Card>
				<Card title="Banco" tone={d && d.db.ping_ms < 800 ? "ok" : "warn"}><b>{d ? `${d.db.ping_ms} ms` : "?"}</b><span className="muted sm">{d?.db.backend}</span></Card>
				<Card title="Escritas hoje" tone={d?.budget.pressure === "critical" ? "bad" : d?.budget.pressure === "economy" ? "warn" : "ok"}><b>{d ? `${d.budget.percent}%` : "?"}</b><span className="muted sm">{d ? `${d.budget.used}/${d.budget.limit} · ${d.budget.pressure}` : ""}</span></Card>
				<Card title="Último envio" tone={feedTone}><b>{age === null ? "nenhum" : `há ${ago(d?.feed.newest_ingest, nowIso)}`}</b><span className="muted sm">{d ? `${d.feed.news_24h} em 24 h · ${d.feed.news_total} no total` : ""}</span></Card>
				<Card title="Caixa" tone={b?.online ? (s?.running ? "ok" : "warn") : "bad"}><b>{b ? (b.online ? (s?.running ? "COLETANDO" : "PARADA") : "SEM CONTATO") : "?"}</b><span className="muted sm">{s ? `modo ${s.mode} · contato há ${ago(s.seen_at, b?.server_time ?? nowIso)}` : ""}</span></Card>
				<Card title="Corpus e preços" tone="ok"><b>{s?.corpus_items ?? "?"} itens</b><span className="muted sm">preço até {s?.prices_last ? s.prices_last.replace("T", " ").replace("Z", "") : "?"}</span></Card>
			</div>
			{s && (s.errors_recent ?? 0) > 0 && <p className="box-msg bad">A caixa registrou {s.errors_recent} erro(s) recente(s) no log. Veja em Caixa, Ver log.</p>}
			<h3 className="box-sub">Banco</h3>
			<div className="box-actions">
				<input className="box-input" inputMode="numeric" value={days} onChange={(e) => setDays(e.target.value.replace(/\D/g, ""))} aria-label="dias a manter" />
				<button className="box-btn" disabled={!days} onClick={() => void purge({ older_than_days: Number(days) }, `Apagar notícias e estatísticas com mais de ${days} dias?`)}>Limpar antigas (mais de N dias)</button>
				<button className="box-btn danger" onClick={() => void purge({ all: true }, "Apagar TODO o feed e recomeçar do zero?")}>Apagar tudo</button>
			</div>
			<p className="muted sm">Cache do feed (KV): {d ? (d.kv_feed_cache ? "ligado" : "desligado") : "?"}. O controle da caixa não usa KV: tudo fica no banco.</p>
			<button className="box-link" onClick={forget}>Trocar token</button>
		</section>
	);
}

export function SystemView() {
	return <TokenGate title="Sistema">{(token, forget) => <Inner token={token} forget={forget} />}</TokenGate>;
}
