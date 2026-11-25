/**
 * Flujo de caña (spec 026, design.md §3): el elemento memorable de la plataforma.
 *
 * Dos orígenes con la misma escala en toneladas: la caña molida se reparte entre la línea de
 * azúcar (`x_s`) y el jugo directo a etanol (`x_e`), y el bagazo de esa caña (`b`) se quema para
 * vapor y energía. Las bandas solo dibujan lo que manda el servidor; aquí no se calcula ningún plan.
 * Sin solución factible no se dibuja nada como si lo fuera.
 */
import { useEffect, useState } from "react";

import { fmt, PRODUCT_LABEL, PRODUCT_UNIT } from "../../lib/planningFormat";
import type { PlanResponse, ProductName } from "../../lib/types";
import { Cane, Ethanol, Power, Sugar } from "../brand/ProductGlyphs";

/** Altura útil (px del viewBox) que ocupa la caña molida: azúcar + etanol. */
export const FLOW_HEIGHT = 200;
const LENGTH = 560;
const ORIGIN_X = 96;
const NODE = 14;
const GAP = 26;
const MARGIN = 24;
const SPREAD = 44;

const BANDS: { id: ProductName; key: "x_s" | "x_e" | "b"; source: string }[] = [
  { id: "sugar", key: "x_s", source: "caña a la línea de azúcar" },
  { id: "ethanol", key: "x_e", source: "caña a jugo para etanol" },
  { id: "power", key: "b", source: "bagazo quemado para vapor y energía" },
];
const GLYPH = { sugar: Sugar, ethanol: Ethanol, power: Power };

interface Band {
  id: ProductName;
  thickness: number;
  y0: number;
  y1: number;
  tonnes: number;
}

function layout(mix: PlanResponse["mix"], scale: number): Band[] {
  const sugar = mix.x_s * scale;
  const ethanol = mix.x_e * scale;
  const power = mix.b * scale;
  const caneTop = MARGIN;
  const bagasseTop = MARGIN + FLOW_HEIGHT + GAP * 1.5;
  // Los destinos se separan a la derecha: la caña se abre en tres productos.
  const ethanolTarget = MARGIN + sugar + SPREAD;
  const powerTarget = Math.max(bagasseTop, ethanolTarget + ethanol + SPREAD);
  return [
    { id: "sugar", thickness: sugar, y0: caneTop, y1: MARGIN, tonnes: mix.x_s },
    { id: "ethanol", thickness: ethanol, y0: caneTop + sugar, y1: ethanolTarget, tonnes: mix.x_e },
    { id: "power", thickness: power, y0: bagasseTop, y1: powerTarget, tonnes: mix.b },
  ];
}

function bandPath(band: Band, vertical: boolean): string {
  const x0 = ORIGIN_X + NODE;
  const x1 = ORIGIN_X + LENGTH;
  const mid = (x0 + x1) / 2;
  const { y0, y1, thickness: t } = band;
  const p = (x: number, y: number) => (vertical ? `${y} ${x}` : `${x} ${y}`);
  return [
    `M${p(x0, y0)}`,
    `C${p(mid, y0)} ${p(mid, y1)} ${p(x1, y1)}`,
    `L${p(x1, y1 + t)}`,
    `C${p(mid, y1 + t)} ${p(mid, y0 + t)} ${p(x0, y0 + t)}`,
    "Z",
  ].join(" ");
}

function useNarrow(query = "(max-width: 559px)"): boolean {
  const [narrow, setNarrow] = useState(
    () => typeof window !== "undefined" && !!window.matchMedia?.(query).matches,
  );
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return undefined;
    const update = () => setNarrow(media.matches);
    media.addEventListener?.("change", update);
    return () => media.removeEventListener?.("change", update);
  }, [query]);
  return narrow;
}

