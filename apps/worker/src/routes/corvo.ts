import { Hono } from "hono";
import { z } from "zod";
import type { AppEnv } from "../env";
import { engineAuthorized } from "../lib/auth";
import { utcDay, type BudgetMode } from "../lib/budget";
import { cacheControl } from "../lib/cache";

/**
 * API do painel do CORVO. O coletor (Python, no GitHub Actions ou num servidor) EMPURRA os dados aqui com `POST /api/corvo/ingest`;
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
	lat: z.number().min(-90).max(90).nullable().default(null),
	lon: z.number().min(-180).max(180).nullable().default(null),
	region: z.string().max(40).nullable().default(null),
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
	sources: z.record(z.string().max(60), z.number().int().min(0)).default({}),
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

/** Limite diário de linhas gravadas. D1 grátis = 100 mil; no Turso o limite é mensal, então ajuste DAILY_WRITE_LIMIT (ex.: 300000). */
const dailyLimit = (env: { DAILY_WRITE_LIMIT?: string }) => Math.max(1000, Number(env.DAILY_WRITE_LIMIT) || 100_000);
const modeFor = (used: number, limit: number): BudgetMode => (used >= limit * 0.85 ? "critical" : used >= limit * 0.6 ? "economy" : "normal");
const RETAIN_NEWS_DAYS = 30;
const RETAIN_STATS_DAYS = 14;

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
	// Teto de escrita: o Worker é a última defesa, mesmo que o Oracle erre. economia = sem buffer; crítico = só HOT muito relevante; no limite = sem notícias.
	const limit = dailyLimit(c.env);
	const usedRow = await db.prepare("SELECT rows FROM write_budget WHERE day = ?1").bind(utcDay()).first<{ rows: number }>();
	const used = usedRow?.rows ?? 0;
	const mode = modeFor(used, limit);
	const admitted = used >= limit ? [] : mode === "normal" ? news : mode === "economy" ? news.filter((n) => n.verdict === "hot") : news.filter((n) => n.verdict === "hot" && n.relevance >= 0.95);
	const shed = news.length - admitted.length;
	// As estatísticas chegam como DELTA da execução; soma ao balde da hora que já existe (execuções independentes não se sobrescrevem).
	const addMaps = (a: Record<string, number>, b: Record<string, number>) => {
		const out = { ...a };
		for (const [k, v] of Object.entries(b)) out[k] = (out[k] ?? 0) + v;
		return out;
	};
	const prev = await Promise.all(
		stats.map((s) =>
			db.prepare("SELECT received,hot,buffer,dropped,reasons,sources FROM corvo_gate_stats WHERE bucket = ?1").bind(s.bucket).first<Record<string, unknown>>(),
		),
	);
	const mergedStats = stats.map((s, i) => {
		const p = prev[i];
		if (!p) return s;
		return {
			...s,
			received: Number(p.received) + s.received,
			hot: Number(p.hot) + s.hot,
			buffer: Number(p.buffer) + s.buffer,
			dropped: Number(p.dropped) + s.dropped,
			reasons: addMaps(parseJson<Record<string, number>>(String(p.reasons), {}), s.reasons),
			sources: addMaps(parseJson<Record<string, number>>(String(p.sources), {}), s.sources),
		};
	});
	const stmts = [
		...admitted.map((n) =>
			db
				.prepare(
					`INSERT INTO corvo_news (item_id,source_id,source_reliability,title,url,published_at,ingested_at,verdict,reason,relevance,kind,topics,assets,lat,lon,region)
					 VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9,?10,?11,?12,?13,?14,?15,?16)
					 ON CONFLICT(item_id) DO UPDATE SET verdict=excluded.verdict, reason=excluded.reason, relevance=excluded.relevance, assets=excluded.assets`,
				)
				.bind(n.item_id, n.source_id, n.source_reliability, n.title, n.url, n.published_at, now, n.verdict, n.reason, n.relevance, n.kind, JSON.stringify(n.topics), JSON.stringify(n.assets), n.lat, n.lon, n.region),
		),
		...mergedStats.map((s) =>
			db
				.prepare(
					`INSERT INTO corvo_gate_stats (bucket,pressure,received,hot,buffer,dropped,reasons,updated_at,sources) VALUES (?1,?2,?3,?4,?5,?6,?7,?8,?9)
					 ON CONFLICT(bucket) DO UPDATE SET pressure=excluded.pressure, received=excluded.received, hot=excluded.hot, buffer=excluded.buffer, dropped=excluded.dropped, reasons=excluded.reasons, updated_at=excluded.updated_at, sources=excluded.sources`,
				)
				.bind(s.bucket, s.pressure, s.received, s.hot, s.buffer, s.dropped, JSON.stringify(s.reasons), now, JSON.stringify(s.sources)),
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
	// retenção: uma vez por dia (03 UTC) apaga o que passou do prazo; DELETE de 0 linhas não gasta cota
	if (new Date().getUTCHours() === 3) {
		const cut = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString();
		await db.batch([
			db.prepare("DELETE FROM corvo_news WHERE published_at < ?1").bind(cut(RETAIN_NEWS_DAYS)),
			db.prepare("DELETE FROM corvo_gate_stats WHERE bucket < ?1").bind(cut(RETAIN_STATS_DAYS)),
		]);
	}
	await c.env.KV?.delete(FEED_KEY); // o próximo GET remonta o instantâneo
	return c.json({ ok: true, written, shed, mode });
});

