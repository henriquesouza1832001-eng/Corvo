import { useEffect, useMemo, useState } from "react";
import { DEMO_BUDGET, DEMO_FORECASTS, DEMO_NEWS } from "./demo";
import { useLiveFeed } from "./feed";
import { WorldMap } from "./WorldMap";
import {
	ANCHORS,
	BUFFER_MIN,
	HOT_MIN,
	KIND_LABEL,
	REASON_LABEL,
	TOPIC_COLOR,
	TOPIC_LABEL,
	decide,
	type ForecastCard,
	type NewsItem,
	type Pressure,
	type Verdict,
} from "./model";

const PRESSURES: { id: Pressure; label: string; hint: string }[] = [
	{ id: "normal", label: "NORMAL", hint: "menos de 60% do teto diário de escrita" },
	{ id: "economy", label: "ECONOMIA", hint: "a partir de 60%: só o que tem relevância" },
	{ id: "critical", label: "CRÍTICO", hint: "a partir de 85%: só o essencial" },
];
const VERDICT_LABEL: Record<Verdict, string> = { hot: "GRAVA", buffer: "BUFFER", drop: "DESCARTA" };
const pct = (n: number) => `${Math.round(n * 100)}%`;

function Clock() {
	const [now, setNow] = useState(() => new Date());
	useEffect(() => {
		const id = setInterval(() => setNow(new Date()), 1000);
		return () => clearInterval(id);
	}, []);
	return <time dateTime={now.toISOString()}>{now.toISOString().slice(0, 19).replace("T", " ")} UTC</time>;
}

