import { useState } from "react";
import { BoxControl } from "./BoxControl";
import { CorvoApp } from "./CorvoApp";
import { SystemView } from "./SystemView";

/** Visão do celular (centro de comando): Sistema, Caixa e o painel completo. Só entra no app Android ou com `#celular` na URL. */
export function isMobileShell(): boolean {
	const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
	return Boolean(cap?.isNativePlatform?.()) || window.location.hash === "#celular";
}

type Tab = "sistema" | "caixa" | "painel";
const TABS: [Tab, string][] = [["sistema", "Sistema"], ["caixa", "Caixa"], ["painel", "Painel"]];

export function MobileApp() {
	const [tab, setTab] = useState<Tab>("sistema");
	return (
		<div className="mobile">
			<nav className="mobile-tabs" role="tablist" aria-label="Seções">
				{TABS.map(([k, label]) => (
					<button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{label}</button>
				))}
			</nav>
			{tab === "sistema" ? <SystemView /> : tab === "caixa" ? <BoxControl /> : <CorvoApp />}
		</div>
	);
}
