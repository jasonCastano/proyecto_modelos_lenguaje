import type { HealthStatus, Mode } from "../lib/types";

interface DemoBannerProps {
  health: HealthStatus | null;
  mode: Mode;
  onEnableDemo: () => void;
  onUseReal: () => void;
}

const ADVERSARIAL_NOTICE =
  "Corpus de prueba adversarial activo: las respuestas usan documentos con instrucciones " +
  "inyectadas (caso 5 de la rúbrica). Reinicia el servidor sin MANUELITA_DEMO_CORPUS para " +
  "volver al corpus real.";

export function DemoBanner(props: DemoBannerProps) {
  const banner = <ModeBanner {...props} />;
  if (!props.health?.adversarial_corpus) return banner;
  return (
    <>
      <div
        className="demo-banner"
        data-kind="warning"
        data-testid="adversarial-banner"
        role="status"
      >
        <span>{ADVERSARIAL_NOTICE}</span>
      </div>
      {banner}
    </>
  );
}

function ModeBanner({ health, mode, onEnableDemo, onUseReal }: DemoBannerProps) {
  if (mode === "demo") {
    return (
      <div className="demo-banner" data-testid="demo-banner" role="status">
        <span>
          Modo demostración: las respuestas son simuladas y no representan al modelo real. La
          recuperación usa el índice de prueba y el modelo guionizado, sin red.
        </span>
        <button className="btn btn-secondary" onClick={onUseReal} type="button">
          Volver al proveedor real
        </button>
      </div>
    );
  }

  if (health && !health.configured) {
    return (
      <div className="demo-banner" data-kind="warning" data-testid="demo-banner" role="status">
        <span>Falta la clave del proveedor. Puedes revisar la experiencia en modo demostración.</span>
        <button className="btn btn-accent" onClick={onEnableDemo} type="button">
          Usar modo demostración
        </button>
      </div>
    );
  }

  if (health && !health.ok) {
    return (
      <div className="demo-banner" data-kind="warning" data-testid="demo-banner" role="status">
        <span>{health.detail ?? "El proveedor no está disponible en este momento."}</span>
        <button className="btn btn-accent" onClick={onEnableDemo} type="button">
          Usar modo demostración
        </button>
      </div>
    );
  }

  return null;
}
