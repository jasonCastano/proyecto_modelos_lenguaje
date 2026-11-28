/**
 * Planificación en la entrada (spec 031, banda oscura): un diagrama de un insumo, un proceso y tres
 * carriles (caña → optimizador → azúcar, etanol y energía) con pulsos que recorren las líneas en 3 s,
 * con botón de pausa; sin cifras (las calcula el optimizador en `/planificacion`). Junto a él, una foto
 * sustituta de una plantación de caña.
 */
import { useEffect, useRef, useState } from "react";

import { photoSrc, photoSrcSet, PHOTOS } from "../../data/photos";
import { productByKey } from "../../data/products";
import { Link } from "../../lib/router";
import { PRODUCT_GLYPHS } from "../brand/ProductGlyphs";

const LANES = [
  { key: "sugar", y: 70 },
  { key: "ethanol", y: 170 },
  { key: "power", y: 270 },
] as const;

function Diagram({ paused }: { paused: boolean }) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = ref.current;
    if (!svg || typeof svg.pauseAnimations !== "function") return;
    if (paused) svg.pauseAnimations();
    else svg.unpauseAnimations();
  }, [paused]);

  return (
    <svg
      ref={ref}
      aria-labelledby="diagram-title"
      className="flow-diagram"
      data-paused={paused || undefined}
      role="img"
      viewBox="0 0 540 340"
    >
      <title id="diagram-title">
        La caña entra al optimizador, que la reparte entre azúcar, etanol y energía.
      </title>
      {LANES.map((lane) => (
        <path
          className="flow-diagram__line"
          d={`M196 170 C 260 170, 270 ${lane.y}, 330 ${lane.y}`}
          id={`lane-${lane.key}`}
          key={`line-${lane.key}`}
        />
      ))}
      <path className="flow-diagram__line" d="M110 170 H196" id="lane-in" />
      <circle className="flow-diagram__pulse" r="5">
        <animateMotion dur="3s" repeatCount="indefinite">
          <mpath href="#lane-in" />
        </animateMotion>
      </circle>
      {LANES.map((lane, i) => (
        <circle
          className="flow-diagram__pulse"
          key={`pulse-${lane.key}`}
          r="5"
          style={{ fill: productByKey(lane.key).color }}
        >
          <animateMotion begin={`${0.6 + i * 0.4}s`} dur="3s" repeatCount="indefinite">
            <mpath href={`#lane-${lane.key}`} />
          </animateMotion>
        </circle>
      ))}
      <g className="flow-diagram__node">
        <rect height="88" rx="14" width="96" x="14" y="126" />
        <PRODUCT_GLYPHS.cane height={30} width={30} x={47} y={140} />
        <text x="62" y="194">Caña</text>
      </g>
      <g className="flow-diagram__node flow-diagram__node--core">
        <rect height="88" rx="14" width="112" x="196" y="126" />
        <text x="252" y="164">Optimizador</text>
        <text className="flow-diagram__small" x="252" y="186">
          programación lineal
        </text>
      </g>
      {LANES.map((lane) => {
        const product = productByKey(lane.key);
        const Glyph = PRODUCT_GLYPHS[lane.key];
        return (
          <g className="flow-diagram__node" key={`node-${lane.key}`}>
            <rect height="64" rx="12" width="196" x="330" y={lane.y - 32} />
            <circle cx="360" cy={lane.y} fill={product.color} r="16" />
            <Glyph height={20} width={20} x={350} y={lane.y - 10} />
            <text className="flow-diagram__label" x="388" y={lane.y + 6}>
              {product.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function PlanningBand() {
  const [paused, setPaused] = useState(
    () =>
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const photo = PHOTOS.cosecha;

  return (
    <section
      aria-labelledby="planificacion-title"
      className="site-section site-section--inv planning-band"
      id="planificacion"
    >
      <div className="wrap planning-band__grid">
        <div className="planning-band__text">
          <h2 className="site-h2" id="planificacion-title">
            La caña de la semana, repartida por un optimizador
          </h2>
          <p className="site-lead">
            Si llega menos caña, Valer-IA calcula cuánto azúcar, etanol y energía cumplen los
            compromisos, qué lo limita y una alternativa. Usa datos sintéticos.
          </p>
          <div className="planning-band__actions">
            <Link className="btn" to="/planificacion">
              Abrir la planificación
            </Link>
            <button
              aria-pressed={paused}
              className="btn btn--line"
              onClick={() => setPaused((value) => !value)}
              type="button"
            >
              {paused ? "Reanudar el diagrama" : "Pausar el diagrama"}
            </button>
          </div>
        </div>
        <div className="planning-band__visual">
          <div className="photo planning-band__photo">
            <img
              alt={photo.alt}
              data-source="stand-in"
              data-subject={photo.subject}
              decoding="async"
              height={463}
              width={700}
              loading="lazy"
              sizes="(min-width: 1024px) 628px, 100vw"
              src={photoSrc(photo.id)}
              srcSet={photoSrcSet(photo.id)}
            />
          </div>
          <div className="planning-band__diagram">
            <Diagram paused={paused} />
          </div>
        </div>
      </div>
    </section>
  );
}
