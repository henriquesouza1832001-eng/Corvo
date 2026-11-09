import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ControlApp, isControlPage } from "./corvo/ControlApp";
import { CorvoApp } from "./corvo/CorvoApp";
import "./corvo/corvo.css";

// A UI anterior (monitor do Brasil, em src/App.tsx e src/components) continua no repositório, mas não é mais montada.
// O painel é sempre o mesmo. A página de controle da caixa é separada: abre com `#caixa` na URL e pede o token de operador.
createRoot(document.getElementById("root")!).render(
	<StrictMode>{isControlPage() ? <ControlApp /> : <CorvoApp />}</StrictMode>,
);
