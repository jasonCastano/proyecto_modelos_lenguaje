/**
 * Pictogramas propios de los productos de Manuelita (spec 026, design.md §4). Trazo de 1,75 px en
 * `currentColor`: el color lo pone quien los usa (un color fijo por producto). No copian piezas
 * de la marca. Sin `title` son decorativos (`aria-hidden`).
 */
import type { ReactNode, SVGProps } from "react";

type GlyphProps = Omit<SVGProps<SVGSVGElement>, "children"> & { title?: string; size?: number };

function Glyph({ title, size = 24, children, ...rest }: GlyphProps & { children: ReactNode }) {
  return (
    <svg
      aria-hidden={title ? undefined : true}
      fill="none"
      focusable="false"
      height={size}
      role={title ? "img" : undefined}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.75}
      viewBox="0 0 24 24"
      width={size}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

/** Caña: tallo con tres nudos y una hoja. */
export function Cane(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M11 22V2" />
      <path d="M9.5 17h3M9.5 11.5h3M9.5 6h3" />
      <path d="M11 11.5c2.5-1 5.5-1.2 8-4.5" />
    </Glyph>
  );
}

/** Azúcar: cristal facetado. */
export function Sugar(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M12 3 20 8v8l-8 5-8-5V8z" />
      <path d="M12 3v18M4 8l8 5 8-5" />
    </Glyph>
  );
}

/** Etanol: gota con menisco. */
export function Ethanol(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M12 3c3.5 4.6 6 8 6 11a6 6 0 0 1-12 0c0-3 2.5-6.4 6-11z" />
      <path d="M8.2 14.5c2.4 1 5.2 1 7.6 0" />
    </Glyph>
  );
}

/** Energía: rayo sobre un haz de bagazo. */
export function Power(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M13 2 7 12h5l-1.5 6L17 8h-5z" />
      <path d="M4 21h16M6 18.5l-2 2.5M18 18.5l2 2.5" />
    </Glyph>
  );
}

/** Miel: gota densa sobre una base. */
export function Molasses(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M12 4c2.6 3.6 4.5 6.2 4.5 8.5a4.5 4.5 0 0 1-9 0C7.5 10.2 9.4 7.6 12 4z" />
      <path d="M5 21h14" />
    </Glyph>
  );
}

/** Palma: racimo de fruto bajo dos hojas. */
export function Palm(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M12 9c-2-3-5-4-8-3M12 9c2-3 5-4 8-3" />
      <circle cx="10" cy="14" r="2" />
      <circle cx="14" cy="14" r="2" />
      <circle cx="12" cy="17.5" r="2" />
      <path d="M12 9v3" />
    </Glyph>
  );
}

/** Uva: racimo. */
export function Grape(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M12 2v3M12 5c1.5-1.5 3.5-1.5 5-1" />
      <circle cx="9" cy="9" r="2" />
      <circle cx="13" cy="9" r="2" />
      <circle cx="11" cy="12.5" r="2" />
      <circle cx="15" cy="12.5" r="2" />
      <circle cx="13" cy="16" r="2" />
      <circle cx="11" cy="19.5" r="1.8" />
    </Glyph>
  );
}

/** Camarón: cuerpo curvo segmentado. */
export function Shrimp(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M18 6c-6-2-12 2-12 8 0 3 2 5 5 5h2" />
      <path d="M9 9.5l2 1.5M7.5 13h2.5M8.5 16.5l2-1" />
      <path d="M13 19l3 2M13 19l1 2.5" />
      <path d="M18 6l3-2M18 6l3 1" />
    </Glyph>
  );
}

/** Mejillón: valva alargada con líneas de crecimiento. */
export function Mussel(props: GlyphProps) {
  return (
    <Glyph {...props}>
      <path d="M5 19C4 13 8 5 15 3c3 2 4 6 2 10-2 5-7 7-12 6z" />
      <path d="M7.5 16.5c3-1 6-4.5 7-9.5M10 18c2.5-1.5 4.5-4 5.5-7" />
    </Glyph>
  );
}

export const PRODUCT_GLYPHS = {
  cane: Cane,
  sugar: Sugar,
  ethanol: Ethanol,
  power: Power,
  molasses: Molasses,
  palm: Palm,
  grape: Grape,
  shrimp: Shrimp,
  mussel: Mussel,
} as const;

export type ProductKey = keyof typeof PRODUCT_GLYPHS;
