import { describe, expect, it } from "vitest";
import { setup } from "./helpers/ingest";

/** KV mínimo em memória (get com "json", put, delete) para provar o controle da caixa sem Cloudflare. */
function fakeKv() {
	const m = new Map<string, string>();
	return {
		get: async (k: string, type?: string) => (m.has(k) ? (type === "json" ? JSON.parse(m.get(k) as string) : m.get(k)) : null),
		put: async (k: string, v: string) => void m.set(k, v),
		delete: async (k: string) => void m.delete(k),
		_m: m,
	};
}

const ENGINE = { Authorization: "Bearer segredo-de-teste", "Content-Type": "application/json" };
const ADMIN = { Authorization: "Bearer admin-de-teste", "Content-Type": "application/json" };
const status = { running: true, mode: "envia", mem_kb: 470000, disk: "1.9G", last_cycle: "ok", version: "t" };

function ctx(admin = true) {
	const t = setup();
	const kv = fakeKv();
	const extra = { KV: kv, ...(admin ? { ADMIN_TOKEN: "admin-de-teste" } : {}) } as never;
	const call = (path: string, init: RequestInit) => t.raw(path, init, extra);
	return { kv, call };
}
const post = (headers: Record<string, string>, body: unknown): RequestInit => ({ method: "POST", headers, body: JSON.stringify(body) });

describe("controle da caixa", () => {
	it("a caixa sem token de envio e o operador sem token de operador são recusados", async () => {
		const { call } = ctx();
		expect((await call("/api/corvo/box/sync", post({}, { status }))).status).toBe(401);
		expect((await call("/api/corvo/box", { headers: ENGINE })).status).toBe(401); // o token de envio NÃO abre o controle
		expect((await call("/api/corvo/box/command", post(ENGINE, { action: "off" }))).status).toBe(401);
	});

	it("sem ADMIN_TOKEN configurado o controle fica fechado (503)", async () => {
		const { call } = ctx(false);
		expect((await call("/api/corvo/box", { headers: ADMIN })).status).toBe(503);
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "off" }))).status).toBe(503);
	});

	it("fluxo completo: estado, comando, entrega e confirmação", async () => {
		const { call } = ctx();
		expect(await (await call("/api/corvo/box/sync", post(ENGINE, { status }))).json()).toEqual({ command: null });
		const g1 = (await (await call("/api/corvo/box", { headers: ADMIN })).json()) as any;
		expect(g1.online).toBe(true);
		expect(g1.status).toMatchObject({ running: true, mode: "envia", mem_kb: 470000 });

		const sent = await call("/api/corvo/box/command", post(ADMIN, { action: "restart" }));
		expect(sent.status).toBe(202);
		const { id } = (await sent.json()) as { id: string };

		const s2 = (await (await call("/api/corvo/box/sync", post(ENGINE, { status }))).json()) as any;
		expect(s2.command).toEqual({ id, action: "restart" });

		const s3 = (await (await call("/api/corvo/box/sync", post(ENGINE, { status, ack: { id, ok: true, note: "ligado" } }))).json()) as any;
		expect(s3.command).toBeNull();
		const g2 = (await (await call("/api/corvo/box", { headers: ADMIN })).json()) as any;
		expect(g2.command).toBeNull();
		expect(g2.result).toMatchObject({ id, action: "restart", ok: true });
	});

	it("só aceita ações da lista e um comando pendente de cada vez", async () => {
		const { call } = ctx();
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "rm -rf /" }))).status).toBe(400);
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "off" }))).status).toBe(202);
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "on" }))).status).toBe(409);
	});

	it("confirmação de outro comando não apaga o pendente", async () => {
		const { call } = ctx();
		const { id } = (await (await call("/api/corvo/box/command", post(ADMIN, { action: "update" }))).json()) as { id: string };
		await call("/api/corvo/box/sync", post(ENGINE, { status, ack: { id: "outro", ok: true } }));
		const g = (await (await call("/api/corvo/box", { headers: ADMIN })).json()) as any;
		expect(g.command?.id).toBe(id);
	});

	it("não regrava o estado a cada chamada (limite de escritas do KV)", async () => {
		const { call, kv } = ctx();
		await call("/api/corvo/box/sync", post(ENGINE, { status }));
		const first = kv._m.get("corvo:box:status:v1");
		await call("/api/corvo/box/sync", post(ENGINE, { status }));
		expect(kv._m.get("corvo:box:status:v1")).toBe(first); // igual: nada foi regravado
		await call("/api/corvo/box/sync", post(ENGINE, { status: { ...status, running: false } }));
		expect(kv._m.get("corvo:box:status:v1")).not.toBe(first); // mudou: regrava
	});

	it("payload inválido do sync é recusado", async () => {
		const { call } = ctx();
		expect((await call("/api/corvo/box/sync", post(ENGINE, { status: { running: "sim" } }))).status).toBe(400);
	});
});