const parseJson = <T,>(s: string, fallback: T): T => {
	try {
		return JSON.parse(s) as T;
	} catch {
		return fallback;
	}
};

async function buildFeed(db: D1Database, limit: number) {
	const [news, stats, forecasts, budget] = await Promise.all([
		db.prepare("SELECT * FROM corvo_news ORDER BY published_at DESC LIMIT 100").all<Record<string, unknown>>(),
		db.prepare("SELECT * FROM corvo_gate_stats ORDER BY bucket DESC LIMIT 24").all<Record<string, unknown>>(),
		db.prepare("SELECT * FROM corvo_forecasts ORDER BY updated_at DESC LIMIT 20").all<Record<string, unknown>>(),
		db.prepare("SELECT rows FROM write_budget WHERE day = ?1").bind(utcDay()).first<{ rows: number }>(),
	]);
	const used = budget?.rows ?? 0;
	return {
		generated_at: new Date().toISOString(),
		pressure: modeFor(used, limit),
		budget: { used, limit },
		news: news.results.map((r) => ({ ...r, topics: parseJson(String(r.topics), []), assets: parseJson(String(r.assets), []) })),
		stats: stats.results.map((r) => ({ ...r, reasons: parseJson(String(r.reasons), {}), sources: parseJson(String(r.sources), {}) })),
		forecasts: forecasts.results,
	};
}

/** Tudo que o painel mostra, numa chamada só. */
corvo.get("/feed", async (c) => {
	c.header("Cache-Control", cacheControl(15));
	const cached = await c.env.KV?.get(FEED_KEY);
	if (cached) return c.body(cached, 200, { "Content-Type": "application/json", "X-Corvo-Cache": "hit" });
	const body = JSON.stringify(await buildFeed(c.env.DB, dailyLimit(c.env)));
	await c.env.KV?.put(FEED_KEY, body, { expirationTtl: FEED_TTL });
	return c.body(body, 200, { "Content-Type": "application/json", "X-Corvo-Cache": "miss" });
});

/** O Oracle lê a pressão do orçamento antes de decidir quanto empurrar (o portão aperta quando o D1 enche). */
corvo.get("/pressure", async (c) => {
	if (!engineAuthorized(c.req.header("Authorization"), c.env.INGEST_TOKEN)) return c.json({ error: "unauthorized" }, 401);
	const row = await c.env.DB.prepare("SELECT rows FROM write_budget WHERE day = ?1").bind(utcDay()).first<{ rows: number }>();
	const used = row?.rows ?? 0;
	const limit = dailyLimit(c.env);
	return c.json({ pressure: modeFor(used, limit), used, limit });
});

/**
 * CONTROLE DA CAIXA (coletor 24 h). A caixa só faz requisições de saída: a cada ~30 s chama `POST /box/sync` (Bearer INGEST_TOKEN),
 * informa o estado e recebe, se houver, UM comando de uma lista fechada. O operador (app no celular) manda o comando com
 * `POST /box/command` e lê o estado com `GET /box` (Bearer ADMIN_TOKEN, nunca o token de envio). Nada é executado fora da lista.
 * Estado e comando vivem no KV; o estado só é regravado quando muda ou a cada 4 min, para respeitar o limite de escritas do KV.
 */
const BOX_STATUS_KEY = "corvo:box:status:v1";
const BOX_CMD_KEY = "corvo:box:cmd:v1";
const BOX_RESULT_KEY = "corvo:box:result:v1";
const BOX_ACTIONS = ["on", "off", "restart", "update", "reboot"] as const;
const BOX_STATUS_REFRESH_MS = 240_000;
const BOX_ONLINE_MS = 600_000;
const BOX_CMD_TTL_S = 600;

const boxSync = z.object({
	status: z.object({
		running: z.boolean(),
		mode: z.enum(["envia", "seco"]),
		mem_kb: z.number().int().min(0).max(1_000_000_000).nullable().default(null),
		disk: z.string().max(40).default(""),
		last_cycle: z.string().max(300).default(""),
		version: z.string().max(40).default(""),
	}),
	ack: z.object({ id: z.string().min(1).max(64), ok: z.boolean(), note: z.string().max(200).default("") }).optional(),
});
type BoxCmd = { id: string; action: (typeof BOX_ACTIONS)[number]; issued_at: string };
type BoxStatus = z.infer<typeof boxSync>["status"] & { seen_at: string };

