import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CorvoApp } from "./corvo/CorvoApp";
import "./corvo/corvo.css";

// A UI anterior (monitor do Brasil, em src/App.tsx e src/components) continua no repositório, mas não é mais montada.
createRoot(document.getElementById("root")!).render(
	<StrictMode>
		<CorvoApp />
	</StrictMode>,
);
