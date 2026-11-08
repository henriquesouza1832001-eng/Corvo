/**
 * Modelo do front do CORVO. Espelha as regras do portão de admissão do engine (engine/corvo_engine/intake/gate.py):
 * os limiares abaixo precisam ficar iguais aos de `GateConfig` no Python.
 */
export type Pressure = "normal" | "economy" | "critical";
export type Verdict = "hot" | "buffer" | "drop";
export type Kind = "fato" | "reportagem" | "rumor" | "opiniao" | "previsao";
export type Topic = "catastrofe" | "geopolitica" | "politica" | "banco_central" | "cripto" | "mercado";

export const HOT_MIN: Record<Pressure, number> = { normal: 0.6, economy: 0.8, critical: 0.95 };
export const BUFFER_MIN: Record<Pressure, number> = { normal: 0.3, economy: 0.5, critical: 0.95 };

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
	catastrofe: "catástrofe",
	geopolitica: "geopolítica",
	politica: "política",
	banco_central: "banco central",
	cripto: "cripto",
	mercado: "mercado",
};

export const KIND_LABEL: Record<Kind, string> = {
	fato: "fato confirmado",
	reportagem: "reportagem",
	rumor: "rumor",
	opiniao: "opinião",
	previsao: "previsão de terceiros",
};
