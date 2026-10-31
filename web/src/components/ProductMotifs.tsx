import type { ReactNode } from "react";

interface Motif {
  title: string;
  copy: string;
  icon: ReactNode;
}

const motifs: Motif[] = [
  {
    title: "Caña",
    copy: "Surcos y tallos: la estructura del pipeline.",
    icon: (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path className="motif-stroke" d="M20 58V12M31 58V8M42 58V16" />
        <path className="motif-stroke" d="M20 46C12 42 8 36 6 29M31 38C40 34 45 28 47 21M42 48C51 44 56 37 58 30" />
        <path className="motif-accent" d="M20 24H31M31 32H42M42 42H52" />
      </svg>
    ),
  },
  {
    title: "Azúcar",
    copy: "Cristales que se vuelven unidades de conocimiento.",
    icon: (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path className="motif-stroke" d="M32 7L52 20L46 46L24 56L10 36L17 15Z" />
        <path className="motif-accent" d="M32 7L26 30L46 46M26 30L10 36M26 30L24 56" />
        <circle className="motif-fill" cx="26" cy="30" r="3" />
      </svg>
    ),
  },
  {
    title: "Etanol",
    copy: "Fermentación y energía: procesos que conectan datos.",
    icon: (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path className="motif-stroke" d="M22 8H42M26 8V24L15 48C13 53 17 57 22 57H42C47 57 51 53 49 48L38 24V8" />
        <path className="motif-accent" d="M20 44C26 40 30 48 36 44C40 41 44 42 47 45" />
        <circle className="motif-fill" cx="30" cy="50" r="2" />
        <circle className="motif-fill" cx="39" cy="47" r="2" />
      </svg>
    ),
  },
  {
    title: "Energía",
    copy: "La onda de la evaluación: medir para responder mejor.",
    icon: (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path className="motif-stroke" d="M6 34H15L22 18L31 50L40 26L47 34H58" />
        <path className="motif-accent" d="M15 42H22M47 20H54" />
        <circle className="motif-fill" cx="31" cy="50" r="2.5" />
      </svg>
    ),
  },
  {
    title: "Palma",
    copy: "Otra cosecha del mismo paisaje agroindustrial.",
    icon: (
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <path className="motif-stroke" d="M32 58V24" />
        <path className="motif-stroke" d="M32 24C22 12 12 12 6 17C16 20 23 25 32 24M32 24C42 12 52 12 58 17C48 20 41 25 32 24M32 24C24 34 14 38 7 38C15 44 25 42 32 34M32 24C40 34 50 38 57 38C49 44 39 42 32 34" />
        <circle className="motif-fill" cx="32" cy="22" r="3" />
      </svg>
    ),
  },
];

export function ProductMotifs() {
  return (
    <section className="products" id="productos" aria-labelledby="products-title">
      <div className="section-head">
        <div>
          <p className="section-label">El paisaje que sostiene la evidencia</p>
          <h2 id="products-title">Motivos de cosecha, no decoración</h2>
        </div>
        <p className="section-intro">
          La caña, el azúcar, el etanol, la energía y la palma ordenan la lectura visual del
          corpus. Cada trazo acompaña una idea del sistema y no afirma productos o cifras que la
          fuente no sostenga.
        </p>
      </div>
      <div className="product-grid">
        {motifs.map((motif) => (
          <article className="product" key={motif.title}>
            {motif.icon}
            <h3>{motif.title}</h3>
            <p>{motif.copy}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
