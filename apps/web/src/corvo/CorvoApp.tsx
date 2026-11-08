import { useMemo, useState } from "react";
import { DEMO_BUDGET, DEMO_FORECASTS, DEMO_NEWS } from "./demo";
import { useLiveFeed } from "./feed";
import {
	BUFFER_MIN,
	HOT_MIN,
	KIND_LABEL,
	REASON_LABEL,
	TOPIC_LABEL,
	decide,
	type ForecastCard,
	type NewsItem,
	type Pressure,
	type Verdict,
} from "./model";

const PRESSURES: { id: Pressure; label: string; hint: string }[] = [
	{ id: "normal", label: "normal", hint: "menos de 60 mil linhas gravadas hoje" },
	{ id: "economy", label: "economia", hint: "a partir de 60 mil: só o que tem relevância" },
	{ id: "critical", label: "crítico", hint: "a partir de 85 mil: só o essencial" },
];
const VERDICT_LABEL: Record<Verdict, string> = { hot: "grava já", buffer: "buffer", drop: "descartada" };
const pct = (n: number) => `${Math.round(n * 100)}%`;

function Raven({ size = 28 }: { size?: number }) {
	return (
		<svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className="raven">
			<path d="M3 21c5-1 7-4 9-8 2-4 6-6 11-5l5-3-2 5c1 3 0 6-3 8-2 2-5 3-8 3l-2 5-2-5c-3 1-6 1-8 0z" fill="currentColor" />
			<circle cx="22" cy="11" r="1.2" fill="var(--bg)" />
		</svg>
	);
}

