/**
 * La frase de la entrada con el momento «letters-assemble» de la skill (spec 031, research R8),
 * reimplementado: las letras empiezan dispersas y giradas y se ordenan una tras otra cuando la sección
 * entra en pantalla, una sola vez. Con «reducir movimiento» la frase queda quieta y visible desde el inicio.
 */
import { useEffect, useRef, useState } from "react";

import { PHOTOS, photoSrc, photoSrcSet } from "../../data/photos";

const PHRASE = "Cada dato, con su fuente.";

function scatter(index: number): React.CSSProperties {
  // Desplazamientos deterministas (sin azar), para que la primera pintura sea estable.
  const x = ((index * 37) % 41) - 20;
  const y = ((index * 53) % 61) - 30;
  const r = ((index * 29) % 50) - 25;
  return {
    "--dx": `${x * 3}px`,
    "--dy": `${y * 2}px`,
    "--rot": `${r}deg`,
    "--i": index,
  } as React.CSSProperties;
}

export function Statement() {
  const ref = useRef<HTMLHeadingElement>(null);
  const [assembled, setAssembled] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const reduce =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || typeof IntersectionObserver === "undefined") {
      setAssembled(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setAssembled(true);
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <section
      aria-labelledby="frase-title"
      className="site-section statement"
      data-moment="letters-assemble"
      id="frase"
    >
      <div className="wrap statement__wrap">
        <div className="statement__text">
        <h2
          aria-label={PHRASE}
          className="statement__line"
          data-assembled={assembled || undefined}
          id="frase-title"
          ref={ref}
        >
          {PHRASE.split(" ").map((word, w, words) => {
            const before = words.slice(0, w).join(" ").length + (w > 0 ? 1 : 0);
            return (
              <span aria-hidden="true" className="statement__word" key={`${word}-${w}`}>
                {[...word].map((letter, l) => (
                  <span className="statement__letter" key={l} style={scatter(before + l)}>
                    {letter}
                  </span>
                ))}
                {w < words.length - 1 ? " " : null}
              </span>
            );
          })}
        </h2>
        <p className="statement__sub">
          Sin evidencia en el corpus, Valer-IA lo dice y te da el canal oficial.
        </p>
        </div>
        <div className="photo statement__photo">
          <img
            alt={PHOTOS.azucar.alt}
            data-source="stand-in"
            data-subject={PHOTOS.azucar.subject}
            decoding="async"
            height={467}
            width={700}
            loading="lazy"
            sizes="(min-width: 1024px) 1100px, 100vw"
            src={photoSrc("azucar")}
            srcSet={photoSrcSet("azucar")}
          />
        </div>
      </div>
    </section>
  );
}
