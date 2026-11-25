# ADR 0030 — Plataforma web en cuatro áreas, API v1 aparte y dirección visual por producto

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-24
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0029 (plataforma de agentes de la idea 7);
  - ADR 0009 (Streamlit, sustituido desde la spec 012);
  - `specs/026-plataforma-web-manuelita/` (spec, plan, `design.md`, contratos).

## Contexto

La spec 025 convirtió a Valer-IA en la plataforma de agentes de Manuelita, pero la web seguía siendo la página
editorial de los Módulos 1 y 2:

- el chat era una pestaña de la consola de preguntas;
- la planificación industrial solo se veía como texto dentro de la conversación;
- la evidencia del Módulo 3 (catálogo, traza, servicios) solo se mostraba con `/traza` y la terminal.

Streamlit ya no era la interfaz desde la spec 012, y la rúbrica no acepta Streamlit, Gradio ni notebooks. Faltaban
cuatro días para la sustentación del sábado 28.

## Decisión

1. **Cuatro áreas con su propia dirección**:
   - `/`: entrada pública;
   - `/agente`: espacio de trabajo por perfil;
   - `/planificacion`: consola visual del planificador;
   - `/evidencia`: panel técnico.

   Se usa un enrutador propio de unas 60 líneas sobre la History API; el fallback de SPA del backend ya servía
   `index.html` en cualquier ruta.
2. **API v1 aparte**: `api_planning.py` (`/api/v1/planning/*`) y `api_evidence.py` (`/api/v1/evidence/*`). Las
   rutas sin versión (`/api/chat`, `/api/channels/*`, voz, memoria) no cambian, así que el puente de WhatsApp y las
   pruebas del Módulo 3 siguen igual.
3. **Una sola fuente de cifras**:
   - la consola llama a `planning.optimize`, la misma función de la herramienta y del CLI;
   - una prueba compara las tres salidas en los 12 escenarios de la batería;
   - el navegador nunca calcula cifras de planta.
4. **Autorización en el backend**: todo `/api/v1/planning/*`, salvo `/access`, exige `profiles.is_authorized`; la
   UI solo refleja `/access`. Guardar una propuesta tiene dos pasos con confirmación y vence a los 5 minutos.
5. **Dirección visual por producto**, hecha con la skill `frontend-design`:
   - **tipografía**: una sola familia (Archivo variable), cuyo eje de ancho marca el rol: expandida en titulares,
     normal en texto y condensada con cifras tabulares en los datos;
   - **color**: un color fijo de la paleta de Manuelita por producto (caña verde, azúcar amarillo, etanol naranja,
     energía lima);
   - **elemento memorable**: el flujo de caña, un Sankey propio en SVG, con su eco en el tallo de caña del rail de
     navegación;
   - **pictogramas**: propios, sin piezas de la marca.
6. **Precios en el escenario**: `Scenario` gana `price_sugar_pct`, `price_ethanol_pct` y `price_power_pct`, de −50
   a +50. Con `None`, los planes de la spec 025 son idénticos, y una prueba los fija contra un snapshot.

## Alternativas consideradas

- **Next.js o Remix**: exigen un servidor Node aparte y rompen `make app`.
- **Librería de componentes (MUI, Chakra, shadcn)**: impone una estética genérica, contraria a la identidad pedida.
- **Librería de gráficos (Recharts, ECharts, d3-sankey)**: suma entre 50 y 300 kB y su estética por defecto. Un
  Sankey de tres destinos se dibuja en pocas líneas.
- **Migrar todas las rutas a `/api/v1`**: arriesga el canal de WhatsApp en producción a días de la sustentación.
- **Cálculo del plan en TypeScript**: crearía dos fuentes de verdad.
- **Capacidad editable por área en la consola**: invita a relajar capacidades físicas, lo que prohíbe la regla 19
  de la Fase 3. Se ofrecen la calidad, los precios y un límite de vapor que solo puede bajar la capacidad.

## Consecuencias

- La web se presenta como la plataforma del pitch y sirve de respaldo si WhatsApp falla. La consola y el panel
  cubren los bloques técnicos sin abrir la terminal.
- Los componentes de la página editorial salen de la entrada: `Hero`, `ShowcaseStory`, `MetricsBand`,
  `ProductMotifs`, `CaneField` y `Footer`. Su prueba E2E `test_showcase.py` se retira. `GET /api/showcase` se
  conserva en el backend.
- `ChatView` gana props opcionales: el perfil controlado, el mensaje de otra área, la petición de olvido y los
  avisos de turno y memoria. Sin ellas se comporta como antes, y sus pruebas no cambiaron de aserción.
- `docs/herramientas.md` se regenera porque `simulate_production_scenario` y `optimize_production_plan` heredan los
  precios opcionales. El conteo sigue en 26.
- Hay que mantener dos prefijos de API mientras convivan clientes de ambos.
