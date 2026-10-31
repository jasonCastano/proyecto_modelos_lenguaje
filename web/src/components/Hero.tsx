import { CaneField } from "./CaneField";

export function Hero() {
  return (
    <section className="hero" data-testid="hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <p className="hero-kicker">Ingenio Manuelita · Valle del Cauca</p>
        <h1 id="hero-title">La memoria del campo, lista para responder.</h1>
        <p className="hero-lede">
          Un RAG académico sobre información pública de Manuelita. Pregunta en lenguaje natural y
          recibe una respuesta con fuentes verificables, o la certeza de que el corpus no alcanza.
        </p>
        <div className="hero-actions">
          <a className="btn btn-primary" href="#consola">
            Preguntar al corpus
            <span aria-hidden="true">↘</span>
          </a>
          <a className="btn btn-secondary" href="#modulo-1">
            Recorrer el Módulo 1
          </a>
        </div>
        <div className="hero-trust" aria-label="Principios del sistema">
          <span className="chip">Cita o fallback</span>
          <span className="chip">Datos públicos</span>
          <span className="chip">DeepSeek + LangChain</span>
        </div>
      </div>
      <div className="hero-art">
        <CaneField />
        <p className="hero-art-note">
          Un cañaveral de líneas conecta el paisaje con la evidencia: cada nodo es una unidad de
          conocimiento, cada surco una ruta de recuperación.
        </p>
      </div>
    </section>
  );
}
