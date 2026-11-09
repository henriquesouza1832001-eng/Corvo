import { useState } from "react";
import { BoxControl } from "./BoxControl";
import { CorvoApp } from "./CorvoApp";

/** Visão do celular: duas abas, o painel completo e o controle da caixa. Só entra no app Android ou com `#celular` na URL. */
export function isMobileShell(): boolean {
	const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor;
	return Boolean(cap?.isNativePlatform?.()) || window.location.hash === "#celular";
}

export function MobileApp() {
	const [tab, setTab] = useState<"caixa" | "painel">("caixa");
	return (
		<div className="mobile">
			<nav className="mobile-tabs" role="tablist" aria-label="Seções">
				<button role="tab" aria-selected={tab === "caixa"} className={tab === "caixa" ? "on" : ""} onClick={() => setTab("caixa")}>Caixa</button>
				<button role="tab" aria-selected={tab === "painel"} className={tab === "painel" ? "on" : ""} onClick={() => setTab("painel")}>Painel</button>
			</nav>
			{tab === "caixa" ? <BoxControl /> : <CorvoApp />}
		</div>
	);
}
