import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { adminFetch, ago } from "./admin";
import { TokenGate } from "./TokenGate";

/** A caixa como AGREGADOR: o que entra (fontes, preços, rede), o que ela faz (portão, CPU, temperatura, energia) e o que sai (banco, rede, corpus). */
interface Hora {
	hour: string;
	temp_avg?: number | null; temp_max?: number | null; cpu_avg?: number | null; mem_min_kb?: number | null;
	power_w_avg?: number | null; energy_wh?: number | null; rx_bytes?: number | null; tx_bytes?: number | null;
	cycles?: number; fetched?: number; new?: number; sent?: number; written?: number; feeds?: number; feeds_failed?: number;
	hot?: number; buffer?: number; dropped?: number; tier?: number;
	sources?: Record<string, [number, number]>; reasons?: Record<string, number>;
}
interface Box {
	online: boolean;
	status: {
		running: boolean; mode: string; mem_kb: number | null; disk: string; seen_at: string; version: string; interval_s?: number | null;
		temp_c?: number | null; cpu_pct?: number | null; load1?: number | null; power_w?: number | null; rx_bps?: number | null; tx_bps?: number | null;
		tier?: number | null; governor?: number | null; temp_limit_c?: number | null; temp_ceiling_c?: number | null; corpus_items?: number | null; prices_last?: string;
	} | null;
	server_time: string;
}

const fmtBytes = (n: number | null | undefined): string => {
	if (n == null) return "?";
	if (n < 1024) return `${n} B`;
	if (n < 1048576) return `${(n / 1024).toFixed(0)} KB`;
	if (n < 1073741824) return `${(n / 1048576).toFixed(1)} MB`;
	return `${(n / 1073741824).toFixed(2)} GB`;
};
const fmtRate = (bps: number | null | undefined): string => (bps == null ? "?" : `${fmtBytes(bps)}/s`);
const sum = (hs: Hora[], f: (h: Hora) => number | null | undefined): number => hs.reduce((a, h) => a + (f(h) ?? 0), 0);

