/** Estado de planta de la semana (spec 026, FR-011): capacidades, caña e inventarios sintéticos. */
import { AREA_LABEL, fmt } from "../../lib/planningFormat";
import type { PlantSnapshot } from "../../lib/types";

const INVENTORY_LABEL: Record<string, string> = {
  sugar_t: "Azúcar en bodega (t)",
  ethanol_l: "Etanol en tanques (L)",
  molasses_t: "Miel (t)",
};

export function PlantStatePanel({ snapshot }: { snapshot: PlantSnapshot }) {
  return (
    <section aria-labelledby="plant-title" className="plant-panel">
      <h2 className="panel-title" id="plant-title">
        Estado de la planta
      </h2>
      <p className="plant-panel__meta">
        Semana {snapshot.week}, versión {snapshot.data_version}. {snapshot.label}.
      </p>
      <dl className="plant-panel__cane">
        <div>
          <dt>Caña disponible</dt>
          <dd className="type-data">{fmt(snapshot.cane_available)} t</dd>
        </div>
        <div>
          <dt>Calidad</dt>
          <dd className="type-data">{fmt(snapshot.cane_quality, 1)} pol</dd>
        </div>
      </dl>
      <ul className="capacity-list">
        {snapshot.capacities.map((capacity) => {
          const percent = Math.round(capacity.factor * 100);
          return (
            <li className="capacity" key={capacity.area}>
              <span className="capacity__name">
                {AREA_LABEL[capacity.area] ?? capacity.area} al {percent} %
              </span>
              <span className="capacity__value type-data">
                {fmt(capacity.effective)} {capacity.unit}
              </span>
              <span aria-hidden="true" className="capacity__bar">
                <span style={{ inlineSize: `${Math.min(percent, 100)}%` }} />
              </span>
            </li>
          );
        })}
      </ul>
      <dl className="plant-panel__inventory">
        {Object.entries(snapshot.inventories).map(([key, value]) => (
          <div key={key}>
            <dt>{INVENTORY_LABEL[key] ?? key}</dt>
            <dd className="type-data">{fmt(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
