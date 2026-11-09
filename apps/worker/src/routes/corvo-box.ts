import { Hono } from "hono";
import { z } from "zod";
import type { AppEnv } from "../env";
import { engineAuthorized } from "../lib/auth";
import { utcDay } from "../lib/budget";

/**
 * CENTRO DE COMANDO da caixa (coletor 24 h) e diagnóstico do sistema. TUDO no banco (Turso), nada no KV.
 * - A caixa só faz requisições de saída: `POST /box/sync` (Bearer INGEST_TOKEN) informa o estado e recebe UM comando de uma lista fechada.
 * - O operador (app no celular) usa `ADMIN_TOKEN`: `GET /box`, `POST /box/command`, `GET /box/command/:id`, `GET /diag`.
 *   Sem ADMIN_TOKEN configurado, o controle fica fechado (503). O token de envio nunca abre o controle.
 * - O estado só é regravado quando muda ou a cada 4 min, para respeitar o limite de escritas do banco.
 * As tabelas são criadas aqui mesmo (idempotente), igual a database/migrations/0009_corvo_box.sql.
 */
export const boxRoutes = new Hono<AppEnv>();

/** Lista fechada. `arg` só existe em `intervalo` (segundos entre ciclos, 300 a 3600). */
const ACTIONS = ["on", "off", "restart", "update", "reboot", "diag", "logs", "seco", "envio", "intervalo"] as const;
const REFRESH_MS = 240_000;
const ONLINE_MS = 600_000;
const PENDING_TTL_MS = 600_000;
const KEEP_COMMANDS = 200;
const OUTPUT_MAX = 4000;

const DDL = [
	"CREATE TABLE IF NOT EXISTS corvo_box_state (id INTEGER PRIMARY KEY CHECK (id = 1), status TEXT NOT NULL, seen_at TEXT NOT NULL)",
	"CREATE TABLE IF NOT EXISTS corvo_box_cmd (id TEXT PRIMARY KEY, action TEXT NOT NULL, arg INTEGER, issued_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending', ok INTEGER, note TEXT, output TEXT, finished_at TEXT)",
	"CREATE INDEX IF NOT EXISTS idx_corvo_box_cmd_issued ON corvo_box_cmd(issued_at)",
];
let schemaReady = false;
async function ensureSchema(db: D1Database) {
	if (schemaReady) return;
	await db.batch(DDL.map((q) => db.prepare(q)));
	schemaReady = true;
}

const syncBody = z.object({
	status: z.object({
		running: z.boolean(),
		mode: z.enum(["envia", "seco"]),
		mem_kb: z.number().int().min(0).max(1_000_000_000).nullable().default(null),
		disk: z.string().max(40).default(""),
		last_cycle: z.string().max(300).default(""),
		version: z.string().max(40).default(""),
		interval_s: z.number().int().min(0).max(86_400).nullable().default(null),
		prices_last: z.string().max(40).default(""),
		corpus_items: z.number().int().min(0).nullable().default(null),
		errors_recent: z.number().int().min(0).max(100_000).nullable().default(null),
	}),
	ack: z.object({ id: z.string().min(1).max(64), ok: z.boolean(), note: z.string().max(200).default(""), output: z.string().max(OUTPUT_MAX).default("") }).optional(),
});
type Status = z.infer<typeof syncBody>["status"];

function operatorDenied(c: { req: { header: (n: string) => string | undefined }; env: { ADMIN_TOKEN?: string } }): 401 | 503 | null {
	if (!c.env.ADMIN_TOKEN) return 503;
	return engineAuthorized(c.req.header("Authorization"), c.env.ADMIN_TOKEN) ? null : 401;
}
const deny = (code: 401 | 503) => ({ error: code === 503 ? "admin_not_configured" : "unauthorized" });

boxRoutes.post("/box/sync", async (c) => {
	if (!engineAuthorized(c.req.header("Authorization"), c.env.INGEST_TOKEN)) return c.json({ error: "unauthorized" }, 401);
	const parsed = syncBody.safeParse(await c.req.json().catch(() => null));
	if (!parsed.success) return c.json({ error: "invalid_request" }, 400);
	const db = c.env.DB;
	await ensureSchema(db);
	const { status, ack } = parsed.data;
	const now = Date.now();
	const nowIso = new Date(now).toISOString();

	if (ack) {
		await db
			.prepare("UPDATE corvo_box_cmd SET state = 'done', ok = ?2, note = ?3, output = ?4, finished_at = ?5 WHERE id = ?1 AND state = 'pending'")
			.bind(ack.id, ack.ok ? 1 : 0, ack.note, ack.output || null, nowIso)
			.run();
	}
	const prev = await db.prepare("SELECT status, seen_at FROM corvo_box_state WHERE id = 1").first<{ status: string; seen_at: string }>();
	let before: Partial<Status> = {};
	try { before = prev ? (JSON.parse(prev.status) as Partial<Status>) : {}; } catch { /* estado antigo ilegível: regrava */ }
	const changed = !prev || before.running !== status.running || before.mode !== status.mode || before.interval_s !== status.interval_s || Boolean(ack);
	if (changed || now - Date.parse(prev.seen_at) > REFRESH_MS) {
		await db
			.prepare("INSERT INTO corvo_box_state (id, status, seen_at) VALUES (1, ?1, ?2) ON CONFLICT(id) DO UPDATE SET status = excluded.status, seen_at = excluded.seen_at")
			.bind(JSON.stringify(status), nowIso)
			.run();
	}
	const cmd = await db
		.prepare("SELECT id, action, arg FROM corvo_box_cmd WHERE state = 'pending' AND issued_at > ?1 ORDER BY issued_at LIMIT 1")
		.bind(new Date(now - PENDING_TTL_MS).toISOString())
		.first<{ id: string; action: string; arg: number | null }>();
	return c.json({ command: cmd ? { id: cmd.id, action: cmd.action, arg: cmd.arg } : null });
});

