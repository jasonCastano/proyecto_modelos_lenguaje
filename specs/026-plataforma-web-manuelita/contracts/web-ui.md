# Contrato: interfaz web (rutas, áreas y accesibilidad)

**Spec**: FR-001 a FR-010, FR-030, FR-031 · **Diseño**: [`../design.md`](../design.md)

## Rutas

| Ruta | Área | Acceso | Componentes raíz |
|---|---|---|---|
| `/` | Entrada pública | Todos | `pages/Home.tsx`, que incluye la `RagConsole` existente para Consulta, Resumen y FAQ |
| `/agente` | Espacio de trabajo | Todos | `pages/Agent.tsx`, que contiene `ProfilePicker`, el `ChatView` actual, `SourcesPanel`, `MemoryPanel` y `ProfileSuggestions` |
| `/planificacion` | Consola | Planificador autorizado; los demás ven `PlannerGate` | `pages/Planning.tsx`, que contiene `ScenarioForm`, `CaneFlow`, `CommitmentLedger`, `PlantStatePanel`, `ComparisonView` y `ProposalDialog` |
| `/evidencia` | Panel técnico | Todos | `pages/Evidence.tsx`, que contiene `ServiceStatusBar`, `ToolCatalogTable`, `TraceViewer` y `EvaluationsTable` |

Las rutas desconocidas redirigen a `/` con el aviso «Esa página no existe; te llevamos a la entrada».

El marco común (`AppShell`) tiene:

- el rail con el tallo de caña, que pasa a barra inferior en teléfono;
- la barra superior con el área, el perfil activo y el modo demo;
- un pie con la declaración académica, y la etiqueta sintética en las áreas con datos de planta.

## Textos fijos

| Clave | Texto |
|---|---|
| Declaración | «Proyecto académico de la Maestría en IA y Ciencia de Datos (UAO). No es un canal oficial de Manuelita.» |
| Etiqueta sintética | «Datos sintéticos de demostración» |
| Frase de decisión | «El agente recomienda; el equipo de planta decide.» |
| Aviso de acceso | «La planificación es solo para el equipo de planta autorizado. Puedes hablar con el agente en otro perfil.» |
| Sin solución | «No hay un plan que cumpla todos los compromisos. Estos son los faltantes, por prioridad.» |

## Acciones y avisos

En cada acción, el verbo del botón se repite en su aviso:

| Botón | Aviso al terminar |
|---|---|
| «Calcular plan» | «Plan calculado» |
| «Comparar con el plan base» | Se muestra la comparación |
| «Explicar con el agente» | Lleva a `/agente` y envía el mensaje |
| «Guardar propuesta» | Abre el diálogo «¿Guardar esta propuesta…?» con «Sí, guardar» y «No». El aviso es «Propuesta guardada» o «Propuesta descartada» |

## Accesibilidad y responsive (pruebas en `tests/e2e/`)

- Sin desplazamiento horizontal a 360, 768, 1440 y 1920 px. `test_responsive.py` se amplía a las cuatro rutas.
- `axe-core` sin violaciones `serious` ni `critical` en las cuatro rutas.
- Foco visible y orden de tabulación lógico. El diálogo de propuesta atrapa el foco y lo devuelve al cerrarse.
- `CaneFlow` lleva `role="img"`, `<title>` y `<desc>` con las cifras, y una tabla equivalente visible bajo un
  `<details>`.
- Con `prefers-reduced-motion: reduce` no hay transiciones de las bandas.
