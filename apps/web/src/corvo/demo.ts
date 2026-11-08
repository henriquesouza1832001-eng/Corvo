import type { ForecastCard, NewsItem } from "./model";

/**
 * DADOS ILUSTRATIVOS. Manchetes e números abaixo são fictícios, escritos só para mostrar como o Corvo trata cada notícia.
 * Quando o endpoint do engine existir, este arquivo é substituído por chamadas à API.
 */
export const DEMO_NEWS: NewsItem[] = [
	{ id: "n1", region: "Estados Unidos", lat: 38.9, lon: -77.04, source: "banco-central-exemplo", reliability: 0.95, title: "Banco central de grande economia anuncia corte surpresa de juros", minutesAgo: 4, topics: ["banco_central"], relevance: 0.97, kind: "fato", assets: [{ symbol: "USD", direction: "down", horizon: "24h" }, { symbol: "BTC", direction: "up", horizon: "24h" }, { symbol: "OURO", direction: "up", horizon: "24h" }] },
	{ id: "n2", region: "Japão", lat: 35.68, lon: 139.69, source: "agencia-global-exemplo", reliability: 0.85, title: "Terremoto de grande magnitude atinge polo industrial; fábricas de chips paralisadas", minutesAgo: 9, topics: ["catastrofe", "mercado"], relevance: 0.96, kind: "reportagem", assets: [{ symbol: "NASDAQ", direction: "down", horizon: "6h" }, { symbol: "SEMICOND", direction: "volatile", horizon: "3d" }] },
	{ id: "n3", source: "portal-cripto-exemplo", reliability: 0.6, title: "Exchange relata exploit em protocolo de empréstimo; fundos em investigação", minutesAgo: 14, topics: ["cripto"], relevance: 0.74, kind: "rumor", assets: [{ symbol: "ETH", direction: "down", horizon: "6h" }] },
	{ id: "n4", region: "China", lat: 39.9, lon: 116.4, source: "agencia-global-exemplo", reliability: 0.85, title: "Novas tarifas sobre importações entram em vigor e afetam petróleo e câmbio", minutesAgo: 22, topics: ["geopolitica", "mercado"], relevance: 0.88, kind: "fato", assets: [{ symbol: "PETROLEO", direction: "volatile", horizon: "24h" }, { symbol: "BRL", direction: "down", horizon: "24h" }] },
	{ id: "n5", region: "Brasil", lat: -15.79, lon: -47.88, source: "jornal-politico-exemplo", reliability: 0.7, title: "Pesquisa eleitoral mostra empate técnico no primeiro turno", minutesAgo: 41, topics: ["politica"], relevance: 0.57, kind: "reportagem", assets: [{ symbol: "BRL", direction: "volatile", horizon: "7d" }] },
	{ id: "n6", source: "portal-cripto-exemplo", reliability: 0.6, title: "Analista diz que bitcoin pode chegar a novo recorde até o fim do ano", minutesAgo: 55, topics: ["cripto"], relevance: 0.48, kind: "previsao", assets: [] },
	{ id: "n7", region: "Estados Unidos", lat: 38.9, lon: -77.04, source: "blog-mercado-exemplo", reliability: 0.35, title: "Opinião: por que as ações de tecnologia vão cair", minutesAgo: 63, topics: ["mercado"], relevance: 0.31, kind: "opiniao", assets: [] },
	{ id: "n8", source: "agencia-global-exemplo", reliability: 0.85, title: "Terremoto de grande magnitude atinge polo industrial; fábricas de chips paralisadas, diz agência", minutesAgo: 11, topics: ["catastrofe", "mercado"], relevance: 0.96, kind: "reportagem", hardDrop: "near_duplicate", assets: [] },
	{ id: "n9", source: "portal-cripto-exemplo", reliability: 0.6, title: "Banco central anuncia corte surpresa de juros (mesma matéria, link com rastreio)", minutesAgo: 6, topics: ["banco_central"], relevance: 0.97, kind: "fato", hardDrop: "duplicate_url", assets: [] },
	{ id: "n10", source: "feed-generico-exemplo", reliability: 0.4, title: "Celebridade lança linha de perfumes", minutesAgo: 30, topics: [], relevance: 0, kind: "reportagem", hardDrop: "irrelevant", assets: [] },
	{ id: "n11", source: "portal-cripto-exemplo", reliability: 0.6, title: "Preço do bitcoin hoje: veja a cotação (página repetida, 17ª vez na hora)", minutesAgo: 18, topics: ["cripto"], relevance: 0.72, kind: "reportagem", hardDrop: "source_quota", assets: [] },
	{ id: "n12", source: "jornal-antigo-exemplo", reliability: 0.7, title: "Guerra comercial entra em nova fase", minutesAgo: 900, topics: ["geopolitica"], relevance: 0.81, kind: "reportagem", hardDrop: "stale", assets: [] },
];

export const DEMO_FORECASTS: ForecastCard[] = [
	{ id: "f1", question: "O dólar (DXY) fecha o dia em queda após o corte de juros?", p: 0.78, lo: 0.66, hi: 0.86, evidences: 9, sources: 5, method: "baseline por evento + calibração isotônica", horizon: "24h", status: "aberta" },
	{ id: "f2", question: "O BTC sobe mais de 3% nas próximas 24 h?", p: 0.41, lo: 0.27, hi: 0.57, evidences: 6, sources: 4, method: "modelo de impacto de notícia, amostra ainda pequena", horizon: "24h", status: "calibrando" },
	{ id: "f3", question: "Índice de semicondutores perde mais de 4% em 3 dias?", p: 0.52, lo: 0.3, hi: 0.73, evidences: 4, sources: 2, method: "analogia com eventos passados (poucos casos)", horizon: "3d", status: "calibrando" },
];

/** Contadores do dia, fictícios, para o funil. */
export const DEMO_BUDGET = { used: 18_400, limit: 100_000 };
