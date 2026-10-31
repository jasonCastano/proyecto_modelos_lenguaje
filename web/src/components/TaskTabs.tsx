import type { TaskKind } from "../lib/types";

const tabs: Array<{ id: TaskKind; label: string; hint: string }> = [
  { id: "qa", label: "Consulta", hint: "Pregunta al corpus" },
  { id: "summary", label: "Resumen", hint: "Sintetiza el paquete" },
  { id: "faq", label: "FAQ", hint: "Preguntas frecuentes" },
];

export function TaskTabs({
  task,
  onChange,
}: {
  task: TaskKind;
  onChange: (task: TaskKind) => void;
}) {
  return (
    <div className="task-tabs" role="tablist" aria-label="Tareas del Módulo 1">
      {tabs.map((tab) => (
        <button
          aria-selected={task === tab.id}
          className="task-tab"
          id={`tab-${tab.id}`}
          key={tab.id}
          onClick={() => onChange(tab.id)}
          role="tab"
          tabIndex={task === tab.id ? 0 : -1}
          type="button"
        >
          {tab.label}
          <span className="sr-only"> — {tab.hint}</span>
        </button>
      ))}
    </div>
  );
}
