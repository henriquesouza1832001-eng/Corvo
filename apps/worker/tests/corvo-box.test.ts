import { describe, expect, it } from "vitest";
import { setup } from "./helpers/ingest";

const ENGINE = { Authorization: "Bearer segredo-de-teste", "Content-Type": "application/json" };
const ADMIN = { Authorization: "Bearer admin-de-teste", "Content-Type": "application/json" };
const status = { running: true, mode: "envia", mem_kb: 470000, disk: "1.9G", last_cycle: "ok", version: "t", interval_s: 900 };

function ctx(admin = true) {
	const t = setup();
	const extra = admin ? { ADMIN_TOKEN: "admin-de-teste" } : {};
	const call = (path: string, init: RequestInit = {}) => t.raw(path, init, extra);
	return { t, call };
}
const post = (headers: Record<string, string>, body: unknown): RequestInit => ({ method: "POST", headers, body: JSON.stringify(body) });
const get = (headers: Record<string, string>): RequestInit => ({ headers });

describe("centro de comando da caixa (tudo no banco)", () => {
	it("a caixa sem token de envio e o operador sem token de operador são recusados", async () => {
		const { call } = ctx();
		expect((await call("/api/corvo/box/sync", post({}, { status }))).status).toBe(401);
		expect((await call("/api/corvo/box", get(ENGINE))).status).toBe(401); // o token de envio NÃO abre o controle
		expect((await call("/api/corvo/box/command", post(ENGINE, { action: "off" }))).status).toBe(401);
		expect((await call("/api/corvo/diag", get(ENGINE))).status).toBe(401);
	});

	it("sem ADMIN_TOKEN configurado o controle fica fechado (503)", async () => {
		const { call } = ctx(false);
		expect((await call("/api/corvo/box", get(ADMIN))).status).toBe(503);
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "off" }))).status).toBe(503);
		expect((await call("/api/corvo/diag", get(ADMIN))).status).toBe(503);
	});

	it("fluxo completo: estado, comando, entrega, confirmação com saída e histórico", async () => {
		const { call } = ctx();
		expect(await (await call("/api/corvo/box/sync", post(ENGINE, { status }))).json()).toEqual({ command: null });
		const g1 = (await (await call("/api/corvo/box", get(ADMIN))).json()) as any;
		expect(g1.online).toBe(true);
		expect(g1.status).toMatchObject({ running: true, mode: "envia", mem_kb: 470000, interval_s: 900 });

		const sent = await call("/api/corvo/box/command", post(ADMIN, { action: "diag" }));
		expect(sent.status).toBe(202);
		const { id } = (await sent.json()) as { id: string };

		const s2 = (await (await call("/api/corvo/box/sync", post(ENGINE, { status }))).json()) as any;
		expect(s2.command).toEqual({ id, action: "diag", arg: null });

		const s3 = (await (await call("/api/corvo/box/sync", post(ENGINE, { status, ack: { id, ok: true, note: "feito", output: "disco 1.9G\nmem 470MB" } }))).json()) as any;
		expect(s3.command).toBeNull();

		const g2 = (await (await call("/api/corvo/box", get(ADMIN))).json()) as any;
		expect(g2.pending).toBeNull();
		expect(g2.history[0]).toMatchObject({ id, action: "diag", state: "done", ok: 1, has_output: 1 });
		const full = (await (await call(`/api/corvo/box/command/${id}`, get(ADMIN))).json()) as any;
		expect(full.output).toContain("disco 1.9G");
	});

	it("só aceita ações da lista, valida o argumento e um comando pendente de cada vez", async () => {
		const { call } = ctx();
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "rm -rf /" }))).status).toBe(400);
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "intervalo" }))).status).toBe(400); // falta o argumento
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "off", arg: 600 }))).status).toBe(400); // arg fora do intervalo
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "intervalo", arg: 10 }))).status).toBe(400); // abaixo do mínimo
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "intervalo", arg: 900 }))).status).toBe(202);
		expect((await call("/api/corvo/box/command", post(ADMIN, { action: "on" }))).status).toBe(409);
	});

	it("confirmação de outro comando não fecha o pendente", async () => {
		const { call } = ctx();
		const { id } = (await (await call("/api/corvo/box/command", post(ADMIN, { action: "update" }))).json()) as { id: string };
		await call("/api/corvo/box/sync", post(ENGINE, { status, ack: { id: "outro", ok: true } }));
		const g = (await (await call("/api/corvo/box", get(ADMIN))).json()) as any;
		expect(g.pending?.id).toBe(id);
	});

	it("não regrava o estado a cada chamada (limite de escritas do banco)", async () => {
		const { t, call } = ctx();
		const seen = () => (t.sqlite.prepare("SELECT seen_at FROM corvo_box_state WHERE id = 1").get() as { seen_at: string }).seen_at;
		await call("/api/corvo/box/sync", post(ENGINE, { status }));
		const first = seen();
		await new Promise((r) => setTimeout(r, 15));
		await call("/api/corvo/box/sync", post(ENGINE, { status }));
		expect(seen()).toBe(first); // igual: nada foi regravado
		await new Promise((r) => setTimeout(r, 15));
		await call("/api/corvo/box/sync", post(ENGINE, { status: { ...status, running: false } }));
		expect(seen()).not.toBe(first); // mudou: regrava
	});

	it("payload inválido do sync é recusado", async () => {
		const { call } = ctx();
		expect((await call("/api/corvo/box/sync", post(ENGINE, { status: { running: "sim" } }))).status).toBe(400);
	});

	it("aceita todos os comandos novos da lista (ciclo, precos, rede, fontes, limpar, agente)", async () => {
		for (const action of ["ciclo", "precos", "rede", "fontes", "limpar", "agente"]) {
			const { call } = ctx();
			const r = await call("/api/corvo/box/command", post(ADMIN, { action }));
			expect(r.status, action).toBe(202);
		}
	});

	it("limpar notícias antigas: o operador pode, sem token não, e o de envio continua valendo", async () => {
		const { call } = ctx();
		const body = { older_than_days: 30 };
		expect((await call("/api/corvo/purge", post({}, body))).status).toBe(401);
		expect((await call("/api/corvo/purge", post({ Authorization: "Bearer errado" }, body))).status).toBe(401);
		expect((await call("/api/corvo/purge", post(ADMIN, body))).status).toBe(200);
		expect((await call("/api/corvo/purge", post(ENGINE, body))).status).toBe(200);
		const { call: semAdmin } = ctx(false);
		expect((await semAdmin("/api/corvo/purge", post(ADMIN, body))).status).toBe(401); // sem ADMIN_TOKEN configurado, nada de operador
	});

	it("diagnóstico do Worker: banco, orçamento e feed", async () => {
		const { call } = ctx();
		const d = (await (await call("/api/corvo/diag", get(ADMIN))).json()) as any;
		expect(d.worker.ok).toBe(true);
		expect(d.db.ping_ms).toBeGreaterThanOrEqual(0);
		expect(d.budget).toMatchObject({ used: 0, pressure: "normal" });
		expect(d.feed.news_total).toBe(0);
		expect(d.kv_feed_cache).toBe(false);
	});
});