function usePrefersReducedMotion(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

interface CaneFlowProps {
  plan: PlanResponse;
  compareTo?: PlanResponse | null;
  reducedMotion?: boolean;
}

export function CaneFlow({ plan, compareTo, reducedMotion }: CaneFlowProps) {
  const vertical = useNarrow();
  const prefersReduced = usePrefersReducedMotion();
  const animate = !(reducedMotion ?? prefersReduced);

  if (plan.status !== "optimal") {
    return (
      <div className="cane-flow cane-flow--empty" data-testid="cane-flow">
        <p className="cane-flow__infeasible">
          No hay un plan que cumpla todos los compromisos. Estos son los faltantes, por prioridad.
        </p>
      </div>
    );
  }

  const cane = plan.mix.x_s + plan.mix.x_e;
  const scale = cane > 0 ? FLOW_HEIGHT / cane : 0;
  const bands = layout(plan.mix, scale);
  const base = compareTo && compareTo.status === "optimal" ? layout(compareTo.mix, scale) : null;
  const total = Math.max(bands[2].y0, bands[2].y1) + bands[2].thickness + MARGIN;
  const width = ORIGIN_X + LENGTH + 48;
  const viewBox = vertical ? `0 0 ${total} ${width}` : `0 0 ${width} ${total}`;
  const share = (tonnes: number) => (cane > 0 ? (100 * tonnes) / cane : 0);
  const caneTitle = `Reparto de la caña, semana ${plan.week}`;
  const description = BANDS.map((item, index) => {
    const band = bands[index];
    return `${item.source}: ${fmt(band.tonnes)} t${
      item.id === "power" ? "" : ` (${fmt(share(band.tonnes), 1)} %)`
    }`;
  }).join("; ");

  const node = (x: number, y: number, h: number) =>
    vertical ? { x: y, y: x, width: h, height: NODE } : { x, y, width: NODE, height: h };

  return (
    <figure className="cane-flow" data-orientation={vertical ? "vertical" : "horizontal"} data-testid="cane-flow">
      <svg
        aria-labelledby={`flow-title-${plan.plan_id} flow-desc-${plan.plan_id}`}
        className={`cane-flow__svg${animate ? " cane-flow--animate" : ""}`}
        key={plan.plan_id}
        role="img"
        viewBox={viewBox}
      >
        <title id={`flow-title-${plan.plan_id}`}>{caneTitle}</title>
        <desc id={`flow-desc-${plan.plan_id}`}>
          {description}. Producción: {fmt(plan.products.sugar)} t de azúcar,{" "}
          {fmt(plan.products.ethanol)} L de etanol y {fmt(plan.products.power)} MWh exportados.
        </desc>
        {base
          ? base.map((band) => (
              <path
                className="cane-flow__base"
                d={bandPath(band, vertical)}
                data-base-band={band.id}
                key={`base-${band.id}`}
              />
            ))
          : null}
        <g className="cane-flow__bands">
          {bands.map((band) => (
            <path
              className={`cane-flow__band cane-flow__band--${band.id}`}
              d={bandPath(band, vertical)}
              data-band={band.id}
              data-thickness={band.thickness}
              key={band.id}
            />
          ))}
        </g>
        <rect className="cane-flow__origin" {...node(ORIGIN_X, MARGIN, FLOW_HEIGHT)} />
        <rect
          className="cane-flow__origin cane-flow__origin--bagasse"
          {...node(ORIGIN_X, bands[2].y0, Math.max(bands[2].thickness, 2))}
        />
        <path
          className="cane-flow__link"
          d={
            vertical
              ? `M${MARGIN + FLOW_HEIGHT} ${ORIGIN_X + NODE / 2} L${bands[2].y0} ${ORIGIN_X + NODE / 2}`
              : `M${ORIGIN_X + NODE / 2} ${MARGIN + FLOW_HEIGHT} L${ORIGIN_X + NODE / 2} ${bands[2].y0}`
          }
        />
        <Cane
          className="cane-flow__glyph cane-flow__glyph--cane"
          height={28}
          width={28}
          x={vertical ? MARGIN + FLOW_HEIGHT / 2 - 14 : ORIGIN_X - 40}
          y={vertical ? ORIGIN_X - 40 : MARGIN + FLOW_HEIGHT / 2 - 14}
        />
        {bands.map((band) => {
          const Glyph = GLYPH[band.id];
          const at = band.y1 + band.thickness / 2 - 12;
          return (
            <Glyph
              className={`cane-flow__glyph cane-flow__glyph--${band.id}`}
              height={24}
              key={`glyph-${band.id}`}
              width={24}
              x={vertical ? at : ORIGIN_X + LENGTH + 12}
              y={vertical ? ORIGIN_X + LENGTH + 12 : at}
            />
          );
        })}
      </svg>
      <figcaption className="cane-flow__legend">
        <ul>
          {bands.map((band) => (
            <li className={`cane-flow__item cane-flow__item--${band.id}`} key={band.id}>
              <span className="cane-flow__product">{PRODUCT_LABEL[band.id]}</span>
              <span className="cane-flow__value type-data">
                {fmt(plan.products[band.id])} {PRODUCT_UNIT[band.id]}
              </span>
              <span className="cane-flow__source">
                {band.id === "power"
                  ? `${fmt(band.tonnes)} t de bagazo`
                  : `${fmt(band.tonnes)} t de caña · ${fmt(share(band.tonnes), 1)} %`}
              </span>
            </li>
          ))}
        </ul>
      </figcaption>
      <details className="cane-flow__table">
        <summary>Ver las cifras en tabla</summary>
        <table>
          <caption>{caneTitle}. {plan.label ?? "Datos sintéticos de demostración"}</caption>
          <thead>
            <tr>
              <th scope="col">Destino</th>
              <th scope="col">Toneladas</th>
              <th scope="col">Producción</th>
            </tr>
          </thead>
          <tbody>
            {bands.map((band, index) => (
              <tr key={band.id}>
                <th scope="row">{BANDS[index].source}</th>
                <td className="type-data">{fmt(band.tonnes)} t</td>
                <td className="type-data">
                  {fmt(plan.products[band.id])} {PRODUCT_UNIT[band.id]}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
