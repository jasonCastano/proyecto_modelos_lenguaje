import { useEffect, useState } from "react";

import { health as fetchHealth, showcase as fetchShowcase } from "./lib/api";
import type { HealthStatus, ShowcaseResponse } from "./lib/types";
import { fallbackSections } from "./data/showcase";
import { Hero } from "./components/Hero";
import { RagConsole } from "./components/RagConsole";
import { ShowcaseStory } from "./components/ShowcaseStory";
import { MetricsBand } from "./components/MetricsBand";
import { ProductMotifs } from "./components/ProductMotifs";
import { LimitsNote } from "./components/LimitsNote";
import { Footer } from "./components/Footer";

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [showcase, setShowcase] = useState<ShowcaseResponse | null>(null);

  useEffect(() => {
    let active = true;
    void fetchHealth()
      .then((result) => {
        if (active) setHealth(result);
      })
      .catch(() => {
        if (active) {
          setHealth({
            ok: false,
            provider: "desconocido",
            model: "desconocido",
            configured: false,
            demo_available: false,
            detail: "No se pudo consultar el estado del proveedor.",
          });
        }
      });
    void fetchShowcase()
      .then((result) => {
        if (active) setShowcase(result);
      })
      .catch(() => {
        if (active) setShowcase(null);
      });
    return () => {
      active = false;
    };
  }, []);

  const sections = showcase?.sections ?? fallbackSections;
  const metrics = showcase?.metrics ?? [];

  return (
    <div className="site-shell">
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <header className="site-header">
        <div className="header-inner">
          <a className="brand" href="#inicio" aria-label="Manuelita, memoria del campo">
            <span className="brand-mark" aria-hidden="true">
              M
            </span>
            <span>
              Manuelita
              <small>RAG · Módulo 1</small>
            </span>
          </a>
          <nav className="nav" aria-label="Navegación principal">
            <a href="#consola">Consultar</a>
            <a href="#modulo-1">Módulo 1</a>
            <a href="#productos">Productos</a>
            <a href="#limites">Límites</a>
          </nav>
          <a className="header-cta" href="#consola">
            Preguntar <span aria-hidden="true">↘</span>
          </a>
        </div>
      </header>

      <main id="contenido">
        <div id="inicio">
          <Hero />
        </div>
        <RagConsole health={health} />
        <ShowcaseStory sections={sections} />
        <MetricsBand metrics={metrics} />
        <ProductMotifs />
        <div id="limites">
          <LimitsNote />
        </div>
      </main>
      <Footer />
    </div>
  );
}
