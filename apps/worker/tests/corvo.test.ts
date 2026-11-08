import { describe, expect, it, vi } from "vitest";
import { setup } from "./helpers/ingest";

const NOW = new Date().toISOString();
const news = (id: string, extra = {}) => ({
	item_id: id, source_id: "agencia", source_reliability: 0.8, title: `Notícia ${id}`, url: "https://a.com/" + id, published_at: NOW,
	verdict: "hot", reason: "relevant", relevance: 0.9, kind: "fato", topics: ["banco_central"], assets: [{ symbol: "BTC", direction: "up", horizon: "24h" }], ...extra,
});
const fc = (extra = {}) => ({ forecast_id: "f1", question: "q?", probability: 0.6, interval_low: 0.4, interval_high: 0.8, evidences: 3, sources: 2, method: "m", horizon: "24h", status: "calibrando", ...extra });
const stats = { bucket: NOW, pressure: "normal", received: 10, hot: 2, buffer: 3, dropped: 5, reasons: { duplicate_url: 3, irrelevant: 2 }, sources: { bbc: 6, g1: 4 } };

describe("API do CORVO", () => {
	it("recusa ingestão sem token", async () => {
		const t = setup();
		const r = await t.raw("/api/corvo/ingest", { method: "POST", body: "{}" });
		expect(r.status).toBe(401);
	});

	it("grava lote e o feed devolve notícias, estatísticas, previsões e o orçamento", async () => {
		const t = setup();
		const post = (body: unknown) => t.raw("/api/corvo/ingest", { method: "POST", headers: { Authorization: "Bearer segredo-de-teste" }, body: JSON.stringify(body) });
		const r = await post({ news: [news("a"), news("b", { verdict: "buffer", relevance: 0.4 })], stats: [stats], forecasts: [fc()] });
		expect(r.status).toBe(200);
		expect((await r.json()) as { written: number }).toMatchObject({ written: 4 });
		const feed = (await (await t.get("/api/corvo/feed")).json()) as any;
		expect(feed.news).toHaveLength(2);
		expect(feed.news[0].topics).toEqual(["banco_central"]);
		expect(feed.stats[0].reasons.duplicate_url).toBe(3);
		expect(feed.stats[0].sources.bbc).toBe(6);
		expect(feed.forecasts[0].probability).toBe(0.6);
		expect(feed.budget.used).toBe(8); // 4 itens x 2 linhas
		expect(feed.pressure).toBe("normal");
	});

	it("reenviar o mesmo item não duplica", async () => {
		const t = setup();
		const post = () => t.raw("/api/corvo/ingest", { method: "POST", headers: { Authorization: "Bearer segredo-de-teste" }, body: JSON.stringify({ news: [news("a")] }) });
		await post(); await post();
		const feed = (await (await t.get("/api/corvo/feed")).json()) as any;
		expect(feed.news).toHaveLength(1);
	});

	it("rejeita previsão sem método, ou com probabilidade fora do intervalo, e notícia descartada", async () => {
		const t = setup();
		const post = (body: unknown) => t.raw("/api/corvo/ingest", { method: "POST", headers: { Authorization: "Bearer segredo-de-teste" }, body: JSON.stringify(body) });
		expect((await post({ forecasts: [fc({ method: "" })] })).status).toBe(400);
		expect((await post({ forecasts: [fc({ probability: 0.9 })] })).status).toBe(400);
		expect((await post({ news: [news("x", { verdict: "drop" })] })).status).toBe(400);
	});

	it("o Oracle lê a pressão com token; sem token, 401", async () => {
		const t = setup();
		expect((await t.get("/api/corvo/pressure")).status).toBe(401);
		const r = await t.get("/api/corvo/pressure", { Authorization: "Bearer segredo-de-teste" });
		expect(await r.json()).toMatchObject({ pressure: "normal", limit: 100000 });
	});
});

describe("estatísticas por hora", () => {
	it("soma os deltas de execuções diferentes no mesmo balde", async () => {
		const t = setup();
		const post = (s: unknown) => t.raw("/api/corvo/ingest", { method: "POST", headers: { Authorization: "Bearer segredo-de-teste" }, body: JSON.stringify({ stats: [s] }) });
		await post({ ...stats, received: 10, hot: 1, buffer: 2, dropped: 7, reasons: { stale: 5, irrelevant: 2 }, sources: { bbc: 6, g1: 4 } });
		await post({ ...stats, received: 5, hot: 0, buffer: 1, dropped: 4, reasons: { stale: 1, near_duplicate: 3 }, sources: { bbc: 2, dw: 3 } });
		const feed = (await (await t.get("/api/corvo/feed")).json()) as any;
		expect(feed.stats).toHaveLength(1);
		expect(feed.stats[0]).toMatchObject({ received: 15, hot: 1, buffer: 3, dropped: 11 });
		expect(feed.stats[0].reasons).toEqual({ stale: 6, irrelevant: 2, near_duplicate: 3 });
		expect(feed.stats[0].sources).toEqual({ bbc: 8, g1: 4, dw: 3 });
	});
});

