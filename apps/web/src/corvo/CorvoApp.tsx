import { useEffect, useMemo, useState } from "react";
import { DEMO_BUDGET, DEMO_NEWS, DEMO_SOURCES } from "./demo";
import { useLiveFeed, useMarketSnapshot } from "./feed";
import { MarketsBoard } from "./MarketsBoard";
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
const VERDICT_LABEL: Record<Verdict, string> = { hot: "GRAVA", buffer: "FILA", drop: "DESCARTA" };

function HourlyBars({ data }: { data: { bucket: string; received: number; hot: number; buffer: number; dropped: number }[] }) {
	const max = Math.max(1, ...data.map((d) => d.received));
	return (
		<div className="hourly" role="img" aria-label="Notícias lidas por hora e o que foi gravado">
			{data.map((d) => (
				<div key={d.bucket} className="hbar" title={`${new Date(d.bucket).toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}: ${d.received} lidas · ${d.hot} grava · ${d.buffer} fila · ${d.dropped} descartadas`}>
					<i className="hd" style={{ height: `${(d.dropped / max) * 100}%` }} />
					<i className="hb" style={{ height: `${(d.buffer / max) * 100}%` }} />
					<i className="hh" style={{ height: `${(d.hot / max) * 100}%` }} />
				</div>
			))}
		</div>
	);
}
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
	const [query, setQuery] = useState("");
	const [topicFilter, setTopicFilter] = useState<string>("all");
	const pressure: Pressure = live ? live.pressure : simulated;
	const budget = live ? live.budget : DEMO_BUDGET;
	const marketSnapshot = useMarketSnapshot();
	// Números de previsão de demonstração já foram removidos: sem resultado real, não publicar odds fictícias.
	const forecasts: ForecastCard[] = live ? live.forecasts : [];

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
	const q = query.trim().toLowerCase();
	const shown = rows.filter(
		(r) =>
			(filter === "all" ? true : r.verdict === filter) &&
			(topicFilter === "all" ? true : r.n.topics.includes(topicFilter as never)) &&
			(q === "" || `${r.n.title} ${r.n.source} ${r.n.region ?? ""}`.toLowerCase().includes(q)),
	);
	const presentTopics = Array.from(new Set(rows.filter((r) => r.verdict !== "drop").flatMap((r) => r.n.topics)));
	const usedPct = Math.min(100, (budget.used / budget.limit) * 100);
	const sources = live ? live.sources : DEMO_SOURCES;
	const sourceList = Object.entries(sources).sort((x, y) => y[1] - x[1]);
	const read24h = sourceList.reduce((n, [, v]) => n + v, 0);
	const located = rows.filter((r) => r.verdict !== "drop" && r.n.lat != null).length;

	return (
		<div className="console">
			<header className="bar">
				<div className="logo">
					<span className="logo-mark" aria-hidden="true">▌</span>CORVO<span className="dim"> // RADAR GLOBAL</span>
				</div>
				<div className="status">
					<Clock />
					<span className={`pill ${live ? "on" : "demo"}`} title={live ? "Dados reais, coletados e enviados à API do CORVO" : "Ainda não chegou nenhum dado real"}>
						{live ? "● AO VIVO" : "○ DEMONSTRAÇÃO · DADOS FICTÍCIOS"}
					</span>
					<span className={`pill p-${pressure}`}>PRESSÃO {PRESSURES.find((p) => p.id === pressure)?.label}</span>
				</div>
			</header>

			<section className="summary" aria-label="Resumo da coleta">
				<Metric label={live ? "ITENS · 24H" : "ITENS DEMO"} value={live ? live.totals.received.toLocaleString("pt-BR") : total.toLocaleString("pt-BR")} />
				<Metric label="FONTES COM DADOS" value={sourceList.length.toLocaleString("pt-BR")} />
				<Metric label="ACEITOS" value={(counts.c.hot + counts.c.buffer).toLocaleString("pt-BR")} />
				<Metric label="DESCARTADOS" value={counts.c.drop.toLocaleString("pt-BR")} />
				<Metric label="PREVISÕES REAIS" value={forecasts.length.toLocaleString("pt-BR")} />
			</section>

			<details className="about">
				<summary>ESCOPO E REGRAS DO MOTOR</summary>
				<p>Hugin coleta e filtra notícias. Munin testa hipóteses contra preços históricos; só publica previsão com amostra, intervalo, evidências e método suficientes.</p>
				<p>Ativos disponíveis nesta tela: cripto e câmbio de referência. Índices acionários e previsão de impacto por notícia ainda não estão ligados ao painel.</p>
			</details>

			<div className="grid">
				<MarketsBoard data={marketSnapshot} />
				<section className="box gate-box" aria-labelledby="t-gate">
					<h2 id="t-gate">COLETA <small>{total.toLocaleString("pt-BR")} itens</small></h2>
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
					<p className="mono sm">grava já com relevância ≥ {pct(HOT_MIN[pressure])} · vai para a fila com ≥ {pct(BUFFER_MIN[pressure])}</p>
					<div className="funnel" role="img" aria-label={`${total} recebidas: ${counts.c.hot} gravadas, ${counts.c.buffer} na fila, ${counts.c.drop} descartadas`}>
						{(["hot", "buffer", "drop"] as Verdict[]).map((v) => (
							<div key={v} className={`fb ${v}`} style={{ flexGrow: Math.max(counts.c[v], 0.0001) }}>{counts.c[v] > 0 && <span>{counts.c[v]}</span>}</div>
						))}
					</div>
					<ul className="legend">
						<li><i className="dot hot" /> grava {counts.c.hot}</li>
						<li><i className="dot buffer" /> fila {counts.c.buffer}</li>
						<li><i className="dot drop" /> descarta {counts.c.drop}</li>
					</ul>
					{live && live.hourly.length > 1 && (
						<details className="hourly-details">
							<summary>VOLUME POR HORA</summary>
							<HourlyBars data={live.hourly} />
						</details>
					)}
					{Object.keys(counts.reasons).length > 0 && (
						<details className="drop-reasons">
							<summary>MOTIVOS DO DESCARTE</summary>
							<ul className="log" aria-label="Motivos dos descartes">
								{Object.entries(counts.reasons).map(([r, n]) => <li key={r}><span>{n}×</span> {REASON_LABEL[r] ?? r}</li>)}
							</ul>
						</details>
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
					<div className="filters">
							<input className="search" type="search" placeholder="buscar por título, fonte ou país" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Buscar no feed" />
							<select className="sel" value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} aria-label="Filtrar por tema">
								<option value="all">todos os temas</option>
								{presentTopics.map((t) => <option key={t} value={t}>{TOPIC_LABEL[t]}</option>)}
							</select>
						</div>
						<p className="muted sm">{shown.length}/{rows.length} itens · selecione um para ver origem e sinais</p>
						{shown.length === 0 && <p className="muted">Nada por aqui com esse filtro.</p>}
					<ul className="feed">
						{shown.map(({ n, verdict, reason }) => (
							<NewsRow key={n.id} n={n} verdict={verdict} reason={reason} selected={selected === n.id} onSelect={() => setSelected(selected === n.id ? null : n.id)} />
						))}
					</ul>
				</section>

				<section className="box src-box" aria-labelledby="t-src">
					<h2 id="t-src">FONTES ATIVAS <small>{sourceList.length} fontes · {read24h.toLocaleString("pt-BR")} notícias lidas em 24 h</small></h2>
					<ul className="sources">
						{sourceList.slice(0, 16).map(([id, n]) => (
							<li key={id}><span className="sname">{id}</span><span className="sbar"><i style={{ width: `${(n / (sourceList[0]?.[1] || 1)) * 100}%` }} /></span><span className="mono">{n.toLocaleString("pt-BR")}</span></li>
						))}
					</ul>
					{sourceList.length === 0 && <p className="muted">Nenhuma fonte reportou ainda.</p>}
				</section>

				<section className="box fc-box" aria-labelledby="t-fc">
					<h2 id="t-fc">MUNIN · PREVISÕES <small>{forecasts.length ? `${forecasts.length} abertas` : "aguardando amostra"}</small></h2>
					{forecasts.length === 0 && <p className="muted">Sem previsões publicadas · mínimo: 30 resultados históricos por hipótese.</p>}
					{forecasts.map((f) => <Forecast key={f.id} f={f} />)}
					<details className="anchors-details">
						<summary>PONTOS DE OBSERVAÇÃO</summary>
						<ul className="anchors">{ANCHORS.map((a) => <li key={a.id}>◇ {a.label}</li>)}</ul>
					</details>
				</section>

				<section className="box map-box" aria-labelledby="t-map">
					<h2 id="t-map">MAPA <small>{located} localizadas</small></h2>
					<WorldMap items={rows.map((r) => ({ n: r.n, verdict: r.verdict }))} selected={selected} onSelect={setSelected} />
					<ul className="key" aria-label="Temas presentes">
						{presentTopics.map((t) => <li key={t}><i style={{ background: TOPIC_COLOR[t] }} /> {TOPIC_LABEL[t]}</li>)}
					</ul>
				</section>
			</div>

			<footer>Referências de mercado não são previsões. O Munin exige amostra histórica e calibração.</footer>
		</div>
	);
}

function Metric({ label, value }: { label: string; value: string }) {
	return <article className="metric"><small>{label}</small><b>{value}</b></article>;
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
