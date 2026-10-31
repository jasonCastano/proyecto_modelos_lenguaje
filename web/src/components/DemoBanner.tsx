import type { HealthStatus, Mode } from "../lib/types";

interface DemoBannerProps {
  health: HealthStatus | null;
  mode: Mode;
  onEnableDemo: () => void;
  onUseReal: () => void;
}

export function DemoBanner({ health, mode, onEnableDemo, onUseReal }: DemoBannerProps) {
  if (mode === "demo") {
    return (
      <div className="demo-banner" data-testid="demo-banner" role="status">
        <span>
          Modo demostración: las respuestas son simuladas y no representan al modelo real.
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
