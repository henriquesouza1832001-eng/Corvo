import { Hono } from "hono";
import { z } from "zod";
import type { AppEnv } from "../env";
import { engineAuthorized } from "../lib/auth";
import { isSuspicious } from "../lib/suspicious";
import { utcDay } from "../lib/budget";

/**
 * API DE LEITURA DO CORVO para consumidores externos (`/api/v1`), com chave por cliente, plano e limite diário.
 * Só LEITURA: nenhum consumidor grava nada no banco do CORVO. Cada chamada válida custa 1 linha de escrita (o contador de uso).
 * O CORVO não envia ordens, não recomenda investimento e só serve probabilidade com método e estado; previsão `aberta` ou
 * `calibrando` é EXPERIMENTAL. Chaves são geradas pelo operador (`ADMIN_TOKEN`) e mostradas UMA vez; o banco guarda só o hash.
 */
export const v1 = new Hono<AppEnv>();
export const keyAdmin = new Hono<AppEnv>();

export const SCHEMA_VERSION = "1";
const PLANS = {
	interno: { daily_limit: 20_000, delay_s: 0 }, // consumidor de casa (sem custo)
	gratis: { daily_limit: 500, delay_s: 900 }, // público: atrasado 15 min
	pago: { daily_limit: 10_000, delay_s: 0 }, // tempo real, com taxa
} as const;
type Plan = keyof typeof PLANS;

const DDL = [
	"CREATE TABLE IF NOT EXISTS corvo_api_key (id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE, daily_limit INTEGER NOT NULL, delay_s INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, revoked_at TEXT)",
	"CREATE TABLE IF NOT EXISTS corvo_api_usage (key_id TEXT NOT NULL, day TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (key_id, day))",
	"CREATE INDEX IF NOT EXISTS idx_corvo_news_ingested ON corvo_news(ingested_at, item_id)",
];
let schemaReady = false;
async function ensureSchema(db: D1Database) {
	if (schemaReady) return;
	await db.batch(DDL.map((q) => db.prepare(q)));
	schemaReady = true;
}

