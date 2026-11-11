import { Hono } from "hono";
import type { AppEnv } from "../env";
import { cacheControl } from "../lib/cache";

/** Quotes de referência para contexto e avaliação do Munin. Não são dados de execução de ordens. */
export const corvoMarkets = new Hono<AppEnv>();

type MarketPoint = {
	symbol: string;
	label: string;
	price: number;
	change_pct: number;
	period: string;
	observed_at: string;
	source: string;
	source_url: string;
};

const CRYPTO = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"] as const;
const FX = ["EUR", "BRL", "JPY", "GBP", "CNY"] as const;
const FX_LABEL: Record<(typeof FX)[number], string> = { EUR: "USD/EUR", BRL: "USD/BRL", JPY: "USD/JPY", GBP: "USD/GBP", CNY: "USD/CNY" };
const json = (value: unknown) => JSON.stringify(value);

async function getJson<T>(url: string): Promise<T> {
	const response = await fetch(url, { headers: { accept: "application/json", "user-agent": "corvo-market-context/1.0" }, signal: AbortSignal.timeout(8_000) });
	if (!response.ok) throw new Error(`upstream_${response.status}`);
	return response.json() as Promise<T>;
}

async function cryptoPoints(): Promise<MarketPoint[]> {
	const symbols = encodeURIComponent(json(CRYPTO));
	const rows = await getJson<Array<{ symbol: string; lastPrice: string; priceChangePercent: string; closeTime: number }>>(
		`https://data-api.binance.vision/api/v3/ticker/24hr?symbols=${symbols}`,
	);
	return rows.filter((r) => CRYPTO.includes(r.symbol as (typeof CRYPTO)[number]) && Number.isFinite(Number(r.lastPrice)) && Number(r.lastPrice) > 0 && Number.isFinite(Number(r.priceChangePercent)) && Number.isFinite(r.closeTime)).map((r) => ({
		symbol: r.symbol.replace("USDT", ""), label: `${r.symbol.replace("USDT", "")}/USDT`, price: Number(r.lastPrice),
		change_pct: Number(r.priceChangePercent), period: "24h", observed_at: new Date(r.closeTime).toISOString(),
		source: "Binance public market data", source_url: "https://data-api.binance.vision/api/v3/ticker/24hr",
	}));
}

async function fxPoints(): Promise<MarketPoint[]> {
	const end = new Date().toISOString().slice(0, 10);
	const start = new Date(Date.now() - 7 * 86_400_000).toISOString().slice(0, 10);
	const result = await getJson<{ rates: Record<string, Record<string, number>> }>(
		`https://api.frankfurter.dev/v1/${start}..${end}?base=USD&symbols=${FX.join(",")}`,
	);
	const days = Object.keys(result.rates).sort();
	if (days.length < 2) return [];
	const previous = result.rates[days[days.length - 2]];
	const latest = result.rates[days[days.length - 1]];
	return FX.filter((ccy) => Number(previous[ccy]) > 0 && Number(latest[ccy]) > 0).map((ccy) => ({
		symbol: `USD${ccy}`, label: FX_LABEL[ccy], price: latest[ccy], change_pct: ((latest[ccy] / previous[ccy]) - 1) * 100,
		period: `${days[days.length - 2]} → ${days[days.length - 1]}`, observed_at: days[days.length - 1],
		source: "Frankfurter · ECB reference rates", source_url: "https://api.frankfurter.dev/",
	}));
}

corvoMarkets.get("/markets", async (c) => {
	c.header("Cache-Control", cacheControl(300, 900));
	const key = "corvo:markets:v1";
	const cached = await c.env.KV?.get(key);
	if (cached) return c.body(cached, 200, { "Content-Type": "application/json", "X-Corvo-Cache": "hit" });
	const [crypto, fx] = await Promise.allSettled([cryptoPoints(), fxPoints()]);
	const points = [...(crypto.status === "fulfilled" ? crypto.value : []), ...(fx.status === "fulfilled" ? fx.value : [])];
	const body = JSON.stringify({
		generated_at: new Date().toISOString(),
		coverage: { crypto: crypto.status === "fulfilled" && crypto.value.length > 0, fx: fx.status === "fulfilled" && fx.value.length > 0 },
		markets: points,
		errors: { crypto: crypto.status === "rejected" ? "indisponível" : null, fx: fx.status === "rejected" ? "indisponível" : null },
		note: "Variações de referência; cripto em 24h, câmbio na última janela diária disponível. Não são previsões nem índices acionários.",
	});
	if (points.length) await c.env.KV?.put(key, body, { expirationTtl: 300 });
	return c.body(body, 200, { "Content-Type": "application/json", "X-Corvo-Cache": "miss" });
});
