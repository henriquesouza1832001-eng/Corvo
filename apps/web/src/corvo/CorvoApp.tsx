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

/** Do dado à previsão: o que já funciona e o que ainda está sendo construído (honesto; ver docs/corvo/PREDITIVO.md). */
const STAGES: { who: "HUGIN" | "MUNIN"; name: string; text: string; state: "pronto" | "em construção" | "planejado" }[] = [
	{ who: "HUGIN", name: "Lê e filtra", text: "Coleta feeds do mundo, descarta o que não mexe em mercado e classifica o resto.", state: "pronto" },
	{ who: "HUGIN", name: "Junta em eventos", text: "O mesmo fato em várias fontes vira um evento só, com o número de confirmações.", state: "planejado" },
	{ who: "MUNIN", name: "Levanta hipóteses", text: "Liga o tema a ativos candidatos, com direção e horizonte, numa tabela auditável.", state: "em construção" },
	{ who: "MUNIN", name: "Prevê com a taxa-base", text: "Começa pela frequência histórica de cada tipo de evento e diz “dados insuficientes” sem amostra.", state: "em construção" },
	{ who: "MUNIN", name: "Confere e calibra", text: "Compara com o preço real, mede o erro contra a taxa-base e só então ganha confiança.", state: "em construção" },
];

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
	const ticker = rows.filter((r) => r.verdict === "hot").slice(0, 20);
	// velocidade constante (~45 px/s): a duração cresce com o tamanho do texto, em vez de correr mais rápido quando há mais manchetes
	const tickerSecs = Math.max(90, Math.round(ticker.reduce((n, r) => n + r.n.title.length + 24, 0) * 0.17));
	const usedPct = Math.min(100, (budget.used / budget.limit) * 100);
	const sources = live ? live.sources : DEMO_SOURCES;
	const sourceList = Object.entries(sources).sort((x, y) => y[1] - x[1]);
	const read24h = sourceList.reduce((n, [, v]) => n + v, 0);
	const located = rows.filter((r) => r.verdict !== "drop" && r.n.lat != null).length;

	return (
		<div className="console">
			<header className="bar">
				<div className="logo">
					<span className="logo-mark" aria-hidden="true">▌</span>CORVO<span className="dim"> // HUGIN LÊ · MUNIN LEMBRA</span>
				</div>
				<div className="status">
					<Clock />
					<span className={`pill ${live ? "on" : "demo"}`} title={live ? "Dados reais, coletados e enviados à API do CORVO" : "Ainda não chegou nenhum dado real"}>
						{live ? "● AO VIVO" : "○ DEMONSTRAÇÃO · DADOS FICTÍCIOS"}
					</span>
					<span className={`pill p-${pressure}`}>PRESSÃO {PRESSURES.find((p) => p.id === pressure)?.label}</span>
				</div>
			</header>

			{ticker.length > 0 && (
				<div className="ticker" aria-label="Últimas notícias gravadas">
					<div className="ticker-track" style={{ animationDuration: `${tickerSecs}s` }}>
						{[...ticker, ...ticker].map(({ n }, i) => (
							<span key={`${n.id}-${i}`} aria-hidden={i >= ticker.length}>
								<b style={{ color: TOPIC_COLOR[n.topics[0]] ?? "var(--g)" }}>[{(n.topics[0] ? TOPIC_LABEL[n.topics[0]] : "geral").toUpperCase()}]</b> {n.title}
							</span>
						))}
					</div>
				</div>
			)}

			<section className="ravens" aria-labelledby="t-ravens">
				<h2 id="t-ravens" className="vh">Como o Corvo funciona</h2>
				<article className="raven-card">
					<h3>HUGIN <small>pensamento · lê o mundo</small></h3>
					<p>
						Na mitologia nórdica, Hugin e Munin são os dois corvos de Odin: saem todo dia para sobrevoar os nove reinos e voltam ao amanhecer para contar o que viram.
						Hugin é o pensamento. Aqui ele lê as fontes, tira o ruído e entende o que cada notícia significa.
					</p>
					<ol className="flow">
						<li><b>Lê</b> {sourceList.length} fontes: agências, bancos centrais e imprensa de todos os continentes.</li>
						<li><b>Filtra</b> o que já viu, o que é velho, repetido ou fora do assunto. Sobra {total > 0 ? pct(1 - counts.c.drop / total) : "pouco"} do que chegou.</li>
						<li><b>Classifica</b> fato, reportagem, rumor ou opinião. Na dúvida, é só reportagem.</li>
						<li><b>Localiza</b> no mapa e liga o fato aos ativos que ele pode mexer.</li>
					</ol>
				</article>
				<article className="raven-card">
					<h3>MUNIN <small>memória · lembra e aprende</small></h3>
					<p>
						Munin é a memória. Ele guarda o que importa, registra cada previsão antes do resultado e depois compara com o que aconteceu, para saber em quais tipos de previsão o Corvo acerta e em quais não.
					</p>
					<ol className="flow">
						<li><b>Guarda</b> só as notícias aprovadas. Descartada vira apenas um contador e um código curto da URL, por 48 horas.</li>
						<li><b>Registra</b> cada previsão com probabilidade, incerteza, evidências e método.</li>
						<li><b>Confere</b> o resultado e calcula o acerto (hoje: {forecasts.filter((f) => f.status === "calibrando").length} em calibração, sem histórico suficiente).</li>
						<li><b>Esquece</b> com prazo: notícias com 30 dias e estatísticas com 14 dias são apagadas.</li>
					</ol>
				</article>
			</section>

			<section className="path" aria-labelledby="t-path">
				<h2 id="t-path">DO DADO À PREVISÃO <small>como Hugin e Munin viram o preditivo, etapa por etapa</small></h2>
				<ol className="stages">
					{STAGES.map((s, i) => (
						<li key={s.name} className={`stage ${s.who === "HUGIN" ? "h" : "m"}`}>
							<span className="st-n">{i + 1}</span>
							<b>{s.name}</b>
							<small className="st-who">{s.who}</small>
							<p>{s.text}</p>
							<span className={`st-state s-${s.state.replace(" ", "-")}`}>{s.state}</span>
						</li>
					))}
				</ol>
			</section>

			<div className="grid">
				<MarketsBoard data={marketSnapshot} />
				<section className="box map-box" aria-labelledby="t-map">
					<h2 id="t-map">MAPA-MÚNDI <small>{located} notícias localizadas · losangos = pontos de observação (coleta em preparação)</small></h2>
					<WorldMap items={rows.map((r) => ({ n: r.n, verdict: r.verdict }))} selected={selected} onSelect={setSelected} />
					<ul className="key" aria-label="Legenda de temas">
						{(presentTopics.length ? presentTopics : (Object.keys(TOPIC_LABEL) as (keyof typeof TOPIC_LABEL)[])).map((t) => (
							<li key={t}><i style={{ background: TOPIC_COLOR[t] }} /> {TOPIC_LABEL[t]}</li>
						))}
					</ul>
				</section>

				<section className="box gate-box" aria-labelledby="t-gate">
					<h2 id="t-gate">PORTÃO DE ADMISSÃO</h2>
					<p className="muted">O robô avalia cada notícia ANTES de gravar qualquer coisa: frescor, URL repetida, quase-duplicata, relevância, cota da fonte e pressão do banco.</p>
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
							<>
								<h2 className="sub">ATIVIDADE POR HORA <small>lidas · fila · grava</small></h2>
								<HourlyBars data={live.hourly} />
							</>
						)}
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
					<div className="filters">
							<input className="search" type="search" placeholder="buscar por título, fonte ou país" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Buscar no feed" />
							<select className="sel" value={topicFilter} onChange={(e) => setTopicFilter(e.target.value)} aria-label="Filtrar por tema">
								<option value="all">todos os temas</option>
								{presentTopics.map((t) => <option key={t} value={t}>{TOPIC_LABEL[t]}</option>)}
							</select>
						</div>
						<p className="muted sm">{shown.length} de {rows.length} · títulos no idioma original da fonte · clique numa notícia para ver o motivo e os ativos</p>
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
						{sourceList.slice(0, 12).map(([id, n]) => (
							<li key={id}><span className="sname">{id}</span><span className="sbar"><i style={{ width: `${(n / (sourceList[0]?.[1] || 1)) * 100}%` }} /></span><span className="mono">{n.toLocaleString("pt-BR")}</span></li>
						))}
					</ul>
					{sourceList.length === 0 && <p className="muted">Nenhuma fonte reportou ainda.</p>}
				</section>

				<section className="box fc-box" aria-labelledby="t-fc">
					<h2 id="t-fc">PREVISÕES <small>probabilidade · incerteza · evidências · método</small></h2>
					{forecasts.length === 0 && <p className="muted">Nenhuma previsão real publicada. O painel mostra variações observadas acima; o Munin só publicará probabilidade após conectar as séries históricas, validar a amostra e registrar o método.</p>}
					{forecasts.map((f) => <Forecast key={f.id} f={f} />)}
					<h2 className="sub">PONTOS DE OBSERVAÇÃO</h2>
					<p className="muted">Lugares onde decisões acontecem. A coleta de cada um ainda está em preparação.</p>
					<ul className="anchors">{ANCHORS.map((a) => <li key={a.id}>◇ {a.label}</li>)}</ul>
				</section>
			</div>

			<footer>
				O CORVO só coleta, analisa e prevê. Não envia ordens e não é recomendação de investimento. Toda previsão mostra probabilidade, incerteza, evidências e método, e fica marcada como “calibrando” enquanto não tiver histórico de acertos.
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
