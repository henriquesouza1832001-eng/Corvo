import { useEffect, useState } from "react";
import { BoxControl } from "./BoxControl";
import { SystemView } from "./SystemView";

/** Página de CONTROLE (separada do painel): Sistema e Caixa, com o token de operador. Abre em `/#caixa` e funciona no celular e no PC. */
export function isControlPage(): boolean {
	return window.location.hash.toLowerCase().startsWith("#caixa");
}

type Tab = "sistema" | "caixa";
const TABS: [Tab, string][] = [["sistema", "Sistema"], ["caixa", "Caixa"]];

export function ControlApp() {
	const [tab, setTab] = useState<Tab>("sistema");
	useEffect(() => { document.title = "CORVO · controle"; }, []);
	return (
		<div className="mobile">
			<nav className="mobile-tabs" role="tablist" aria-label="Seções">
				{TABS.map(([k, label]) => (
					<button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>
				))}
				<a className="mobile-back" href="#/" onClick={() => { window.location.hash = ""; window.location.reload(); }}>Painel</a>
			</nav>
			{tab === "sistema" ? <SystemView /> : <BoxControl />}
		</div>
	);
}
