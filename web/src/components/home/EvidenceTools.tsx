/**
 * Evidencia en la entrada (spec 031): las herramientas reales del proyecto con sus íconos a color
 * (Gil Barbara's logos, CC0; marcas de sus dueños, créditos en `public/media/iconos/icons-credits.json`)
 * y el acceso a la vista de evidencia, donde ahora viven también la consulta de los Módulos 1 y 2.
 */
import { Link } from "../../lib/router";

const TOOLS = [
  { file: "qdrant.svg", name: "Qdrant", role: "Búsqueda híbrida en el corpus" },
  { file: "deepseek.svg", name: "DeepSeek", role: "Modelo de lenguaje" },
  { file: "langchain.svg", name: "LangChain y LangGraph", role: "Agente, router y memoria" },
  { file: "fastapi.svg", name: "FastAPI", role: "API de la plataforma" },
  { file: "whatsapp.svg", name: "WhatsApp", role: "Canal con OpenClaw" },
  { file: "python.svg", name: "Python", role: "Optimizador y herramientas" },
];

export function EvidenceTools() {
  return (
    <section aria-labelledby="evidencia-title" className="site-section" id="evidencia">
      <div className="wrap evidence-tools">
        <div className="sec-head">
          <h2 className="site-h2" id="evidencia-title">
            Herramientas que puedes revisar
          </h2>
          <p className="site-lead">
            El catálogo de 26 herramientas, la traza de cada turno, los servicios y las evaluaciones están
            abiertos.
          </p>
          <ol aria-label="Traza de un turno" className="trace-fragment">
            <li>
              <code>router</code> ruta documentos <span>reglas</span>
            </li>
            <li>
              <code>search_documents</code> 8 fragmentos <span>Qdrant</span>
            </li>
            <li>
              <code>validar citas</code> [U1] [U2] <span>2 de 2</span>
            </li>
            <li>
              <code>respuesta</code> con fuentes <span>DeepSeek</span>
            </li>
          </ol>
          <div className="evidence-tools__actions">
            <Link className="btn" to="/evidencia">
              Ver la evidencia
            </Link>
          </div>
        </div>
        <ul className="tools-grid">
          {TOOLS.map((tool) => (
            <li className="site-card tools-grid__item" key={tool.name}>
              <img alt="" className="tools-grid__icon" height="40" loading="lazy" src={`/media/iconos/${tool.file}`} width="40" />
              <h3>{tool.name}</h3>
              <p>{tool.role}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
