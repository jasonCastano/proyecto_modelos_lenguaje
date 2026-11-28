/**
 * Hero de la entrada (spec 031, hero «split» de la skill): aviso de proyecto académico, h1 que nombra la
 * categoría y el público, la línea con el dato duro y dos acciones; el visual es el video pitch (spec
 * 028), que sigue siendo lo primero de la entrada. Entra una sola vez al cargar (`data-enter`).
 */
import { Link } from "../../lib/router";
import { PRIMARY_ACTION } from "../shell/AppShell";
import { PitchVideo } from "./PitchVideo";

export function Hero() {
  return (
    <section aria-labelledby="hero-title" className="site-section home-hero" data-enter id="inicio">
      <div className="wrap home-hero__grid">
        <div className="home-hero__text">
          <p className="home-hero__notice" data-enter-step style={{ "--step": 0 } as React.CSSProperties}>
            Proyecto académico con IA. No es un canal oficial de Manuelita.
          </p>
          <h1
            className="home-hero__title"
            data-enter-step
            id="hero-title"
            style={{ "--step": 1 } as React.CSSProperties}
            tabIndex={-1}
          >
            Agentes de IA para consultar a Manuelita
          </h1>
          <p className="home-hero__lead" data-enter-step style={{ "--step": 2 } as React.CSSProperties}>
            Valer-IA responde a cinco perfiles con 26 herramientas y la fuente de cada dato, y reparte
            la caña de la semana con un optimizador.
          </p>
          <div className="home-hero__actions" data-enter-step style={{ "--step": 3 } as React.CSSProperties}>
            <Link className="btn" to="/agente">
              {PRIMARY_ACTION}
            </Link>
            <Link className="btn btn--line" to="/planificacion">
              Ver la planificación
            </Link>
          </div>
        </div>
        <div className="home-hero__visual" data-enter-step style={{ "--step": 2 } as React.CSSProperties}>
          <PitchVideo />
        </div>
      </div>
    </section>
  );
}