boxRoutes.get("/box", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	const db = c.env.DB;
	await ensureSchema(db);
	const now = Date.now();
	const [state, pending, history] = await Promise.all([
		db.prepare("SELECT status, seen_at FROM corvo_box_state WHERE id = 1").first<{ status: string; seen_at: string }>(),
		db.prepare("SELECT id, action, arg, issued_at FROM corvo_box_cmd WHERE state = 'pending' AND issued_at > ?1 ORDER BY issued_at LIMIT 1").bind(new Date(now - PENDING_TTL_MS).toISOString()).first(),
		db.prepare("SELECT id, action, arg, state, ok, note, issued_at, finished_at, (output IS NOT NULL AND output <> '') AS has_output FROM corvo_box_cmd ORDER BY issued_at DESC LIMIT 15").all(),
	]);
	let status: (Status & { seen_at: string }) | null = null;
	try { status = state ? { ...(JSON.parse(state.status) as Status), seen_at: state.seen_at } : null; } catch { status = null; }
	c.header("Cache-Control", "no-store");
	return c.json({ online: status ? now - Date.parse(status.seen_at) < ONLINE_MS : false, status, pending: pending ?? null, history: history.results ?? [], server_time: new Date(now).toISOString() });
});

boxRoutes.get("/box/command/:id", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	await ensureSchema(c.env.DB);
	const row = await c.env.DB.prepare("SELECT id, action, arg, state, ok, note, output, issued_at, finished_at FROM corvo_box_cmd WHERE id = ?1").bind(c.req.param("id")).first();
	c.header("Cache-Control", "no-store");
	return row ? c.json(row) : c.json({ error: "not_found" }, 404);
});

boxRoutes.post("/box/command", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	const body = z
		.object({ action: z.enum(ACTIONS), arg: z.number().int().min(300).max(3600).optional() })
		.refine((b) => (b.action === "intervalo") === (b.arg !== undefined), { message: "arg só em intervalo (300 a 3600 s) e obrigatório nele" })
		.safeParse(await c.req.json().catch(() => null));
	if (!body.success) return c.json({ error: "invalid_request", allowed: ACTIONS }, 400);
	const db = c.env.DB;
	await ensureSchema(db);
	const now = Date.now();
	const open = await db.prepare("SELECT id FROM corvo_box_cmd WHERE state = 'pending' AND issued_at > ?1 LIMIT 1").bind(new Date(now - PENDING_TTL_MS).toISOString()).first();
	if (open) return c.json({ error: "command_pending" }, 409); // um de cada vez; expira sozinho em 10 min
	const id = crypto.randomUUID();
	await db.batch([
		db.prepare("UPDATE corvo_box_cmd SET state = 'expired' WHERE state = 'pending' AND issued_at <= ?1").bind(new Date(now - PENDING_TTL_MS).toISOString()),
		db.prepare("INSERT INTO corvo_box_cmd (id, action, arg, issued_at) VALUES (?1, ?2, ?3, ?4)").bind(id, body.data.action, body.data.arg ?? null, new Date(now).toISOString()),
		db.prepare("DELETE FROM corvo_box_cmd WHERE id NOT IN (SELECT id FROM corvo_box_cmd ORDER BY issued_at DESC LIMIT ?1)").bind(KEEP_COMMANDS),
	]);
	return c.json({ ok: true, id, action: body.data.action }, 202);
});

/** Verificação do sistema feita PELO Worker (operador): o próprio Worker, o banco, o orçamento de escrita e o feed. */
boxRoutes.get("/diag", async (c) => {
	const denied = operatorDenied(c);
	if (denied) return c.json(deny(denied), denied);
	const db = c.env.DB;
	const t0 = Date.now();
	await db.prepare("SELECT 1").first();
	const db_ms = Date.now() - t0;
	const day = utcDay();
	const limit = Math.max(1000, Number(c.env.DAILY_WRITE_LIMIT) || 100_000);
	const since = new Date(Date.now() - 86_400_000).toISOString();
	const [budget, news, stats] = await Promise.all([
		db.prepare("SELECT rows FROM write_budget WHERE day = ?1").bind(day).first<{ rows: number }>(),
		db.prepare("SELECT COUNT(*) AS total, MAX(ingested_at) AS newest, SUM(ingested_at > ?1) AS last_24h FROM corvo_news").bind(since).first<{ total: number; newest: string | null; last_24h: number | null }>(),
		db.prepare("SELECT MAX(bucket) AS newest FROM corvo_gate_stats").first<{ newest: string | null }>(),
	]);
	const used = budget?.rows ?? 0;
	const newest = news?.newest ?? null;
	c.header("Cache-Control", "no-store");
	return c.json({
		worker: { ok: true, time: new Date().toISOString() },
		db: { backend: c.env.DB_BACKEND || "d1", ping_ms: db_ms },
		budget: { used, limit, percent: Math.round((used / limit) * 10000) / 100, pressure: used >= limit * 0.85 ? "critical" : used >= limit * 0.6 ? "economy" : "normal" },
		feed: { news_total: news?.total ?? 0, news_24h: news?.last_24h ?? 0, newest_ingest: newest, newest_age_s: newest ? Math.max(0, Math.round((Date.now() - Date.parse(newest)) / 1000)) : null, stats_newest: stats?.newest ?? null },
		kv_feed_cache: Boolean(c.env.KV),
	});
});
