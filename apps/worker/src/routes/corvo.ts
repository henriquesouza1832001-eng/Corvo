import { Hono } from "hono";
import { z } from "zod";
import type { AppEnv } from "../env";
import { engineAuthorized } from "../lib/auth";
import { budgetMode, DAILY_LIMIT, utcDay } from "../lib/budget";
import { cacheControl } from "../lib/cache";

/**
 * API do painel do CORVO. O Oracle (cérebro, junto do MNEME) EMPURRA os dados aqui com `POST /api/corvo/ingest`;
 * o painel só LÊ. O KV guarda o instantâneo do feed por alguns segundos para o painel não bater no D1 a cada visita.
 */
export const corvo = new Hono<AppEnv>();

const iso = z.iso.datetime();
const prob = z.number().min(0).max(1);
const newsSchema = z.object({
	item_id: z.string().min(1).max(80),
	source_id: z.string().min(1).max(80),
	source_reliability: prob,
	title: z.string().min(1).max(400),
	url: z.string().url().max(1000).nullable(),
	published_at: iso,
	verdict: z.enum(["hot", "buffer"]), // descartadas nunca chegam aqui: só entram nas estatísticas
	reason: z.string().max(60),
	relevance: prob,
	kind: z.enum(["fato", "reportagem", "rumor", "opiniao", "previsao"]),
	topics: z.array(z.string().max(30)).max(8),
	assets: z.array(z.object({ symbol: z.string().max(20), direction: z.enum(["up", "down", "volatile"]), horizon: z.string().max(10) })).max(12),
});
const statsSchema = z.object({
	bucket: iso,
	pressure: z.enum(["normal", "economy", "critical"]),
	received: z.number().int().min(0),
	hot: z.number().int().min(0),
	buffer: z.number().int().min(0),
	dropped: z.number().int().min(0),
	reasons: z.record(z.string().max(40), z.number().int().min(0)),
});
const forecastSchema = z.object({
	forecast_id: z.string().min(1).max(80),
	question: z.string().min(1).max(300),
	probability: prob,
	interval_low: prob,
	interval_high: prob,
	evidences: z.number().int().min(0),
	sources: z.number().int().min(0),
	method: z.string().min(1).max(200), // previsão sem método registrado não entra
	horizon: z.string().max(10),
	status: z.enum(["aberta", "calibrando", "resolvida"]),
});
const batchSchema = z.object({
	news: z.array(newsSchema).max(200).default([]),
	stats: z.array(statsSchema).max(48).default([]),
	forecasts: z.array(forecastSchema).max(50).default([]),
});

const FEED_KEY = "corvo:feed:v1";
const FEED_TTL = 60; // o mínimo do KV é 60 s

