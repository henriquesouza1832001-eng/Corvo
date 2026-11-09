import { useState, type ReactNode } from "react";
import { clearToken, readToken, saveToken } from "./admin";

/** Pede o token de operador uma vez e entrega `token` e `forget` a quem estiver dentro. */
export function TokenGate({ title, children }: { title: string; children: (token: string, forget: () => void) => ReactNode }) {
	const [token, setToken] = useState(readToken);
	const [draft, setDraft] = useState("");
	if (token) return <>{children(token, () => { clearToken(); setToken(""); })}</>;
	return (
		<section className="ctl">
			<h2>{title}</h2>
			<p className="muted">Cole o token de operador. Ele fica só neste aparelho e nunca é mostrado de novo.</p>
			<input className="box-input" type="password" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="token de operador" />
			<button className="box-btn go" disabled={draft.trim().length < 8} onClick={() => { saveToken(draft.trim()); setToken(draft.trim()); setDraft(""); }}>Salvar e entrar</button>
		</section>
	);
}
