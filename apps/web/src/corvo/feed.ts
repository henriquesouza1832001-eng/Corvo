import { useEffect, useState } from "react";
import type { AssetImpact, ForecastCard, Kind, NewsItem, Pressure, Topic } from "./model";

export const API_URL: string = import.meta.env.VITE_API_URL || "https://corvo-api.henriquesouza.workers.dev";

interface ApiNews {
	item_id: string; source_id: string; source_reliability: number; title: string; published_at: string;
	verdict: "hot" | "buffer"; reason: string; relevance: number; kind: Kind; topics: Topic[]; assets: AssetImpact[];
	lat: number | null; lon: number | null; region: string | null;
}
interface ApiForecast {
	forecast_id: string; question: string; probability: number; interval_low: number; interval_high: number;
	evidences: number; sources: number; method: string; horizon: string; status: "aberta" | "calibrando" | "resolvida";
}
interface ApiStats { received: number; hot: number; buffer: number; dropped: number; reasons: Record<string, number> }
export interface ApiFeed {
	generated_at: string; pressure: Pressure; budget: { used: number; limit: number };
	news: ApiNews[]; stats: ApiStats[]; forecasts: ApiForecast[];
}

export interface LiveView {
	pressure: Pressure;
	budget: { used: number; limit: number };
	items: (NewsItem & { verdict: "hot" | "buffer"; reason: string })[];
	totals: { received: number; hot: number; buffer: number; dropped: number; reasons: Record<string, number> };
	forecasts: ForecastCard[];
	generatedAt: string;
}

export function toView(f: ApiFeed): LiveView {
	const now = Date.now();
	const totals = { received: 0, hot: 0, buffer: 0, dropped: 0, reasons: {} as Record<string, number> };
	for (const s of f.stats) {
		totals.received += s.received; totals.hot += s.hot; totals.buffer += s.buffer; totals.dropped += s.dropped;
		for (const [k, v] of Object.entries(s.reasons)) totals.reasons[k] = (totals.reasons[k] ?? 0) + v;
	}
	return {
		pressure: f.pressure,
		budget: f.budget,
		generatedAt: f.generated_at,
		totals,
		items: f.news.map((n) => ({
			id: n.item_id, source: n.source_id, reliability: n.source_reliability, title: n.title,
			minutesAgo: Math.max(0, Math.round((now - Date.parse(n.published_at)) / 60_000)),
			topics: n.topics, relevance: n.relevance, kind: n.kind, assets: n.assets, verdict: n.verdict, reason: n.reason,
			lat: n.lat, lon: n.lon, region: n.region,
		})),
		forecasts: f.forecasts.map((x) => ({
			id: x.forecast_id, question: x.question, p: x.probability, lo: x.interval_low, hi: x.interval_high,
			evidences: x.evidences, sources: x.sources, method: x.method, horizon: x.horizon,
			status: x.status === "resolvida" ? "aberta" : x.status,
		})),
	};
}

/** Busca o feed do Cloudflare a cada 30 s. `null` = ainda sem dados reais (API fora do ar ou vazia): a UI cai na demonstração. */
export function useLiveFeed(): LiveView | null {
	const [view, setView] = useState<LiveView | null>(null);
	useEffect(() => {
		let alive = true;
		const load = async () => {
			try {
				const r = await fetch(`${API_URL}/api/corvo/feed`);
				if (!r.ok) throw new Error(String(r.status));
				const v = toView((await r.json()) as ApiFeed);
				if (alive) setView(v.items.length > 0 || v.totals.received > 0 ? v : null);
			} catch {
				if (alive) setView(null);
			}
		};
		void load();
		// Poupa leituras do banco: não consulta com a aba escondida e recarrega ao voltar.
		const id = setInterval(() => { if (!document.hidden) void load(); }, 30_000);
		const onVis = () => { if (!document.hidden) void load(); };
		document.addEventListener("visibilitychange", onVis);
		return () => { alive = false; clearInterval(id); document.removeEventListener("visibilitychange", onVis); };
	}, []);
	return view;
}
