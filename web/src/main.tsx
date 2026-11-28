import "@fontsource-variable/archivo/wdth.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles/tokens.css";
import "./styles/global.css";
import "./styles/platform.css";
import "./styles/site.css";
import "./styles/home.css";
import "./styles/whatsapp.css";

const container = document.getElementById("root");

if (!container) {
  throw new Error("No se encontró el contenedor de la aplicación.");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
