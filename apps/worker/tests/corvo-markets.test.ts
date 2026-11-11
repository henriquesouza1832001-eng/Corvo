import { afterEach, describe, expect, it, vi } from "vitest";
import { setup } from "./helpers/ingest";

afterEach(() => vi.unstubAllGlobals());

describe("referências de mercado do CORVO", () => {
	it("devolve cripto e câmbio com variação, janela e proveniência", async () => {
		const ticker = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"].map((symbol) => ({ symbol, lastPrice: "100", priceChangePercent: "2.5", closeTime: 1_800_000_000_000 }));
		const fx = { rates: { "2026-11-09": { EUR: 0.91, BRL: 5.2, JPY: 150, GBP: 0.78, CNY: 7.1 }, "2026-11-10": { EUR: 0.92, BRL: 5.3, JPY: 151, GBP: 0.79, CNY: 7.2 } } };
		vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(Response.json(ticker)).mockResolvedValueOnce(Response.json(fx)));
		const t = setup();
		const response = await t.get("/api/corvo/markets");
		const body = await response.json() as any;
		expect(response.status).toBe(200);
		expect(body.markets).toHaveLength(10);
		expect(body.markets.find((p: any) => p.symbol === "BTC")).toMatchObject({ change_pct: 2.5, period: "24h", source: "Binance public market data" });
		expect(body.markets.find((p: any) => p.symbol === "USDBRL").change_pct).toBeCloseTo((5.3 / 5.2 - 1) * 100);
		expect(body.note).toContain("Não são previsões");
	});

	it("mantém uma classe de dados quando a outra fonte falha", async () => {
		vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("indisponível")).mockResolvedValueOnce(Response.json({ rates: {} })));
		const t = setup();
		const body = await (await t.get("/api/corvo/markets")).json() as any;
		expect(body.markets).toEqual([]);
		expect(body.coverage).toEqual({ crypto: false, fx: false });
		expect(body.errors.crypto).toBe("indisponível");
	});
});