async function sha256Hex(text: string): Promise<string> {
	const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
	return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const parseJson = <T>(s: unknown, fallback: T): T => {
	try { return JSON.parse(String(s)) as T; } catch { return fallback; }
};
const secondsToMidnightUtc = () => Math.max(1, Math.ceil((Date.parse(`${utcDay()}T00:00:00Z`) + 86_400_000 - Date.now()) / 1000));

type Consumer = { id: string; name: string; plan: string; daily_limit: number; delay_s: number };

/** Autentica a chave e aplica o limite diário. Devolve o consumidor ou a resposta de erro. */
async function authenticate(c: { req: { header: (n: string) => string | undefined }; env: AppEnv["Bindings"]; header: (k: string, v: string) => void; json: (b: unknown, s?: number) => Response }): Promise<Consumer | Response> {
	const db = c.env.DB;
	await ensureSchema(db);
	const m = /^Bearer (cvk_[0-9a-f]{64})$/.exec(c.req.header("Authorization") ?? "");
	if (!m) return c.json({ error: "invalid_key", detail: "use Authorization: Bearer cvk_..." }, 401);
	const row = await db
		.prepare("SELECT id, name, plan, daily_limit, delay_s, revoked_at FROM corvo_api_key WHERE key_hash = ?1")
		.bind(await sha256Hex(m[1]))
		.first<Consumer & { revoked_at: string | null }>();
	if (!row || row.revoked_at) return c.json({ error: "invalid_key" }, 401);
	const day = utcDay();
	const used = (await db.prepare("SELECT n FROM corvo_api_usage WHERE key_id = ?1 AND day = ?2").bind(row.id, day).first<{ n: number }>())?.n ?? 0;
	c.header("X-RateLimit-Limit", String(row.daily_limit));
	if (used >= row.daily_limit) {
		c.header("Retry-After", String(secondsToMidnightUtc()));
		c.header("X-RateLimit-Remaining", "0");
		return c.json({ error: "quota_exceeded", limit: row.daily_limit, plan: row.plan }, 429);
	}
	await db.prepare("INSERT INTO corvo_api_usage (key_id, day, n) VALUES (?1, ?2, 1) ON CONFLICT(key_id, day) DO UPDATE SET n = n + 1").bind(row.id, day).run();
	c.header("X-RateLimit-Remaining", String(row.daily_limit - used - 1));
	return row;
}

const enc = (ingested_at: string, id: string) => btoa(`${ingested_at}|${id}`).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
function dec(cursor: string): { at: string; id: string } | null {
	try {
		const raw = atob(cursor.replace(/-/g, "+").replace(/_/g, "/"));
		const i = raw.indexOf("|");
		const at = raw.slice(0, i);
		return i > 0 && !Number.isNaN(Date.parse(at)) ? { at, id: raw.slice(i + 1) } : null;
	} catch { return null; }
}

v1.get("/", (c) =>
	c.json({
		schema_version: SCHEMA_VERSION,
		service: "CORVO",
		endpoints: ["GET /api/v1/evidencias?since=<cursor>&limit=<1..200>", "GET /api/v1/previsoes", "GET /api/v1/uso"],
		notice: "O CORVO só coleta, analisa e prevê. Não envia ordens e não é recomendação de investimento. Previsão aberta ou calibrando é experimental.",
	}),
);

v1.get("/evidencias", async (c) => {
	const who = await authenticate(c);
	if (who instanceof Response) return who;
	const limit = Math.min(200, Math.max(1, Number(c.req.query("limit")) || 100));
	const now = Date.now();
	const since = c.req.query("since");
	const from = since ? dec(since) : { at: new Date(now - 86_400_000).toISOString(), id: "" };
	if (!from) return c.json({ error: "invalid_cursor" }, 400);
	const cutoff = new Date(now - who.delay_s * 1000).toISOString(); // plano com atraso só enxerga o que já "envelheceu"
	const rows = await c.env.DB.prepare(
		"SELECT item_id, source_id, source_reliability, title, url, published_at, ingested_at, verdict, relevance, kind, topics, assets, lat, lon, region FROM corvo_news WHERE (ingested_at > ?1 OR (ingested_at = ?1 AND item_id > ?2)) AND ingested_at <= ?3 ORDER BY ingested_at, item_id LIMIT ?4",
	)
		.bind(from.at, from.id, cutoff, limit)
		.all<Record<string, unknown>>();
	const items = (rows.results ?? []).map((r) => ({
		id: r.item_id,
		title: r.title,
		url: r.url,
		source_id: r.source_id,
		source_reliability: r.source_reliability,
		published_at: r.published_at, // quando saiu na fonte
		received_at: r.ingested_at, // quando o CORVO soube (use este para reconstruir "o que se sabia em T")
		kind: r.kind,
		topics: parseJson<string[]>(r.topics, []),
		region: r.region ?? null,
		lat: r.lat ?? null,
		lon: r.lon ?? null,
		relevance: r.relevance,
		verdict: r.verdict,
		asset_hypotheses: parseJson<unknown[]>(r.assets, []), // HIPÓTESE de impacto, nunca direção nem conselho
		suspicious: isSuspicious(String(r.title)), // padrão de injeção de prompt ou golpe: não entregue o texto cru a um modelo
	}));
	const last = rows.results?.[rows.results.length - 1];
	c.header("Cache-Control", "no-store");
	return c.json({
		schema_version: SCHEMA_VERSION,
		generated_at: new Date(now).toISOString(),
		count: items.length,
		items,
		next_cursor: last ? enc(String(last.ingested_at), String(last.item_id)) : (since ?? null),
	});
});

v1.get("/previsoes", async (c) => {
	const who = await authenticate(c);
	if (who instanceof Response) return who;
	const rows = await c.env.DB.prepare("SELECT forecast_id, question, probability, interval_low, interval_high, evidences, sources, method, horizon, status, updated_at FROM corvo_forecasts ORDER BY updated_at DESC LIMIT 50").all();
	c.header("Cache-Control", "no-store");
	return c.json({
		schema_version: SCHEMA_VERSION,
		items: rows.results ?? [],
		notice: "Probabilidade com intervalo, evidências e método. Estado aberta ou calibrando = EXPERIMENTAL. Não é recomendação de investimento.",
	});
});

v1.get("/uso", async (c) => {
	const who = await authenticate(c);
	if (who instanceof Response) return who;
	const day = utcDay();
	const used = (await c.env.DB.prepare("SELECT n FROM corvo_api_usage WHERE key_id = ?1 AND day = ?2").bind(who.id, day).first<{ n: number }>())?.n ?? 0;
	return c.json({ schema_version: SCHEMA_VERSION, name: who.name, plan: who.plan, day, used, limit: who.daily_limit, delay_s: who.delay_s });
});

/* ===== administração das chaves (operador) ===== */
function operatorDenied(c: { req: { header: (n: string) => string | undefined }; env: { ADMIN_TOKEN?: string } }): 401 | 503 | null {
	if (!c.env.ADMIN_TOKEN) return 503;
	return engineAuthorized(c.req.header("Authorization"), c.env.ADMIN_TOKEN) ? null : 401;
}
const deny = (code: 401 | 503) => ({ error: code === 503 ? "admin_not_configured" : "unauthorized" });

keyAdmin.post("/admin/keys", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	const body = z
		.object({
			name: z.string().min(1).max(60),
			plan: z.enum(["interno", "gratis", "pago"]),
			daily_limit: z.number().int().min(10).max(1_000_000).optional(),
			delay_s: z.number().int().min(0).max(86_400).optional(),
		})
		.safeParse(await c.req.json().catch(() => null));
	if (!body.success) return c.json({ error: "invalid_request", plans: Object.keys(PLANS) }, 400);
	await ensureSchema(c.env.DB);
	const preset = PLANS[body.data.plan as Plan];
	const bytes = crypto.getRandomValues(new Uint8Array(32));
	const key = "cvk_" + [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
	const id = crypto.randomUUID();
	await c.env.DB.prepare("INSERT INTO corvo_api_key (id, name, plan, key_hash, daily_limit, delay_s, created_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)")
		.bind(id, body.data.name, body.data.plan, await sha256Hex(key), body.data.daily_limit ?? preset.daily_limit, body.data.delay_s ?? preset.delay_s, new Date().toISOString())
		.run();
	c.header("Cache-Control", "no-store");
	return c.json({ id, key, plan: body.data.plan, daily_limit: body.data.daily_limit ?? preset.daily_limit, delay_s: body.data.delay_s ?? preset.delay_s, notice: "Guarde a chave agora: ela não é mostrada de novo." }, 201);
});

keyAdmin.get("/admin/keys", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	await ensureSchema(c.env.DB);
	const rows = await c.env.DB.prepare(
		"SELECT k.id, k.name, k.plan, k.daily_limit, k.delay_s, k.created_at, k.revoked_at, COALESCE(u.n, 0) AS used_today FROM corvo_api_key k LEFT JOIN corvo_api_usage u ON u.key_id = k.id AND u.day = ?1 ORDER BY k.created_at DESC LIMIT 200",
	)
		.bind(utcDay())
		.all();
	c.header("Cache-Control", "no-store");
	return c.json({ keys: rows.results ?? [] }); // nunca devolve a chave nem o hash
});

keyAdmin.post("/admin/keys/:id/revoke", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	await ensureSchema(c.env.DB);
	const r = await c.env.DB.prepare("UPDATE corvo_api_key SET revoked_at = ?2 WHERE id = ?1 AND revoked_at IS NULL").bind(c.req.param("id"), new Date().toISOString()).run();
	return (r.meta?.changes ?? 0) > 0 ? c.json({ ok: true }) : c.json({ error: "not_found_or_already_revoked" }, 404);
});
