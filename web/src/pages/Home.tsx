/**
 * Entrada pública de la plataforma (spec 026, historia 2): qué es Valer-IA, para quién es y cómo
 * responde. Consulta, Resumen y FAQ de los Módulos 1 y 2 siguen disponibles más abajo.
 */
import { Guarantees } from "../components/home/Guarantees";
import { PlatformHero } from "../components/home/PlatformHero";
import { ProfileLedger } from "../components/home/ProfileLedger";
import { LimitsNote } from "../components/LimitsNote";
import { RagConsole } from "../components/RagConsole";
import type { HealthStatus } from "../lib/types";

interface HomeProps {
  health: HealthStatus | null;
}

export function Home({ health }: HomeProps) {
  return (
    <div className="home">
      <PlatformHero />
      <ProfileLedger />
      <Guarantees />
      <section aria-labelledby="modules-heading" className="modules">
        <h2 className="section-title" id="modules-heading">
          Consulta, resumen y preguntas frecuentes
        </h2>
        <p className="modules__lead">
          Las funciones de los Módulos 1 y 2 responden solo con el corpus público y citan cada
          fragmento.
        </p>
        <RagConsole health={health} />
      </section>
      <div id="limites">
        <LimitsNote />
      </div>
    </div>
  );
}
