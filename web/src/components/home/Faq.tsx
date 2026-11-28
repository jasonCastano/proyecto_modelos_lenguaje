/**
 * Preguntas frecuentes de la entrada (spec 031, copy.md): cinco preguntas, respuestas planas.
 */
const QUESTIONS = [
  {
    q: "¿Es un canal oficial de Manuelita?",
    a: "No. Es un proyecto académico de la Maestría en IA y Ciencia de Datos de la UAO y responde solo con información pública.",
  },
  {
    q: "¿De dónde salen las respuestas?",
    a: "Del sitio de Manuelita, sus informes de sostenibilidad y noticias públicas, con la cita de cada fragmento.",
  },
  {
    q: "¿Puedo usarla por WhatsApp?",
    a: "Sí. El mismo agente responde en el número de WhatsApp del proyecto, con los mismos perfiles.",
  },
  {
    q: "¿Las cifras de planificación son reales?",
    a: "No. Son datos sintéticos de demostración: muestran la capacidad del optimizador, no la operación de Manuelita.",
  },
  {
    q: "¿Guarda lo que escribo?",
    a: "Solo lo que apruebas con «SÍ». Con /olvidar borras tu perfil guardado.",
  },
];

export function Faq() {
  return (
    <section aria-labelledby="preguntas-title" className="site-section site-section--surface" id="preguntas">
      <div className="wrap faq">
        <h2 className="site-h2" id="preguntas-title">
          Preguntas frecuentes
        </h2>
        <div className="faq__list">
          {QUESTIONS.map((item) => (
            <details className="faq__item" key={item.q} open>
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
