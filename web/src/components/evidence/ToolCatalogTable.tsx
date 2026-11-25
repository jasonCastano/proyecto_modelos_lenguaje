/** Catálogo de herramientas (spec 026, FR-020): tabla densa con filtros por tipo y perfil. */
import { useState } from "react";

import { audienceLabel, AUDIENCES } from "../../lib/platform";
import type { ToolEvidence } from "../../lib/types";

type KindFilter = "all" | "read" | "write";

export function ToolCatalogTable({ tools }: { tools: ToolEvidence[] }) {
  const [kind, setKind] = useState<KindFilter>("all");
  const [profile, setProfile] = useState("all");
  const visible = tools.filter(
    (tool) =>
      (kind === "all" || tool.kind === kind) && (profile === "all" || tool.profiles.includes(profile)),
  );
  return (
    <section aria-labelledby="catalog-title" className="catalog">
      <h2 className="panel-title" id="catalog-title">
        {tools.length} herramientas
      </h2>
      <div className="catalog__filters">
        <label>
          Tipo
          <select onChange={(event) => setKind(event.target.value as KindFilter)} value={kind}>
            <option value="all">Todas</option>
            <option value="read">Lectura</option>
            <option value="write">Escritura con aprobación</option>
          </select>
        </label>
        <label>
          Perfil
          <select onChange={(event) => setProfile(event.target.value)} value={profile}>
            <option value="all">Todos</option>
            {AUDIENCES.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <p className="catalog__count" role="status">
          {visible.length} de {tools.length}
        </p>
      </div>
      <div className="table-scroll">
        <table className="catalog__table type-data">
          <caption className="visually-hidden">Catálogo de herramientas del agente</caption>
          <thead>
            <tr>
              <th scope="col">Herramienta</th>
              <th scope="col">Tipo</th>
              <th scope="col">Perfiles</th>
              <th scope="col">Modo degradado</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((tool) => (
              <tr data-kind={tool.kind} key={tool.name}>
                <th scope="row" title={tool.description}>
                  {tool.name}
                </th>
                <td>{tool.kind === "write" ? "escritura, pide «Sí»" : "lectura"}</td>
                <td>{tool.profiles.map(audienceLabel).join(", ") || "ninguno"}</td>
                <td>{tool.mcp_allowed ? "disponible" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