function Spark({ values, color = "var(--c)", label }: { values: (number | null | undefined)[]; color?: string; label: string }) {
	const v = values.map((x) => (x == null ? null : x));
	const nums = v.filter((x): x is number => x !== null);
	if (nums.length < 2) return <div className="spark muted sm">{label}: aguardando horas</div>;
	const lo = Math.min(...nums), hi = Math.max(...nums), span = hi - lo || 1;
	const W = 160, H = 36;
	const pts = v.map((x, i) => (x === null ? null : `${((i / (v.length - 1)) * W).toFixed(1)},${(H - 3 - ((x - lo) / span) * (H - 6)).toFixed(1)}`)).filter(Boolean).join(" ");
	return (
		<div className="spark">
			<svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label}, de ${lo.toFixed(1)} a ${hi.toFixed(1)}`} preserveAspectRatio="none">
				<polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" />
			</svg>
			<span className="sm muted">{label} · {lo.toFixed(1)} a {hi.toFixed(1)}</span>
		</div>
	);
}

function Kpi({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "ok" | "warn" | "bad" }) {
	return <div className={`kpi ${tone ?? ""}`}><span className="kpi-l">{label}</span><b>{value}</b>{hint ? <span className="sm muted">{hint}</span> : null}</div>;
}

function Inner({ token, forget }: { token: string; forget: () => void }) {
	const [box, setBox] = useState<Box | null>(null);
	const [hs, setHs] = useState<Hora[]>([]);
	const [msg, setMsg] = useState("");
	const load = useCallback(async () => {
		const [b, m] = await Promise.all([adminFetch<Box>(token, "/api/corvo/box"), adminFetch<{ hours: Hora[] }>(token, "/api/corvo/box/metrics?hours=24")]);
		if (b.ok) { setBox(b.data); setMsg(""); } else setMsg(b.message);
		if (m.ok) setHs(m.data.hours);
	}, [token]);
	useEffect(() => {
		void load();
		const t = window.setInterval(() => { if (!document.hidden) void load(); }, 15000);
		return () => window.clearInterval(t);
	}, [load]);

	const s = box?.status;
	const now = box?.server_time ?? new Date().toISOString();
	const tot = useMemo(() => ({
		novas: sum(hs, (h) => h.new), grava: sum(hs, (h) => h.hot), fila: sum(hs, (h) => h.buffer), desc: sum(hs, (h) => h.dropped),
		enviadas: sum(hs, (h) => h.sent), escritas: sum(hs, (h) => h.written), rx: sum(hs, (h) => h.rx_bytes), tx: sum(hs, (h) => h.tx_bytes),
		wh: sum(hs, (h) => h.energy_wh), ciclos: sum(hs, (h) => h.cycles), falhas: sum(hs, (h) => h.feeds_failed),
	}), [hs]);
	const fontes = useMemo(() => {
		const acc: Record<string, [number, number]> = {};
		for (const h of hs) for (const [k, [n, a]] of Object.entries(h.sources ?? {})) { const c = (acc[k] ??= [0, 0]); c[0] += n; c[1] += a; }
		return Object.entries(acc).sort((a, b) => b[1][0] - a[1][0]).slice(0, 12);
	}, [hs]);
	const motivos = useMemo(() => {
		const acc: Record<string, number> = {};
		for (const h of hs) for (const [k, n] of Object.entries(h.reasons ?? {})) acc[k] = (acc[k] ?? 0) + n;
		return Object.entries(acc).sort((a, b) => b[1] - a[1]).slice(0, 5);
	}, [hs]);

	const teto = s?.temp_ceiling_c ?? 68, limite = s?.temp_limit_c ?? 80, temp = s?.temp_c ?? null;
	const tempTone = temp == null ? undefined : temp >= teto ? "bad" : temp >= teto - 4 ? "warn" : "ok";
	const pct = temp == null ? 0 : Math.max(0, Math.min(100, (temp / limite) * 100));
	const totalDec = tot.grava + tot.fila + tot.desc;

	return (
		<section className="ctl wide">
			<div className="box-head"><h2>Fluxo da caixa</h2><button className="box-link" onClick={() => void load()}>Atualizar</button></div>
			{msg && <p className="box-msg">{msg}</p>}
			<p className="muted sm">Últimas 24 h ({hs.length} h de dados). Energia é <b>estimada</b> pela CPU (a caixa não tem medidor). Rede é o que passa pela interface da caixa.</p>

			<div className="flow">
				<div className="flow-col in">
					<h3>ENTRADAS</h3>
					<Kpi label="Fontes ativas" value={hs.length ? (hs[hs.length - 1].feeds ?? "?") : "?"} hint={`camada ${s?.tier ?? "?"} · ${tot.falhas} falhas em 24 h`} tone={tot.falhas > 0 ? "warn" : "ok"} />
					<Kpi label="Itens novos lidos" value={tot.novas} hint={`${tot.ciclos} ciclos`} />
					<Kpi label="Rede, recebido" value={fmtBytes(tot.rx)} hint={`agora ${fmtRate(s?.rx_bps)}`} />
					<Kpi label="Preços" value={s?.prices_last ? s.prices_last.slice(5, 16).replace("T", " ") : "?"} hint="último ponto (UTC)" />
				</div>
				<div className="flow-arrow" aria-hidden>→</div>
				<div className="flow-col mid">
					<h3>CAIXA</h3>
					<div className="kpi"><span className="kpi-l">Portão (24 h)</span>
						<div className="funnel2" role="img" aria-label={`grava ${tot.grava}, fila ${tot.fila}, descarta ${tot.desc}`}>
							<i className="g" style={{ flexGrow: tot.grava }} /><i className="f" style={{ flexGrow: tot.fila }} /><i className="d" style={{ flexGrow: Math.max(tot.desc, 1) }} />
						</div>
						<span className="sm muted">grava {tot.grava} · fila {tot.fila} · descarta {tot.desc}{totalDec ? ` (${((100 * (tot.grava + tot.fila)) / totalDec).toFixed(1)}% aprovado)` : ""}</span>
					</div>
					<Kpi label="Temperatura" value={temp == null ? "?" : `${temp} °C`} tone={tempTone} hint={`teto ${teto} °C · limite ${limite} °C`} />
					<div className="gauge" aria-hidden><i style={{ width: `${pct}%` }} className={tempTone} /><u style={{ left: `${(teto / limite) * 100}%` }} /></div>
					<Kpi label="CPU" value={s?.cpu_pct != null ? `${s.cpu_pct}%` : "?"} hint={`carga ${s?.load1 ?? "?"} · RAM livre ${s?.mem_kb ? Math.round(s.mem_kb / 1024) : "?"} MB`} />
					<Kpi label="Energia (estimada)" value={s?.power_w != null ? `${s.power_w} W` : "?"} hint={`${tot.wh.toFixed(1)} Wh em 24 h · ${(tot.wh / 1000).toFixed(3)} kWh`} />
					<Kpi label="Camada de fontes" value={`${s?.tier ?? "?"} de 2`} hint={s?.governor ? "governador térmico ligado" : "governador desligado"} />
				</div>
				<div className="flow-arrow" aria-hidden>→</div>
				<div className="flow-col out">
					<h3>SAÍDAS</h3>
					<Kpi label="Enviado ao banco" value={tot.enviadas} hint={`${tot.escritas} linhas escritas em 24 h`} />
					<Kpi label="Rede, enviado" value={fmtBytes(tot.tx)} hint={`agora ${fmtRate(s?.tx_bps)}`} />
					<Kpi label="Corpus local" value={s?.corpus_items != null ? `${s.corpus_items} itens` : "?"} hint={`disco livre ${s?.disk ?? "?"}`} />
					<Kpi label="Último contato" value={s ? `há ${ago(s.seen_at, now)}` : "?"} hint={s ? `versão ${s.version} · modo ${s.mode}` : ""} tone={box?.online ? "ok" : "bad"} />
				</div>
			</div>

			<h3 className="box-sub">Últimas 24 horas</h3>
			<div className="sparks">
				<Spark values={hs.map((h) => h.temp_avg)} color="var(--a)" label="temperatura °C" />
				<Spark values={hs.map((h) => h.power_w_avg)} color="var(--g)" label="potência estimada W" />
				<Spark values={hs.map((h) => (h.rx_bytes ?? 0) + (h.tx_bytes ?? 0))} color="var(--c)" label="rede (bytes por hora)" />
				<Spark values={hs.map((h) => h.new)} color="var(--g)" label="itens novos por hora" />
				<Spark values={hs.map((h) => (h.hot ?? 0) + (h.buffer ?? 0))} color="var(--a)" label="aprovados por hora" />
			</div>

			<h3 className="box-sub">Por fonte (24 h): novos e aprovados</h3>
			{fontes.length === 0 ? <p className="muted sm">Sem dados por fonte ainda (o primeiro resumo chega ao fechar a primeira hora).</p> : (
				<ul className="srctable">
					{fontes.map(([k, [n, a]]) => (
						<li key={k}><span className="sname">{k}</span><span className="sbar"><i style={{ width: `${Math.min(100, (100 * a) / Math.max(n, 1))}%` }} /></span><span className="mono sm">{a}/{n}</span></li>
					))}
				</ul>
			)}
			{motivos.length > 0 && <p className="sm muted">Motivos de descarte: {motivos.map(([k, n]) => `${k} ${n}`).join(" · ")}</p>}
			<button className="box-link" onClick={forget}>Trocar token</button>
		</section>
	);
}

export function FluxoView() {
	return <TokenGate title="Fluxo da caixa">{(token, forget) => <Inner token={token} forget={forget} />}</TokenGate>;
}
