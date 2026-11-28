/**
 * La app en grande (spec 031, `app-frame` de la skill): una ventana del agente con la lista de
 * conversaciones y una respuesta abierta con sus citas y la fuente desplegada. HTML vivo, no captura.
 * La respuesta usa dos unidades reales del corpus oro (FSSC 22000 y la recertificación Bonsucro), con
 * sus documentos de origen.
 */
import { Link } from "../../lib/router";

const THREADS = [
  { title: "Certificaciones del azúcar", profile: "Cliente B2B", active: true },
  { title: "Programas para proveedores", profile: "Proveedor cañero", active: false },
  { title: "Línea ética", profile: "Colaborador", active: false },
  { title: "Plan con 15 % menos caña", profile: "Planificador industrial", active: false },
];

const SOURCES = [
  {
    tag: "U1",
    title: "Informe de Sostenibilidad Manuelita 2023-2024",
    quote:
      "Manuelita Azúcar y Energía está certificada por FSSC 22000, que acredita nuestra certificación de gestión de inocuidad alimentaria.",
    url: "https://www.manuelita.com/sostenibilidad",
  },
  {
    tag: "U2",
    title: "Noticias de Manuelita: recertificación de Bonsucro",
    quote:
      "Manuelita pasó satisfactoriamente la auditoría de recertificación realizada entre el 15 y el 19 de enero de 2024 […] versión 5.2.",
    url: "https://www.manuelita.com/manuelita-noticias/las-claves-de-manuelita-azucar-y-energia-para-lograr-la-recertificacion-de-bonsucro",
  },
];

export function AppFrame() {
  return (
    <section aria-labelledby="producto-title" className="site-section app-section" id="producto">
      <div className="wrap">
        <div className="sec-head">
          <h2 className="site-h2" id="producto-title">
            Respuestas con la fuente de cada dato
          </h2>
          <p className="site-lead">
            Pregunta por productos, certificaciones o programas para proveedores. Cada cifra llega con
            la cita del documento del que sale.
          </p>
        </div>
        <div className="app-frame" role="presentation">
          <div aria-hidden="true" className="app-frame__bar">
            <span />
            <span />
            <span />
            <p>Valer-IA · Agente</p>
          </div>
          <div className="app-frame__body">
            <ul aria-label="Conversaciones" className="app-frame__threads">
              {THREADS.map((thread) => (
                <li data-active={thread.active || undefined} key={thread.title}>
                  <strong>{thread.title}</strong>
                  <span>{thread.profile}</span>
                </li>
              ))}
            </ul>
            <div className="app-frame__chat">
              <p className="app-frame__profile">Perfil: Cliente B2B</p>
              <p className="app-frame__ask">
                Compro azúcar para mi empresa, ¿qué certificaciones tienen?
              </p>
              <div className="app-frame__answer">
                <p>
                  Manuelita Azúcar y Energía está certificada en FSSC 22000, de inocuidad
                  alimentaria <a href={SOURCES[0].url}>[U1]</a>, y pasó la recertificación de
                  Bonsucro en enero de 2024, con la versión 5.2 del estándar{" "}
                  <a href={SOURCES[1].url}>[U2]</a>.
                </p>
                <p className="app-frame__meta">2 fuentes · herramienta: search_documents</p>
              </div>
            </div>
            <aside aria-label="Fuentes de la respuesta" className="app-frame__sources">
              <p className="app-frame__sources-title">Fuentes</p>
              {SOURCES.map((source) => (
                <article key={source.tag}>
                  <p className="app-frame__tag">{source.tag}</p>
                  <p className="app-frame__source-title">{source.title}</p>
                  <blockquote>{source.quote}</blockquote>
                </article>
              ))}
            </aside>
          </div>
        </div>
        <p className="app-section__go">
          <Link className="text-link" to="/agente">
            Pregunta tú mismo en la vista del agente
          </Link>
        </p>
      </div>
    </section>
  );
}
