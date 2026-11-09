import { API_URL } from "./feed";

/** Token de operador: fica só neste aparelho (localStorage). Nunca é exibido de novo depois de salvo. */
const KEY = "corvo_admin_token";
export function readToken(): string {
	try { return localStorage.getItem(KEY) ?? ""; } catch { return ""; }
}
export function saveToken(t: string): void {
	try { localStorage.setItem(KEY, t); } catch { /* sem armazenamento: vale só nesta sessão */ }
}
export function clearToken(): void {
	try { localStorage.removeItem(KEY); } catch { /* ignora */ }
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; message: string };
export async function adminFetch<T>(token: string, path: string, init?: { method?: string; body?: unknown }): Promise<ApiResult<T>> {
	try {
		const r = await fetch(`${API_URL}${path}`, {
			method: init?.method ?? "GET",
			headers: { Authorization: `Bearer ${token}`, ...(init?.body ? { "Content-Type": "application/json" } : {}) },
			body: init?.body ? JSON.stringify(init.body) : undefined,
		});
		if (r.status === 401) return { ok: false, status: 401, message: "Token recusado. Confira o token de operador." };
		if (r.status === 503) return { ok: false, status: 503, message: "O controle ainda não foi ativado no servidor (falta o segredo de operador)." };
		if (r.status === 409) return { ok: false, status: 409, message: "Já há um comando esperando a caixa. Aguarde." };
		if (!r.ok) return { ok: false, status: r.status, message: `A API respondeu ${r.status}.` };
		return { ok: true, data: (await r.json()) as T };
	} catch { return { ok: false, status: 0, message: "Sem conexão com a API." }; }
}

export function ago(iso: string | null | undefined, now: string): string {
	if (!iso) return "nunca";
	const s = Math.max(0, Math.round((Date.parse(now) - Date.parse(iso)) / 1000));
	return s < 90 ? `${s}s` : s < 5400 ? `${Math.round(s / 60)}min` : s < 172800 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`;
}
