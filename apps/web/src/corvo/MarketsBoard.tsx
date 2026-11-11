import type { MarketSnapshot } from "./feed";

const price = (value: number, symbol: string) => {
	const formatted = new Intl.NumberFormat("en-US", { maximumFractionDigits: value >= 100 ? 2 : value >= 1 ? 3 : 6 }).format(value);
	return symbol.startsWith("USD") ? `${formatted} ${symbol.slice(3)} per USD` : `$${formatted}`;
};

export function MarketsBoard({ data }: { data: MarketSnapshot | null }) {
	return (
		<section className="box market-box" aria-labelledby="t-market">
			<div className="row">
				<h2 id="t-market">ATIVOS OBSERVADOS <small>variação de referência · contexto para validação preditiva</small></h2>
				{data && <span className="muted sm">atualizado {new Date(data.generated_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>}
			</div>
			{!data || data.markets.length === 0 ? (
				<p className="muted">Cotações indisponíveis no momento. A previsão permanece separada destes dados.</p>
			) : (
				<>
					<div className="market-list">
						{data.markets.map((item) => (
							<article key={item.symbol} className="market-tile" title={`${item.source} · ${item.period} · observado ${item.observed_at.length === 10 ? item.observed_at : new Date(item.observed_at).toLocaleString("pt-BR")}`}>
								<div className="row"><b>{item.label}</b><span className={item.change_pct >= 0 ? "market-up" : "market-down"}>{item.change_pct >= 0 ? "+" : ""}{item.change_pct.toFixed(2)}%</span></div>
								<div className="market-price">{price(item.price, item.symbol)}</div>
								<small className="muted">{item.period} · <a href={item.source_url} target="_blank" rel="noreferrer">{item.source}</a></small>
							</article>
						))}
					</div>
					<p className="muted sm market-note">{data.note} · Esses movimentos ainda não são incorporados às previsões publicadas.</p>
				</>
			)}
		</section>
	);
}
