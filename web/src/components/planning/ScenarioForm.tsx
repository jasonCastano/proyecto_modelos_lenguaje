/**
 * Escenario de la consola (spec 026, FR-012): controles acotados con los rangos que manda el
 * backend (`snapshot.ranges`, tomados del esquema de `Scenario`). Solo se envían los campos tocados;
 * un valor fuera de rango se explica y bloquea el cálculo antes de llamar al servidor.
 */
import { useState, type FormEvent } from "react";

import { fmt, SCENARIO_LABEL } from "../../lib/planningFormat";
import type { PlantSnapshot, Scenario, ScenarioField } from "../../lib/types";

interface Control {
  field: ScenarioField;
  unit: "%" | "pol" | "t";
  step: number;
  slider: boolean;
  hint: string;
}

const CONTROLS: Control[] = [
  { field: "cane_delta_pct", unit: "%", step: 1, slider: true, hint: "−15 significa 15 % menos caña" },
  { field: "cane_quality", unit: "pol", step: 0.1, slider: true, hint: "Sacarosa aparente de la caña" },
  { field: "price_sugar_pct", unit: "%", step: 1, slider: true, hint: "Cambio sobre el precio de referencia" },
  { field: "price_ethanol_pct", unit: "%", step: 1, slider: true, hint: "Cambio sobre el precio de referencia" },
  { field: "price_power_pct", unit: "%", step: 1, slider: true, hint: "Cambio sobre el precio de referencia" },
  { field: "steam_limit", unit: "t", step: 100, slider: false, hint: "Solo puede bajar la capacidad de las calderas" },
];

function rangeText(min: number, max: number | undefined, unit: Control["unit"]): string {
  const show = (value: number) => (value < 0 ? `−${fmt(Math.abs(value), 1)}` : fmt(value, 1));
  const suffix = unit === "%" ? " %" : unit === "pol" ? " pol" : " t";
  return max === undefined
    ? `Usa un valor de ${show(min)}${suffix} o más`
    : `Usa un valor entre ${show(min)}${suffix} y ${show(max)}${suffix}`;
}

interface ScenarioFormProps {
  snapshot: PlantSnapshot;
  busy: boolean;
  onCalculate: (scenario: Scenario) => void;
  onCompare: (scenario: Scenario) => void;
}

export function ScenarioForm({ snapshot, busy, onCalculate, onCompare }: ScenarioFormProps) {
  const [values, setValues] = useState<Partial<Record<ScenarioField, string>>>({});
  const [prioritize, setPrioritize] = useState<"margin" | "power">("margin");
  const [prioritizeTouched, setPrioritizeTouched] = useState(false);

  const defaults: Partial<Record<ScenarioField, number>> = {
    cane_delta_pct: 0,
    cane_quality: snapshot.cane_quality,
    price_sugar_pct: 0,
    price_ethanol_pct: 0,
    price_power_pct: 0,
  };

  function errorFor(control: Control): string | null {
    const raw = values[control.field];
    if (raw === undefined || raw === "") return null;
    const value = Number(raw);
    const range = snapshot.ranges[control.field];
    if (!range) return null;
    if (!Number.isFinite(value) || value < range.min || (range.max !== undefined && value > range.max)) {
      return rangeText(range.min, range.max, control.unit);
    }
    return null;
  }

  const invalid = CONTROLS.some((control) => errorFor(control) !== null);

  function scenario(): Scenario {
    const result: Scenario = {};
    for (const control of CONTROLS) {
      const raw = values[control.field];
      if (raw !== undefined && raw !== "") result[control.field] = Number(raw);
    }
    if (prioritizeTouched) result.prioritize = prioritize;
    return result;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!invalid) onCalculate(scenario());
  }

  return (
    <form aria-labelledby="scenario-title" className="scenario-form" noValidate onSubmit={submit}>
      <h2 className="panel-title" id="scenario-title">
        Escenario de la semana
      </h2>
      {CONTROLS.map((control) => {
        const range = snapshot.ranges[control.field];
        const id = `scenario-${control.field}`;
        const error = errorFor(control);
        const current = values[control.field] ?? String(defaults[control.field] ?? "");
        return (
          <div className="scenario-field" data-invalid={error ? true : undefined} key={control.field}>
            <label htmlFor={id}>
              {SCENARIO_LABEL[control.field]}
              <span className="scenario-field__hint">{control.hint}</span>
            </label>
            <div className="scenario-field__inputs">
              {control.slider && range?.max !== undefined ? (
                <input
                  aria-hidden="true"
                  className="scenario-field__slider"
                  max={range.max}
                  min={range.min}
                  onChange={(event) =>
                    setValues((previous) => ({ ...previous, [control.field]: event.target.value }))
                  }
                  step={control.step}
                  tabIndex={-1}
                  type="range"
                  value={current === "" ? range.min : current}
                />
              ) : null}
              <input
                aria-describedby={error ? `${id}-error` : undefined}
                aria-invalid={error ? true : undefined}
                className="scenario-field__number type-data"
                id={id}
                inputMode="decimal"
                max={range?.max}
                min={range?.min}
                onChange={(event) =>
                  setValues((previous) => ({ ...previous, [control.field]: event.target.value }))
                }
                placeholder={control.field === "steam_limit" ? "sin límite" : undefined}
                step={control.step}
                type="number"
                value={current}
              />
              <output className="scenario-field__unit" htmlFor={id}>
                {control.unit}
              </output>
            </div>
            {error ? (
              <p className="field-error" id={`${id}-error`}>
                {error}
              </p>
            ) : null}
          </div>
        );
      })}
      <fieldset className="scenario-priority">
        <legend>Prioridad</legend>
        {(
          [
            ["margin", "Mejor margen"],
            ["power", "Más energía para la red"],
          ] as const
        ).map(([key, label]) => (
          <label key={key}>
            <input
              checked={prioritize === key}
              name="prioritize"
              onChange={() => {
                setPrioritize(key);
                setPrioritizeTouched(true);
              }}
              type="radio"
              value={key}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <div className="scenario-actions">
        <button className="action action--primary" disabled={busy || invalid} type="submit">
          Calcular plan
        </button>
        <button
          className="action action--quiet"
          disabled={busy || invalid}
          onClick={() => onCompare(scenario())}
          type="button"
        >
          Comparar con el plan base
        </button>
      </div>
    </form>
  );
}
