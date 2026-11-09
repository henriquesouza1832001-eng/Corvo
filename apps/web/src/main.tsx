import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CorvoApp } from "./corvo/CorvoApp";
import { MobileApp, isMobileShell } from "./corvo/MobileApp";
import "./corvo/corvo.css";

// A UI anterior (monitor do Brasil, em src/App.tsx e src/components) continua no repositório, mas não é mais montada.
// No app Android (ou com #celular na URL) entra a visão do celular: aba da caixa + painel. No navegador comum, só o painel.
createRoot(document.getElementById("root")!).render(
	<StrictMode>{isMobileShell() ? <MobileApp /> : <CorvoApp />}</StrictMode>,
);