export function CorvoApp() {
	const live = useLiveFeed();
	const [simulated, setSimulated] = useState<Pressure>("normal");
	const [filter, setFilter] = useState<Verdict | "all">("all");
	const pressure: Pressure = live ? live.pressure : simulated;
	const budget = live ? live.budget : DEMO_BUDGET;
	const forecasts = live ? live.forecasts : DEMO_FORECASTS;

	const rows = useMemo(
		() => (live ? live.items.map((n) => ({ n, d: { verdict: n.verdict as Verdict, reason: n.reason } })) : DEMO_NEWS.map((n) => ({ n, d: decide(n, pressure) }))),
		[live, pressure],
	);
	const counts = useMemo(() => {
		if (live) return { c: { hot: live.totals.hot, buffer: live.totals.buffer, drop: live.totals.dropped } as Record<Verdict, number>, reasons: live.totals.reasons };
		const c: Record<Verdict, number> = { hot: 0, buffer: 0, drop: 0 };
		const reasons: Record<string, number> = {};
		for (const { d } of rows) {
			c[d.verdict]++;
			if (d.verdict === "drop") reasons[d.reason] = (reasons[d.reason] ?? 0) + 1;
		}
		return { c, reasons };
	}, [live, rows]);
	const shown = rows.filter(({ d }) => filter === "all" || d.verdict === filter);
	const total = live ? live.totals.received : rows.length;

	return (
		<>
			<header className="top">
				<div className="brand">
					<Raven />
					<div>
						<h1>CORVO</h1>
						<p>Hugin e Munin sobrevoam o mundo e voltam com o que viram.</p>
					</div>
				</div>
				{live ? (
					<span className="badge live" title="Dados reais vindos do Oracle via Cloudflare">ao vivo · {new Date(live.generatedAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
				) : (
					<span className="badge" title="Ainda não chegou nenhum dado real do Oracle">demonstração · dados fictícios</span>
				)}
			</header>

			<main>
				<section className="intro">
					<h2>Um radar de notícias que vira previsão calibrada.</h2>
					<p>
						O Corvo lê política, catástrofes e economia do mundo todo, separa o que é fato do que é rumor e estima o efeito sobre
						cripto, ações, câmbio e commodities. Toda previsão sai com probabilidade, incerteza, evidências e método. Nunca com ordem de compra ou venda.
					</p>
					<div className="ravens">
						<article>
							<h3>Hugin · pensamento</h3>
							<p>Lê as fontes, filtra o ruído, junta as matérias do mesmo acontecimento e descobre quais ativos ele toca.</p>
						</article>
						<article>
							<h3>Munin · memória</h3>
							<p>Guarda cada previsão e o que de fato aconteceu depois, e usa esse histórico para calibrar as próximas probabilidades.</p>
						</article>
					</div>
				</section>

				<section aria-labelledby="funil">
					<h2 id="funil">Como o Corvo trata a notícia</h2>
					<p className="lede">
						Antes de gravar qualquer coisa, cada item passa por um portão. Ele protege o banco (o D1 grátis aceita 100 mil linhas por dia)
						e decide entre gravar já, guardar em lote ou descartar, sempre dizendo o motivo.
					</p>

					<ol className="steps">
						<li><b>1 · Frescor</b><span>notícia velha não entra</span></li>
						<li><b>2 · Duplicata</b><span>mesma URL, ignorando rastreio</span></li>
						<li><b>3 · Quase-duplicata</b><span>mesmo fato em fontes diferentes</span></li>
						<li><b>4 · Relevância</b><span>política, catástrofe, juros, cripto, mercado</span></li>
						<li><b>5 · Cota da fonte</b><span>nenhuma fonte inunda o painel</span></li>
						<li><b>6 · Pressão</b><span>quanto mais cheio o orçamento, mais rígido o corte</span></li>
					</ol>

					<div className="panel">
						<div className="panel-head">
							<div>
								<strong>Pressão do orçamento</strong>
								<small>
									{budget.used.toLocaleString("pt-BR")} de {budget.limit.toLocaleString("pt-BR")} linhas hoje.{live ? "" : " Experimente os outros modos."}
								</small>
							</div>
							<div className="seg" role="radiogroup" aria-label="Pressão do orçamento">
								{PRESSURES.map((p) => (
									<button key={p.id} role="radio" aria-checked={pressure === p.id} disabled={!!live} className={pressure === p.id ? "on" : ""} title={p.hint} onClick={() => setSimulated(p.id)}>
										{p.label}
									</button>
								))}
							</div>
						</div>
						<p className="cuts">
							Corte para gravar já: relevância ≥ <b>{pct(HOT_MIN[pressure])}</b> · para entrar no buffer: ≥ <b>{pct(BUFFER_MIN[pressure])}</b>
						</p>

						<div className="funnel" role="img" aria-label={`${total} recebidas: ${counts.c.hot} gravadas, ${counts.c.buffer} em buffer, ${counts.c.drop} descartadas`}>
							{(["hot", "buffer", "drop"] as Verdict[]).map((v) => (
								<div key={v} className={`seg-bar ${v}`} style={{ flexGrow: Math.max(counts.c[v], 0.0001) }}>
									{counts.c[v] > 0 && <span>{counts.c[v]}</span>}
								</div>
							))}
						</div>
						<ul className="legend">
							<li><i className="dot hot" /> grava já · {counts.c.hot}</li>
							<li><i className="dot buffer" /> buffer em lote · {counts.c.buffer}</li>
							<li><i className="dot drop" /> descartadas · {counts.c.drop}</li>
						</ul>
						{counts.c.drop > 0 && (
							<p className="reasons">
								Motivos dos descartes:{" "}
								{Object.entries(counts.reasons).map(([r, n]) => `${REASON_LABEL[r] ?? r} (${n})`).join(" · ")}
							</p>
						)}
					</div>
				</section>

				<section aria-labelledby="feed">
					<div className="row">
						<h2 id="feed">Notícias tratadas</h2>
						<div className="seg" role="group" aria-label="Filtrar por decisão">
							{(live ? (["all", "hot", "buffer"] as const) : (["all", "hot", "buffer", "drop"] as const)).map((f) => (
								<button key={f} className={filter === f ? "on" : ""} aria-pressed={filter === f} onClick={() => setFilter(f)}>
									{f === "all" ? "todas" : VERDICT_LABEL[f]}
								</button>
							))}
						</div>
					</div>
					<ul className="feed">
						{shown.map(({ n, d }) => (
							<NewsRow key={n.id} n={n} verdict={d.verdict} reason={d.reason} />
						))}
					</ul>
				</section>

				<section aria-labelledby="prev">
					<h2 id="prev">Previsões</h2>
					<p className="lede">
						Uma previsão sem histórico de acerto fica marcada como <em>calibrando</em>. Sinal fraco não é fato, e alegação política não vira fato.
					</p>
					<div className="forecasts">
						{forecasts.length === 0 && <p className="lede">Nenhuma previsão publicada ainda.</p>}
						{forecasts.map((f) => (
							<Forecast key={f.id} f={f} />
						))}
					</div>
				</section>
			</main>

			<footer>
				<p>
					O Corvo não envia ordens e não é recomendação de investimento. As decisões de trade ficam com o{" "}
					<a href="https://github.com/th1agx/MNEME" rel="noreferrer">MNEME</a>, que mede cada resultado em simulado antes de qualquer dinheiro real.
				</p>
			</footer>
		</>
	);
}

function NewsRow({ n, verdict, reason }: { n: NewsItem; verdict: Verdict; reason: string }) {
	const ago = n.minutesAgo >= 120 ? `há ${Math.round(n.minutesAgo / 60)} h` : `há ${n.minutesAgo} min`;
	return (
		<li className={`news ${verdict}`}>
			<div className="news-top">
				<span className={`tag ${verdict}`}>{VERDICT_LABEL[verdict]}</span>
				<span className="meta">{n.source} · {ago}</span>
			</div>
			<h3>{n.title}</h3>
			<div className="chips">
				{n.topics.map((t) => <span key={t} className="chip">{TOPIC_LABEL[t]}</span>)}
				<span className={`chip kind-${n.kind}`}>{KIND_LABEL[n.kind]}</span>
				<span className="chip" title="Nota inicial da fonte, a ser medida pelo histórico">fonte {pct(n.reliability)}</span>
			</div>
			<div className="rel" title={`relevância ${pct(n.relevance)}`}>
				<div className="rel-bar"><div style={{ width: pct(n.relevance) }} /></div>
				<small>relevância {pct(n.relevance)}</small>
			</div>
			<p className="why">{REASON_LABEL[reason] ?? reason}</p>
			{verdict !== "drop" && n.assets.length > 0 && (
				<ul className="assets" aria-label="Ativos possivelmente afetados">
					{n.assets.map((a) => (
						<li key={a.symbol} className={a.direction}>
							<b>{a.symbol}</b> {a.direction === "up" ? "▲ alta" : a.direction === "down" ? "▼ queda" : "◆ volátil"} <small>{a.horizon}</small>
						</li>
					))}
				</ul>
			)}
		</li>
	);
}

function Forecast({ f }: { f: ForecastCard }) {
	return (
		<article className="fc">
			<h3>{f.question}</h3>
			<div className="fc-p">{pct(f.p)}</div>
			<div className="fc-range" role="img" aria-label={`intervalo de ${pct(f.lo)} a ${pct(f.hi)}`}>
				<div className="fc-band" style={{ left: pct(f.lo), width: pct(f.hi - f.lo) }} />
				<div className="fc-dot" style={{ left: pct(f.p) }} />
			</div>
			<small>incerteza: {pct(f.lo)} a {pct(f.hi)} · horizonte {f.horizon}</small>
			<dl>
				<dt>evidências</dt><dd>{f.evidences} em {f.sources} fontes</dd>
				<dt>método</dt><dd>{f.method}</dd>
				<dt>estado</dt><dd>{f.status}</dd>
			</dl>
		</article>
	);
}