corvo.post("/box/sync", async (c) => {
	if (!engineAuthorized(c.req.header("Authorization"), c.env.INGEST_TOKEN)) return c.json({ error: "unauthorized" }, 401);
	const kv = c.env.KV;
	if (!kv) return c.json({ error: "kv_unavailable" }, 503);
	const parsed = boxSync.safeParse(await c.req.json().catch(() => null));
	if (!parsed.success) return c.json({ error: "invalid_request" }, 400);
	const { status, ack } = parsed.data;
	const now = Date.now();
	const [prev, pending] = await Promise.all([kv.get<BoxStatus>(BOX_STATUS_KEY, "json"), kv.get<BoxCmd>(BOX_CMD_KEY, "json")]);
	let cmd = pending;
	if (ack && cmd && ack.id === cmd.id) {
		await kv.put(BOX_RESULT_KEY, JSON.stringify({ id: cmd.id, action: cmd.action, ok: ack.ok, note: ack.note, finished_at: new Date(now).toISOString() }), { expirationTtl: 86_400 });
		await kv.delete(BOX_CMD_KEY);
		cmd = null;
	}
	const changed = !prev || prev.running !== status.running || prev.mode !== status.mode || Boolean(ack);
	if (changed || now - Date.parse(prev.seen_at) > BOX_STATUS_REFRESH_MS) {
		await kv.put(BOX_STATUS_KEY, JSON.stringify({ ...status, seen_at: new Date(now).toISOString() }), { expirationTtl: 604_800 });
	}
	return c.json({ command: cmd ? { id: cmd.id, action: cmd.action } : null });
});

function boxOperator(c: { req: { header: (n: string) => string | undefined }; env: { ADMIN_TOKEN?: string } }): 401 | 503 | null {
	if (!c.env.ADMIN_TOKEN) return 503; // sem o segredo do operador, o controle fica fechado
	return engineAuthorized(c.req.header("Authorization"), c.env.ADMIN_TOKEN) ? null : 401;
}

corvo.get("/box", async (c) => {
	const denied = boxOperator(c);
	if (denied) return c.json({ error: denied === 503 ? "admin_not_configured" : "unauthorized" }, denied);
	const kv = c.env.KV;
	if (!kv) return c.json({ error: "kv_unavailable" }, 503);
	const [status, command, result] = await Promise.all([kv.get<BoxStatus>(BOX_STATUS_KEY, "json"), kv.get<BoxCmd>(BOX_CMD_KEY, "json"), kv.get(BOX_RESULT_KEY, "json")]);
	const now = Date.now();
	const online = status ? now - Date.parse(status.seen_at) < BOX_ONLINE_MS : false;
	c.header("Cache-Control", "no-store");
	return c.json({ online, status, command, result, server_time: new Date(now).toISOString() });
});

corvo.post("/box/command", async (c) => {
	const denied = boxOperator(c);
	if (denied) return c.json({ error: denied === 503 ? "admin_not_configured" : "unauthorized" }, denied);
	const kv = c.env.KV;
	if (!kv) return c.json({ error: "kv_unavailable" }, 503);
	const body = z.object({ action: z.enum(BOX_ACTIONS) }).safeParse(await c.req.json().catch(() => null));
	if (!body.success) return c.json({ error: "invalid_request", allowed: BOX_ACTIONS }, 400);
	if (await kv.get(BOX_CMD_KEY)) return c.json({ error: "command_pending" }, 409); // um de cada vez; expira sozinho em 10 min
	const cmd: BoxCmd = { id: crypto.randomUUID(), action: body.data.action, issued_at: new Date().toISOString() };
	await kv.put(BOX_CMD_KEY, JSON.stringify(cmd), { expirationTtl: BOX_CMD_TTL_S });
	return c.json({ ok: true, id: cmd.id, action: cmd.action }, 202);
});

/**
 * Limpeza manual (Bearer INGEST_TOKEN). `{"all": true}` apaga notícias e estatísticas (recomeçar do zero depois de mudar o filtro);
 * `{"older_than_days": N}` apaga só o que passou do prazo. Nunca mexe no orçamento do dia nem nas previsões.
 */
corvo.post("/purge", async (c) => {
	if (!engineAuthorized(c.req.header("Authorization"), c.env.INGEST_TOKEN)) return c.json({ error: "unauthorized" }, 401);
	const body = z.object({ all: z.boolean().optional(), older_than_days: z.number().int().min(0).max(3650).optional() }).safeParse(await c.req.json().catch(() => null));
	if (!body.success || (!body.data.all && body.data.older_than_days === undefined)) return c.json({ error: "invalid_request", detail: 'use {"all": true} ou {"older_than_days": N}' }, 400);
	const db = c.env.DB;
	const stmts = body.data.all
		? [db.prepare("DELETE FROM corvo_news"), db.prepare("DELETE FROM corvo_gate_stats")]
		: (() => {
				const cut = new Date(Date.now() - (body.data.older_than_days as number) * 86_400_000).toISOString();
				return [db.prepare("DELETE FROM corvo_news WHERE published_at < ?1").bind(cut), db.prepare("DELETE FROM corvo_gate_stats WHERE bucket < ?1").bind(cut)];
			})();
	const results = await db.batch(stmts);
	await c.env.KV?.delete(FEED_KEY);
	return c.json({ ok: true, deleted: { news: results[0].meta?.changes ?? 0, stats: results[1].meta?.changes ?? 0 } });
});