export function CorvoApp() {
	const live = useLiveFeed();
	const [simulated, setSimulated] = useState<Pressure>("normal");
	const [filter, setFilter] = useState<Verdict | "all">("all");
	const [selected, setSelected] = useState<string | null>(null);
	const pressure: Pressure = live ? live.pressure : simulated;
	const budget = live ? live.budget : DEMO_BUDGET;
	const forecasts: ForecastCard[] = live ? live.forecasts : DEMO_FORECASTS;

	const rows = useMemo(
		() => (live ? live.items.map((n) => ({ n: n as NewsItem, verdict: n.verdict as Verdict, reason: n.reason })) : DEMO_NEWS.map((n) => ({ n, ...(({ verdict, reason }) => ({ verdict, reason }))(decide(n, pressure)) }))),
		[live, pressure],
	);
	const counts = useMemo(() => {
		if (live) return { c: { hot: live.totals.hot, buffer: live.totals.buffer, drop: live.totals.dropped } as Record<Verdict, number>, reasons: live.totals.reasons };
		const c: Record<Verdict, number> = { hot: 0, buffer: 0, drop: 0 };
		const reasons: Record<string, number> = {};
		for (const r of rows) {
			c[r.verdict]++;
			if (r.verdict === "drop") reasons[r.reason] = (reasons[r.reason] ?? 0) + 1;
		}
		return { c, reasons };
	}, [live, rows]);
	const total = live ? live.totals.received : rows.length;
	const shown = rows.filter((r) => (filter === "all" ? true : r.verdict === filter));
	const ticker = rows.filter((r) => r.verdict === "hot");
	const usedPct = Math.min(100, (budget.used / budget.limit) * 100);
	const located = rows.filter((r) => r.verdict !== "drop" && r.n.lat != null).length;

	return (
		<div className="console">
			<header className="bar">
				<div className="logo">
					<span className="logo-mark" aria-hidden="true">▌</span>CORVO<span className="dim"> // HUGIN · MUNIN</span>
				</div>
				<div className="status">
					<Clock />
					<span className={`pill ${live ? "on" : "demo"}`} title={live ? "Dados reais do Oracle via Cloudflare" : "Ainda não chegou nenhum dado real"}>
						{live ? "● AO VIVO" : "○ DEMONSTRAÇÃO · DADOS FICTÍCIOS"}
					</span>
					<span className={`pill p-${pressure}`}>PRESSÃO {PRESSURES.find((p) => p.id === pressure)?.label}</span>
				</div>
			</header>

			{ticker.length > 0 && (
				<div className="ticker" aria-label="Últimas notícias gravadas">
					<div className="ticker-track">
						{[...ticker, ...ticker].map(({ n }, i) => (
							<span key={`${n.id}-${i}`} aria-hidden={i >= ticker.length}>
								<b style={{ color: TOPIC_COLOR[n.topics[0]] ?? "var(--g)" }}>[{(n.topics[0] ? TOPIC_LABEL[n.topics[0]] : "geral").toUpperCase()}]</b> {n.title}
							</span>
						))}
					</div>
				</div>
			)}

			<div className="grid">
				<section className="box map-box" aria-labelledby="t-map">
					<h2 id="t-map">MAPA-MÚNDI <small>{located} notícias localizadas · losangos = âncoras do Pizza Index (sensores ainda desligados)</small></h2>
					<WorldMap items={rows.map((r) => ({ n: r.n, verdict: r.verdict }))} selected={selected} onSelect={setSelected} />
					<ul className="key" aria-label="Legenda de temas">
						{(Object.keys(TOPIC_LABEL) as (keyof typeof TOPIC_LABEL)[]).map((t) => (
							<li key={t}><i style={{ background: TOPIC_COLOR[t] }} /> {TOPIC_LABEL[t]}</li>
						))}
					</ul>
				</section>

				<section className="box gate-box" aria-labelledby="t-gate">
					<h2 id="t-gate">PORTÃO DE ADMISSÃO</h2>
					<p className="muted">Cada notícia passa por: frescor, URL repetida, quase-duplicata, relevância, cota da fonte e pressão do banco.</p>
					<div className="meter" role="img" aria-label={`${budget.used} de ${budget.limit} linhas gravadas hoje`}>
						<div style={{ width: `${usedPct}%` }} className={`fill p-${pressure}`} />
					</div>
					<p className="mono sm">{budget.used.toLocaleString("pt-BR")} / {budget.limit.toLocaleString("pt-BR")} linhas hoje</p>
					<div className="seg" role="radiogroup" aria-label="Pressão do orçamento">
						{PRESSURES.map((p) => (
							<button key={p.id} role="radio" aria-checked={pressure === p.id} disabled={!!live} className={pressure === p.id ? "on" : ""} title={p.hint} onClick={() => setSimulated(p.id)}>
								{p.label}
							</button>
						))}
					</div>
					<p className="mono sm">gravar já ≥ {pct(HOT_MIN[pressure])} · buffer ≥ {pct(BUFFER_MIN[pressure])}</p>
					<div className="funnel" role="img" aria-label={`${total} recebidas: ${counts.c.hot} gravadas, ${counts.c.buffer} em buffer, ${counts.c.drop} descartadas`}>
						{(["hot", "buffer", "drop"] as Verdict[]).map((v) => (
							<div key={v} className={`fb ${v}`} style={{ flexGrow: Math.max(counts.c[v], 0.0001) }}>{counts.c[v] > 0 && <span>{counts.c[v]}</span>}</div>
						))}
					</div>
					<ul className="legend">
						<li><i className="dot hot" /> grava {counts.c.hot}</li>
						<li><i className="dot buffer" /> buffer {counts.c.buffer}</li>
						<li><i className="dot drop" /> descarta {counts.c.drop}</li>
					</ul>
					{Object.keys(counts.reasons).length > 0 && (
						<ul className="log" aria-label="Motivos dos descartes">
							{Object.entries(counts.reasons).map(([r, n]) => <li key={r}><span>{n}×</span> {REASON_LABEL[r] ?? r}</li>)}
						</ul>
					)}
				</section>

				<section className="box feed-box" aria-labelledby="t-feed">
					<div className="row">
						<h2 id="t-feed">FEED TRATADO</h2>
						<div className="seg" role="group" aria-label="Filtrar por decisão">
							{(live ? (["all", "hot", "buffer"] as const) : (["all", "hot", "buffer", "drop"] as const)).map((f) => (
								<button key={f} className={filter === f ? "on" : ""} aria-pressed={filter === f} onClick={() => setFilter(f)}>
									{f === "all" ? "TODAS" : VERDICT_LABEL[f]}
								</button>
							))}
						</div>
					</div>
					{shown.length === 0 && <p className="muted">Nada por aqui ainda.</p>}
					<ul className="feed">
						{shown.map(({ n, verdict, reason }) => (
							<NewsRow key={n.id} n={n} verdict={verdict} reason={reason} selected={selected === n.id} onSelect={() => setSelected(selected === n.id ? null : n.id)} />
						))}
					</ul>
				</section>

				<section className="box fc-box" aria-labelledby="t-fc">
					<h2 id="t-fc">PREVISÕES <small>probabilidade · incerteza · evidências · método</small></h2>
					{forecasts.length === 0 && <p className="muted">Nenhuma previsão publicada ainda.</p>}
					{forecasts.map((f) => <Forecast key={f.id} f={f} />)}
					<h2 className="sub">ÂNCORAS (PIZZA INDEX)</h2>
					<p className="muted">Lugares onde decisões acontecem. O sensor de cada um ainda não está ligado: <a href="https://github.com/henriquesouza1832001-eng/Corvo/blob/hen/docs/corvo/SENSORES.md" rel="noreferrer">como funciona</a>.</p>
					<ul className="anchors">{ANCHORS.map((a) => <li key={a.id}>◇ {a.label}</li>)}</ul>
				</section>
			</div>

			<footer>
				O CORVO não envia ordens nem é recomendação de investimento. Previsão sem histórico fica marcada como “calibrando”. Trades são decididos pelo{" "}
				<a href="https://github.com/th1agx/MNEME" rel="noreferrer">MNEME</a>.
			</footer>
		</div>
	);
}