corvo.post("/ingest", async (c) => {
	if (!engineAuthorized(c.req.header("Authorization"), c.env.INGEST_TOKEN)) return c.json({ error: "unauthorized" }, 401);
	const parsed = batchSchema.safeParse(await c.req.json().catch(() => null));
	if (!parsed.success) return c.json({ error: "invalid_batch", issues: parsed.error.issues.slice(0, 5) }, 400);
	const { news, stats, forecasts } = parsed.data;
	if (forecasts.some((f) => f.interval_low > f.probability || f.interval_high < f.probability)) {
		return c.json({ error: "invalid_batch", detail: "a probabilidade precisa estar dentro do intervalo de incerteza" }, 400);
	}
	const db = c.env.DB;
	const now = new Date().toISOString();
	const stmts = [
		...news.map((n) =>
			db
				.prepare(
					`INSERT INTO corvo_news (item_id,source_id,source_reliability,title,url,published_at,ingested_at,verdict,reason,relevance,kind,topics,assets)
					 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13)
					 ON CONFLICT(item_id) DO UPDATE SET verdict=excluded.verdict, reason=excluded.reason, relevance=excluded.relevance, assets=excluded.assets`,
				)
				.bind(n.item_id, n.source_id, n.source_reliability, n.title, n.url, n.published_at, now, n.verdict, n.reason, n.relevance, n.kind, JSON.stringify(n.topics), JSON.stringify(n.assets)),
		),
		...stats.map((s) =>
			db
				.prepare(
					`INSERT INTO corvo_gate_stats (bucket,pressure,received,hot,buffer,dropped,reasons,updated_at) VALUES (?1,?2,?3,?4,?5,?6,?7,?8)
					 ON CONFLICT(bucket) DO UPDATE SET pressure=excluded.pressure, received=excluded.received, hot=excluded.hot, buffer=excluded.buffer, dropped=excluded.dropped, reasons=excluded.reasons, updated_at=excluded.updated_at`,
				)
				.bind(s.bucket, s.pressure, s.received, s.hot, s.buffer, s.dropped, JSON.stringify(s.reasons), now),
		),
		...forecasts.map((f) =>
			db
				.prepare(
					`INSERT INTO corvo_forecasts (forecast_id,question,probability,interval_low,interval_high,evidences,sources,method,horizon,status,updated_at)
					 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11)
					 ON CONFLICT(forecast_id) DO UPDATE SET probability=excluded.probability, interval_low=excluded.interval_low, interval_high=excluded.interval_high,
					   evidences=excluded.evidences, sources=excluded.sources, method=excluded.method, status=excluded.status, updated_at=excluded.updated_at`,
				)
				.bind(f.forecast_id, f.question, f.probability, f.interval_low, f.interval_high, f.evidences, f.sources, f.method, f.horizon, f.status, now),
		),
	];
	if (stmts.length === 0) return c.json({ ok: true, written: 0 });
	const written = stmts.length;
	// contabiliza no orçamento diário (mesma tabela do ingest antigo), ~2 linhas por item (linha + índice)
	stmts.push(
		db.prepare("INSERT INTO write_budget (day,rows) VALUES (?1,?2) ON CONFLICT(day) DO UPDATE SET rows = rows + excluded.rows").bind(utcDay(), written * 2),
	);
	await db.batch(stmts);
	await c.env.KV?.delete(FEED_KEY); // o próximo GET remonta o instantâneo
	return c.json({ ok: true, written });
});

const parseJson = <T,>(s: string, fallback: T): T => {
	try {
		return JSON.parse(s) as T;
	} catch {
		return fallback;
	}
};

async function buildFeed(db: D1Database) {
	const [news, stats, forecasts, budget] = await Promise.all([
		db.prepare("SELECT * FROM corvo_news ORDER BY published_at DESC LIMIT 100").all<Record<string, unknown>>(),
		db.prepare("SELECT * FROM corvo_gate_stats ORDER BY bucket DESC LIMIT 24").all<Record<string, unknown>>(),
		db.prepare("SELECT * FROM corvo_forecasts ORDER BY updated_at DESC LIMIT 20").all<Record<string, unknown>>(),
		db.prepare("SELECT rows FROM write_budget WHERE day = ?1").bind(utcDay()).first<{ rows: number }>(),
	]);
	const used = budget?.rows ?? 0;
	return {
		generated_at: new Date().toISOString(),
		pressure: budgetMode(used),
		budget: { used, limit: DAILY_LIMIT },
		news: news.results.map((r) => ({ ...r, topics: parseJson(String(r.topics), []), assets: parseJson(String(r.assets), []) })),
		stats: stats.results.map((r) => ({ ...r, reasons: parseJson(String(r.reasons), {}) })),
		forecasts: forecasts.results,
	};
}

/** Tudo que o painel mostra, numa chamada só. */
corvo.get("/feed", async (c) => {
	c.header("Cache-Control", cacheControl(15));
	const cached = await c.env.KV?.get(FEED_KEY);
	if (cached) return c.body(cached, 200, { "Content-Type": "application/json", "X-Corvo-Cache": "hit" });
	const body = JSON.stringify(await buildFeed(c.env.DB));
	await c.env.KV?.put(FEED_KEY, body, { expirationTtl: FEED_TTL });
	return c.body(body, 200, { "Content-Type": "application/json", "X-Corvo-Cache": "miss" });
});

/** O Oracle lê a pressão do orçamento antes de decidir quanto empurrar (o portão aperta quando o D1 enche). */
corvo.get("/pressure", async (c) => {
	if (!engineAuthorized(c.req.header("Authorization"), c.env.INGEST_TOKEN)) return c.json({ error: "unauthorized" }, 401);
	const row = await c.env.DB.prepare("SELECT rows FROM write_budget WHERE day = ?1").bind(utcDay()).first<{ rows: number }>();
	const used = row?.rows ?? 0;
	return c.json({ pressure: budgetMode(used), used, limit: DAILY_LIMIT });
});
