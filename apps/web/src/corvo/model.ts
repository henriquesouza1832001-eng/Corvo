/**
 * Modelo do front do CORVO. Espelha as regras do portão de admissão do engine (engine/corvo_engine/intake/gate.py):
 * os limiares abaixo precisam ficar iguais aos de `GateConfig` no Python.
 */
export type Pressure = "normal" | "economy" | "critical";
export type Verdict = "hot" | "buffer" | "drop";
export type Kind = "fato" | "reportagem" | "rumor" | "opiniao" | "previsao";
export type Topic = "banco_central" | "dados_macro" | "comercio" | "energia" | "geopolitica" | "conflito_chave" | "catastrofe" | "infraestrutura" | "cripto" | "empresas" | "politica" | "mercado";

export const HOT_MIN: Record<Pressure, number> = { normal: 0.75, economy: 0.85, critical: 0.95 };
export const BUFFER_MIN: Record<Pressure, number> = { normal: 0.5, economy: 0.6, critical: 0.95 };

export type DropReason = "duplicate_url" | "near_duplicate" | "stale" | "irrelevant" | "source_quota" | "malformed";

export interface AssetImpact {
	symbol: string;
	direction: "up" | "down" | "volatile";
	horizon: string;
}

export interface NewsItem {
	id: string;
	source: string;
	reliability: number; // 0-1, nota inicial da fonte
	title: string;
	minutesAgo: number;
	topics: Topic[];
	relevance: number; // 0-1, calculada pelo portão
	kind: Kind;
	/** Descarte que independe da pressão (duplicata, velha, cota, lixo). */
	hardDrop?: DropReason;
	assets: AssetImpact[];
	lat?: number | null;
	lon?: number | null;
	region?: string | null;
}

export interface ForecastCard {
	id: string;
	question: string;
	p: number; // probabilidade
	lo: number;
	hi: number; // intervalo de incerteza
	evidences: number;
	sources: number;
	method: string;
	horizon: string;
	status: "aberta" | "calibrando";
}

export function decide(item: NewsItem, pressure: Pressure): { verdict: Verdict; reason: string } {
	if (item.hardDrop) return { verdict: "drop", reason: item.hardDrop };
	if (item.relevance < BUFFER_MIN[pressure]) return { verdict: "drop", reason: item.relevance === 0 ? "irrelevant" : "below_threshold" };
	if (item.relevance >= HOT_MIN[pressure]) return { verdict: "hot", reason: "relevant" };
	return { verdict: "buffer", reason: "batch_later" };
}

export const REASON_LABEL: Record<string, string> = {
	duplicate_url: "mesma URL já vista",
	near_duplicate: "título quase igual ao de outra fonte",
	stale: "velha demais",
	irrelevant: "fora dos temas do Corvo",
	below_threshold: "relevância abaixo do corte da pressão atual",
	source_quota: "cota por hora da fonte esgotada",
	malformed: "item malformado",
	relevant: "grava já e segue para análise",
	batch_later: "fica no buffer e sobe em lote",
};

export const TOPIC_LABEL: Record<Topic, string> = {
	banco_central: "banco central",
	dados_macro: "dados macro",
	comercio: "comércio e sanções",
	energia: "energia e commodities",
	geopolitica: "conflito",
	conflito_chave: "conflito em região-chave",
	catastrofe: "catástrofe",
	infraestrutura: "infraestrutura crítica",
	cripto: "cripto",
	empresas: "empresas e crédito",
	politica: "crise política",
	mercado: "mercado",
};

export const KIND_LABEL: Record<Kind, string> = {
	fato: "fato confirmado",
	reportagem: "reportagem",
	rumor: "rumor",
	opiniao: "opinião",
	previsao: "previsão de terceiros",
};

/** Pontos de observação: lugares onde decisões acontecem. Ainda SEM coleta ligada (ver docs/corvo/SENSORES.md). */
export const ANCHORS = [
	{ id: "pentagono", label: "Pentágono · Casa Branca", lat: 38.87, lon: -77.05 },
	{ id: "wallstreet", label: "Wall Street · Fed NY", lat: 40.71, lon: -74.01 },
	{ id: "kremlin", label: "Kremlin", lat: 55.75, lon: 37.62 },
	{ id: "bce", label: "Banco Central Europeu", lat: 50.11, lon: 8.70 },
	{ id: "pequim", label: "Pequim", lat: 39.91, lon: 116.38 },
	{ id: "toquio", label: "Banco do Japão", lat: 35.69, lon: 139.77 },
	{ id: "planalto", label: "Planalto · B3", lat: -15.80, lon: -47.86 },
] as const;

export const TOPIC_COLOR: Record<Topic, string> = {
	banco_central: "#29d8ff",
	dados_macro: "#5aa9ff",
	comercio: "#ff8a3d",
	energia: "#e0c341",
	geopolitica: "#ff6a3d",
	conflito_chave: "#ff3d3d",
	catastrofe: "#ff4d5e",
	infraestrutura: "#ff7a90",
	cripto: "#ffb000",
	empresas: "#c0a0ff",
	politica: "#b58cff",
	mercado: "#39ff88",
};