function NewsRow({ n, verdict, reason, selected, onSelect }: { n: NewsItem; verdict: Verdict; reason: string; selected: boolean; onSelect: () => void }) {
	const ago = n.minutesAgo >= 120 ? `${Math.round(n.minutesAgo / 60)}h` : `${n.minutesAgo}min`;
	return (
		<li className={`news ${verdict}${selected ? " sel" : ""}`}>
			<button className="news-btn" onClick={onSelect} aria-expanded={selected}>
				<span className={`tag ${verdict}`}>{VERDICT_LABEL[verdict]}</span>
				<span className="meta">{n.source} · {ago}{n.region ? ` · ${n.region}` : ""}</span>
				<span className="title">{n.title}</span>
			</button>
			<div className="chips">
				{n.topics.map((t) => <span key={t} className="chip" style={{ color: TOPIC_COLOR[t] }}>{TOPIC_LABEL[t]}</span>)}
				<span className={`chip kind-${n.kind}`}>{KIND_LABEL[n.kind]}</span>
				<span className="chip" title="Nota inicial da fonte, a ser medida pelo histórico">fonte {pct(n.reliability)}</span>
				<span className="chip">relevância {pct(n.relevance)}</span>
			</div>
			{selected && (
				<div className="detail">
					<p className="muted">{REASON_LABEL[reason] ?? reason}</p>
					{verdict !== "drop" && n.assets.length > 0 && (
						<ul className="assets" aria-label="Ativos possivelmente afetados">
							{n.assets.map((a) => (
								<li key={a.symbol} className={a.direction}><b>{a.symbol}</b> {a.direction === "up" ? "▲ alta" : a.direction === "down" ? "▼ queda" : "◆ volátil"} <small>{a.horizon}</small></li>
							))}
						</ul>
					)}
				</div>
			)}
		</li>
	);
}

function Forecast({ f }: { f: ForecastCard }) {
	return (
		<article className="fc">
			<h3>{f.question}</h3>
			<div className="fc-row">
				<span className="fc-p">{pct(f.p)}</span>
				<div className="fc-range" role="img" aria-label={`intervalo de ${pct(f.lo)} a ${pct(f.hi)}`}>
					<div className="fc-band" style={{ left: pct(f.lo), width: pct(f.hi - f.lo) }} />
					<div className="fc-dot" style={{ left: pct(f.p) }} />
				</div>
			</div>
			<small>incerteza {pct(f.lo)}–{pct(f.hi)} · horizonte {f.horizon} · {f.evidences} evidências em {f.sources} fontes · {f.status}</small>
			<small className="dim">método: {f.method}</small>
		</article>
	);
}
