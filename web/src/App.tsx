/**
 * Valer-IA, plataforma de agentes de Manuelita (spec 026): cinco áreas con su propia dirección.
 * `/` entrada · `/agente` espacio de trabajo · `/planificacion` consola · `/evidencia` panel ·
 * `/whatsapp` enlace al chat de WhatsApp (spec 032).
 */
import { useEffect, useState } from "react";

import { AppShell } from "./components/shell/AppShell";
import { health as fetchHealth, getVersion } from "./lib/api";
import { useRoute } from "./lib/router";
import type { AppVersion, HealthStatus, Mode } from "./lib/types";
import { Agent } from "./pages/Agent";
import { Evidence } from "./pages/Evidence";
import { Home } from "./pages/Home";
import { Planning } from "./pages/Planning";
import { WhatsApp } from "./pages/WhatsApp";

const NOT_FOUND = "Esa página no existe; te llevamos a la entrada.";

export default function App() {
  const { route, notFound } = useRoute();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [version, setVersion] = useState<AppVersion | null>(null);

  useEffect(() => {
    let active = true;
    void getVersion()
      .then((result) => active && setVersion(result))
      .catch(() => undefined);
    void fetchHealth()
      .then((result) => active && setHealth(result))
      .catch(() => {
        if (!active) return;
        setHealth({
          ok: false,
          provider: "desconocido",
          model: "desconocido",
          configured: false,
          demo_available: false,
          detail: "No se pudo consultar el estado del proveedor.",
        });
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (notFound) window.history.replaceState(null, "", "/");
  }, [notFound]);

  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "Valer-IA · plataforma de agentes de Manuelita",
      "/agente": "Agente · Valer-IA",
      "/planificacion": "Planificación industrial · Valer-IA",
      "/evidencia": "Evidencia técnica · Valer-IA",
      "/whatsapp": "WhatsApp · Valer-IA",
    };
    document.title = titles[route];
  }, [route]);

  const mode: Mode = health && !health.configured ? "demo" : "real";

  return (
    <AppShell
      demo={mode === "demo"}
      notice={notFound ? NOT_FOUND : null}
      route={route}
      version={version}
    >
      {route === "/" ? <Home /> : null}
      {route === "/agente" ? <Agent mode={mode} /> : null}
      {route === "/planificacion" ? <Planning /> : null}
      {route === "/evidencia" ? <Evidence health={health} /> : null}
      {route === "/whatsapp" ? <WhatsApp /> : null}
    </AppShell>
  );
}
