/**
 * Entrada de la plataforma (spec 026, design.md §3): titular expandido junto a la cadena de
 * productos que nace de la caña. Sin cifra grande ni degradado.
 */
import { Link } from "../../lib/router";
import { PRODUCT_GLYPHS, type ProductKey } from "../brand/ProductGlyphs";

const CHAIN: { key: ProductKey; label: string; x: number; y: number }[] = [
  { key: "sugar", label: "Azúcar", x: 262, y: 40 },
  { key: "ethanol", label: "Etanol", x: 300, y: 112 },
  { key: "power", label: "Energía", x: 300, y: 196 },
  { key: "palm", label: "Palma", x: 262, y: 270 },
  { key: "grape", label: "Uva", x: 150, y: 318 },
  { key: "shrimp", label: "Camarón", x: 44, y: 300 },
  { key: "mussel", label: "Mejillón", x: 8, y: 228 },
];

function ProductChain() {
  return (
    <svg
      aria-labelledby="chain-title"
      className="hero-chain"
      role="img"
      viewBox="0 0 360 380"
    >
      <title id="chain-title">
        De la caña nacen azúcar, etanol y energía; Manuelita también cultiva palma, uva, camarón y
        mejillón.
      </title>
      <path className="hero-chain__stalk" d="M150 372V150" />
      {[330, 290, 250, 210, 170].map((y) => (
        <path className="hero-chain__knot" d={`M138 ${y}h24`} key={y} />
      ))}
      {CHAIN.map((item) => (
        <path
          className={`hero-chain__branch hero-chain__branch--${item.key}`}
          d={`M150 150 C 150 ${item.y + 20}, ${item.x - 20} ${item.y + 20}, ${item.x + 4} ${item.y + 24}`}
          key={`branch-${item.key}`}
        />
      ))}
      {CHAIN.map((item) => {
        const Glyph = PRODUCT_GLYPHS[item.key];
        return (
          <g className={`hero-chain__node hero-chain__node--${item.key}`} key={item.key}>
            <circle cx={item.x + 24} cy={item.y + 24} r="26" />
            <Glyph height={28} width={28} x={item.x + 10} y={item.y + 10} />
          </g>
        );
      })}
      <g className="hero-chain__node hero-chain__node--cane">
        <circle cx="150" cy="128" r="30" />
        <PRODUCT_GLYPHS.cane height={34} width={34} x={133} y={111} />
      </g>
    </svg>
  );
}

export function PlatformHero() {
  return (
    <section aria-labelledby="hero-title" className="platform-hero">
      <div className="platform-hero__copy">
        <h1 className="type-display platform-hero__title" id="hero-title" tabIndex={-1}>
          Un agente para cada persona que trabaja con Manuelita.
        </h1>
        <p className="platform-hero__lead">
          Valer-IA atiende a visitantes, clientes, proveedores, colaboradores y al equipo de planta
          con un perfil para cada uno. Cita sus fuentes, calcula las cifras en código y pide tu «Sí»
          antes de guardar algo.
        </p>
        <p className="platform-hero__note">
          Es un proyecto académico con información pública y una planta de datos sintéticos. No es
          un canal oficial de Manuelita.
        </p>
        <div className="platform-hero__actions">
          <Link className="action action--primary" to="/agente">
            Hablar con el agente
          </Link>
          <Link className="action action--quiet" to="/planificacion">
            Abrir la planificación
          </Link>
        </div>
      </div>
      <ProductChain />
    </section>
  );
}
