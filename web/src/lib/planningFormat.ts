/** Formato de cifras de planta para la consola (spec 026). Solo formatea: nunca calcula el plan. */
import type { ProductName } from "./types";

const integer = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 });

export function fmt(value: number, decimals: 0 | 1 = 0): string {
  return (decimals ? oneDecimal : integer).format(value);
}

/** Signo explícito con menos tipográfico: «+2,1» o «−320». */
export function signed(value: number, decimals: 0 | 1 = 0): string {
  const rounded = decimals ? Math.round(value * 10) / 10 : Math.round(value);
  if (rounded === 0) return "0";
  return `${rounded > 0 ? "+" : "−"}${fmt(Math.abs(rounded), decimals)}`;
}

export function millions(value: number): string {
  return `COP ${fmt(value / 1_000_000)} millones`;
}

export const PRODUCT_LABEL: Record<ProductName, string> = {
  sugar: "Azúcar",
  ethanol: "Etanol",
  power: "Energía exportada",
};

export const PRODUCT_UNIT: Record<ProductName, string> = {
  sugar: "t",
  ethanol: "L",
  power: "MWh",
};

export const AREA_LABEL: Record<string, string> = {
  molino: "Molienda",
  destileria: "Destilería",
  caldera: "Calderas",
  turbogenerador: "Turbogenerador",
};

export const SCENARIO_LABEL: Record<string, string> = {
  cane_delta_pct: "Caña disponible",
  cane_quality: "Calidad de la caña (pol %)",
  price_sugar_pct: "Precio del azúcar",
  price_ethanol_pct: "Precio del etanol",
  price_power_pct: "Precio de la energía",
  steam_limit: "Vapor máximo (t/semana)",
};

/** Texto del escenario para «Explicar con el agente» (mismos parámetros que la consola). */
export function describeScenario(input: object): string {
  const scenario = input as Record<string, unknown>;
  const parts: string[] = [];
  const pct = (key: string, label: string) => {
    const value = scenario[key];
    if (typeof value === "number") parts.push(`${label} ${signed(value, 1)} %`);
  };
  pct("cane_delta_pct", "caña");
  if (typeof scenario.cane_quality === "number") {
    parts.push(`calidad ${fmt(scenario.cane_quality, 1)} pol`);
  }
  pct("price_sugar_pct", "precio del azúcar");
  pct("price_ethanol_pct", "precio del etanol");
  pct("price_power_pct", "precio de la energía");
  if (typeof scenario.steam_limit === "number") {
    parts.push(`vapor máximo ${fmt(scenario.steam_limit)} t`);
  }
  if (scenario.prioritize === "power") parts.push("priorizando energía");
  return parts.length ? parts.join(", ") : "la caña y los precios de la semana";
}
