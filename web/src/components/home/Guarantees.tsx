/**
 * Garantías de cada respuesta (spec 031): cuatro tarjetas, al modo de las cuatro tarjetas de
 * sostenibilidad del sitio oficial de Manuelita, cada una con su glifo y una frase.
 */
const GUARANTEES = [
  {
    title: "Cita el documento de cada dato",
    body: "La fuente aparece junto a la respuesta y se abre en un paso.",
    tone: "var(--leaf-green)",
    icon: "M5 4h10l4 4v12H5z M15 4v4h4 M8 12h8 M8 16h6",
  },
  {
    title: "Calcula las cifras en código",
    body: "Sumas, promedios y repartos salen de una herramienta, nunca del modelo.",
    tone: "var(--leaf-orange)",
    icon: "M6 3h12v18H6z M9 7h6 M9 11h1 M12 11h1 M15 11h0 M9 15h1 M12 15h1 M15 15v3",
  },
  {
    title: "Pide tu «SÍ» antes de guardar",
    body: "Recordar tu perfil o guardar una propuesta espera tu permiso.",
    tone: "var(--leaf-red)",
    icon: "M5 12l4 4 10-10",
  },
  {
    title: "Dice cuando no sabe",
    body: "Sin evidencia en el corpus, lo dice y te da el canal oficial.",
    tone: "var(--mussel)",
    icon: "M12 3a9 9 0 1 0 0 18a9 9 0 0 0 0-18z M12 8v5 M12 16v.5",
  },
];

export function Guarantees() {
  return (
    <section aria-labelledby="garantias-title" className="site-section site-section--surface" id="garantias">
      <div className="wrap">
        <div className="sec-head">
          <h2 className="site-h2" id="garantias-title">
            Garantías de cada respuesta
          </h2>
          <p className="site-lead">
            Valer-IA responde solo con información pública de Manuelita y te muestra de dónde sale.
          </p>
        </div>
        <ul className="guarantees">
          {GUARANTEES.map((item) => (
            <li className="site-card guarantees__card" key={item.title}>
              <svg
                aria-hidden="true"
                className="guarantees__icon"
                fill="none"
                stroke={item.tone}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.9"
                viewBox="0 0 24 24"
              >
                <path d={item.icon} />
              </svg>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
