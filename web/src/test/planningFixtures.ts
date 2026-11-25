import type { PlanComparison, PlanResponse, PlantSnapshot } from "../lib/types";

export const snapshot: PlantSnapshot = {
  week: "2026-W48",
  data_version: "v1",
  seed: 2026,
  cane_available: 54140,
  cane_quality: 13.3,
  capacities: [
    { area: "molino", nominal: 60000, factor: 1, effective: 60000, unit: "t de caña" },
    { area: "destileria", nominal: 1954000, factor: 1, effective: 1954000, unit: "L de etanol" },
    { area: "caldera", nominal: 40010, factor: 1, effective: 40010, unit: "t de vapor" },
    { area: "turbogenerador", nominal: 4000, factor: 0.92, effective: 3680, unit: "MWh" },
  ],
  equipment: [],
  inventories: { sugar_t: 1200, ethanol_l: 150000, molasses_t: 300 },
  current_mix: { x_s: 50000, x_e: 4140 },
  commitments: [
    {
      id: "c-azucar-1",
      product: "sugar",
      min_quantity: 4470,
      unit: "t",
      priority: 1,
      counterparty: "Cliente industrial A",
    },
    {
      id: "c-etanol-1",
      product: "ethanol",
      min_quantity: 910000,
      unit: "L",
      priority: 1,
      counterparty: "Mezcla E10",
    },
    {
      id: "c-energia-1",
      product: "power",
      min_quantity: 1000,
      unit: "MWh",
      priority: 2,
      counterparty: "Operador de red",
    },
  ],
  prices: { sugar: 1, ethanol: 1, power: 1 },
  ranges: {
    cane_delta_pct: { min: -50, max: 50 },
    cane_quality: { min: 9, max: 16 },
    steam_limit: { min: 0 },
    price_sugar_pct: { min: -50, max: 50 },
    price_ethanol_pct: { min: -50, max: 50 },
    price_power_pct: { min: -50, max: 50 },
  },
  synthetic: true,
  label: "Datos sintéticos de demostración",
};

export const plan: PlanResponse = {
  plan_id: "p-0aed9288",
  status: "optimal",
  scenario: { cane_delta_pct: -15, prioritize: "margin" },
  resolved: { cane: 46019 },
  mix: { x_s: 39513, x_e: 6506, b: 12977, v: 28680, g: 1358 },
  products: { sugar: 4653, ethanol: 910000, power: 1358 },
  margin: 6253633156,
  binding: {
    constraint: "compromiso de etanol",
    dual: 598,
    unit: "COP por L de etanol comprometido",
    weight: 1,
    commitment: true,
  },
  sensitivity: [],
  shortfalls: [],
  alternatives: [
    {
      name: "mezcla actual",
      margin: 6334169477,
      products: { sugar: 4877, ethanol: 775313, power: 1358 },
      delta_vs_best: 80536321,
      violations: ["compromiso de etanol"],
    },
  ],
  assumptions: ["modelo lineal semanal"],
  week: "2026-W48",
  data_version: "v1",
  synthetic: true,
  label: "Datos sintéticos de demostración",
  decision_phrase: "El agente recomienda; el equipo de planta decide.",
};

export const infeasible: PlanResponse = {
  ...plan,
  plan_id: "p-deadbeef",
  status: "infeasible_relaxed",
  binding: null,
  alternatives: [],
  shortfalls: [{ commitment_id: "c-etanol-1", product: "ethanol", missing: 320000, unit: "L" }],
};

export const comparison: PlanComparison = {
  base: { ...plan, plan_id: "p-base0001", mix: { ...plan.mix, x_s: 48753, x_e: 5387 } },
  scenario: plan,
  mix_delta: {
    sugar: { tonnes: -9240, points: -4.1 },
    ethanol: { tonnes: 1119, points: 4.1 },
  },
  products_delta: [
    { product: "sugar", base: 5740, scenario: 4653, delta: -1087, unit: "t" },
    { product: "ethanol", base: 910000, scenario: 910000, delta: 0, unit: "L" },
    { product: "power", base: 1600, scenario: 1358, delta: -242, unit: "MWh" },
  ],
  commitments: [
    {
      id: "c-azucar-1",
      product: "sugar",
      required: 4470,
      unit: "t",
      met_base: true,
      met_scenario: true,
      gap_base: 0,
      gap_scenario: 0,
    },
  ],
  margin_delta: -1199476018,
  synthetic: true,
};