describe("teto de escrita do CORVO", () => {
	const post = (t: ReturnType<typeof setup>, body: unknown, extra: Record<string, string> = {}) =>
		t.raw("/api/corvo/ingest", { method: "POST", headers: { Authorization: "Bearer segredo-de-teste" }, body: JSON.stringify(body) }, extra);
	const day = new Date().toISOString().slice(0, 10);

	it("em economia só passa HOT; no limite não passa notícia, mas as estatísticas continuam", async () => {
		const t = setup();
		t.sqlite.exec(`INSERT INTO write_budget (day,rows) VALUES ('${day}', 7000)`); // 70% de 10000
		const r = (await (await post(t, { news: [news("a"), news("b", { verdict: "buffer", relevance: 0.4 })], stats: [stats] }, { DAILY_WRITE_LIMIT: "10000" })).json()) as any;
		expect(r).toMatchObject({ shed: 1, mode: "economy" });
		t.sqlite.exec(`UPDATE write_budget SET rows = 10000 WHERE day = '${day}'`);
		const r2 = (await (await post(t, { news: [news("c")], stats: [stats] }, { DAILY_WRITE_LIMIT: "10000" })).json()) as any;
		expect(r2).toMatchObject({ shed: 1, mode: "critical", written: 1 });
	});

	it("a pressão usa o limite configurado", async () => {
		const t = setup();
		t.sqlite.exec(`INSERT INTO write_budget (day,rows) VALUES ('${day}', 7000)`);
		const r = await t.raw("/api/corvo/pressure", { headers: { Authorization: "Bearer segredo-de-teste" } }, { DAILY_WRITE_LIMIT: "10000" });
		expect(await r.json()).toMatchObject({ pressure: "economy", limit: 10000 });
	});
});

describe("limpeza", () => {
	const auth = { Authorization: "Bearer segredo-de-teste" };
	it("exige token e pedido válido", async () => {
		const t = setup();
		expect((await t.raw("/api/corvo/purge", { method: "POST", body: JSON.stringify({ all: true }) })).status).toBe(401);
		expect((await t.raw("/api/corvo/purge", { method: "POST", headers: auth, body: "{}" })).status).toBe(400);
	});

	it("apaga tudo ou só o que passou do prazo, sem tocar nas previsões", async () => {
		// Fixa o relógio às 03:37 UTC, a hora da retenção diária do ingest: o teste tem que passar em QUALQUER hora (o CI já falhou por isso).
		vi.useFakeTimers({ toFake: ["Date"] });
		vi.setSystemTime(new Date("2026-11-08T03:37:00Z"));
		try {
			const t = setup();
			const post = (body: unknown) => t.raw("/api/corvo/ingest", { method: "POST", headers: auth, body: JSON.stringify(body) });
			await post({ news: [news("novo", { published_at: new Date().toISOString() })], stats: [stats], forecasts: [fc()] });
			// o item velho entra direto no banco: pelo ingest, a retenção das 03 UTC o apagaria antes de a purga ser testada
			const old = new Date(Date.now() - 40 * 86_400_000).toISOString();
			t.sqlite.exec(`INSERT INTO corvo_news (item_id,source_id,source_reliability,title,url,published_at,ingested_at,verdict,reason,relevance,kind)
				VALUES ('velho','s',0.8,'Notícia velha',NULL,'${old}','${old}','hot','relevant',0.9,'fato')`);
			const r1 = (await (await t.raw("/api/corvo/purge", { method: "POST", headers: auth, body: JSON.stringify({ older_than_days: 30 }) })).json()) as any;
			expect(r1.deleted.news).toBe(1);
			expect(((await (await t.get("/api/corvo/feed")).json()) as any).news).toHaveLength(1);
			await t.raw("/api/corvo/purge", { method: "POST", headers: auth, body: JSON.stringify({ all: true }) });
			const feed = (await (await t.get("/api/corvo/feed")).json()) as any;
			expect(feed.news).toHaveLength(0);
			expect(feed.stats).toHaveLength(0);
			expect(feed.forecasts).toHaveLength(1);
		} finally {
			vi.useRealTimers();
		}
	});
});
