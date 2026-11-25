/** Las cuatro garantías del agente con su evidencia (spec 026). No son una secuencia: sin números. */
import { Link } from "../../lib/router";

const REPO = "https://github.com/jasonCastano/proyecto_modelos_lenguaje/blob/main/";

const GUARANTEES = [
  {
    title: "Cita sus fuentes",
    text: "Cada dato público lleva su enlace; si no hay evidencia, lo dice en vez de inventar.",
    href: `${REPO}docs/evaluacion_modulo2.md`,
    link: "Ver la evaluación de recuperación",
  },
  {
    title: "Calcula las cifras en código",
    text: "El plan de producción sale de un optimizador lineal verificado contra una referencia independiente.",
    href: `${REPO}docs/evaluacion_planificacion_directa.md`,
    link: "Ver la evaluación del optimizador",
  },
  {
    title: "Pide tu «Sí» antes de guardar",
    text: "Contactar un asesor, recordar tu perfil o guardar una propuesta exige una confirmación.",
    href: null,
    link: "Ver el catálogo de herramientas",
  },
  {
    title: "Recuerda con permiso",
    text: "Puedes ver lo que recuerda y borrarlo; los usuarios del canal aparecen con un seudónimo.",
    href: null,
    link: "Ver la evidencia técnica",
  },
];

export function Guarantees() {
  return (
    <section aria-labelledby="guarantees-heading" className="guarantees">
      <h2 className="section-title" id="guarantees-heading">
        Cómo responde
      </h2>
      <ul className="guarantees__list">
        {GUARANTEES.map((item) => (
          <li className="guarantees__item" key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
            {item.href ? (
              <a href={item.href} rel="noreferrer" target="_blank">
                {item.link}
              </a>
            ) : (
              <Link to="/evidencia">{item.link}</Link>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
