# Fase 0 — Investigación: entrada canónica de scraping

**Feature**: `005-scrape-empresa-entrypoint`
**Fecha**: 2026-10-30
**Estado**: decisiones cerradas; sin `NEEDS CLARIFICATION`.

## 1. Fachada frente a un segundo crawler

- **Decisión**: `scripts/scrape_empresa.py` es una fachada fina sobre el pipeline de bronce existente.
  La lógica de descubrimiento, extracción, política, almacenamiento y métricas permanece en
  `CampaignRunner`, el fetcher HTTP, `PolicyEngine`, `BronzeStorage` y `Catalog`.
- **Racional**: la especificación prohíbe duplicar el crawler; el bronce ya está probado y auditado.
  Una fachada reduce el riesgo de divergencia y mantiene una sola fuente de verdad.
- **Alternativas consideradas**:
  - Reimplementar el flujo en el script: rechazado por duplicación y riesgo de saltarse políticas.
  - Renombrar `run_campaign.py`: rechazado porque rompe referencias existentes y no aporta una
    interfaz nueva.

## 2. Analizador de argumentos

- **Decisión**: usar `argparse` de la biblioteca estándar, con un parser propio y ayuda en español.
- **Racional**: es la convención del proyecto (`pml` ya usa `argparse`), no añade dependencias y permite
  controlar el comportamiento de `--help` y de la invocación sin argumentos.
- **Alternativas consideradas**:
  - `click` o `typer`: añaden dependencias y no aportan valor para una sola entrada.
  - Parseo manual de `sys.argv`: más frágil y difícil de testear.

## 3. Estado de campaña y reanudación

- **Decisión**: consultar `Catalog.get_campaign` antes de ejecutar y aplicar esta matriz:

  | Estado existente | Sin `--resume` | Con `--resume` |
  |------------------|----------------|----------------|
  | No existe | Crear y ejecutar | Error de uso (código 2) |
  | `planned` | Reanudar automáticamente | Reanudar |
  | `paused` | Reanudar automáticamente | Reanudar |
  | `failed` | Reanudar automáticamente | Reanudar |
  | `running` | Rechazar por concurrencia | Rechazar por concurrencia |
  | `completed` | Reportar completada, sin red | Reportar completada, sin red |
  | `aborted` | Error: usar un identificador nuevo | Error: usar un identificador nuevo |

- **Racional**: coincide con el comportamiento actual de `run_campaign.py` y del runner, pero lo hace
  explícito y testeable. Evita reabrir campañas terminadas y evita dos procesos concurrentes.
- **Alternativas consideradas**:
  - Reanudar siempre: riesgo de mezclar ejecuciones y perder trazabilidad.
  - Preguntar interactivamente: incompatible con CI y con `--json`.

## 4. Aislamiento del `--dry-run`

- **Decisión**: ejecutar el `--dry-run` contra una raíz de bronce temporal (`data_root` en un directorio
  temporal) y descartarla al terminar. El catálogo y el almacenamiento reales no se abren en modo
  escritura.
- **Racional**: `CampaignRunner` crea la campaña y escribe estado incluso en modo seco. La especificación
  exige cero artefactos y cero registros de catálogo en el bronce real. Aislar la raíz es la forma menos
  invasiva de cumplirlo sin cambiar el runner.
- **Alternativas consideradas**:
  - Modificar `CampaignRunner` para no crear campaña en seco: cambia el comportamiento del núcleo y
    afecta a pruebas existentes.
  - No ejecutar nada y solo validar la configuración: no valida descubrimiento ni conectividad, que es
    el valor del `--dry-run`.

## 5. Orquestación compartida

- **Decisión**: extraer una función `start_campaign(...)` a un módulo de servicio
  (`src/proyecto_modelos_lenguaje/campaign_service.py`) que construye catálogo, almacenamiento, fetcher y
  runner, ejecuta la campaña y devuelve un resumen con duración y políticas. `cmd_campaign_start` y la
  nueva entrada canónica la reutilizan.
- **Racional**: evita duplicar las ~15 líneas de orquestación entre la CLI y el script, y permite inyectar
  un fetcher o una raíz temporal en pruebas.
- **Alternativas consideradas**:
  - Duplicar la orquestación en el script: viola la simplicidad y crea dos rutas que pueden divergir.
  - Llamar a `main(["campaign","start",...])` y capturar la salida: frágil para combinar JSON y duración.

## 6. Salida humana y JSON

- **Decisión**: una sola estructura `ScrapeOutcome` con parámetros efectivos, resumen del pipeline,
  políticas agregadas, duración y código de salida. En modo humano se imprime una tabla legible; en modo
  `--json` se emite un único objeto validable contra un esquema.
- **Racional**: el operador necesita contexto antes de la ejecución y el evaluador necesita una salida
  estable. Un solo objeto evita JSON parciales o duplicados.
- **Alternativas consideradas**:
  - Dejar que el pipeline imprima su JSON y añadir líneas sueltas: rompe el contrato de un único objeto.
  - Solo salida humana: impide la automatización y la comparación con la línea base.

## 7. Códigos de salida

- **Decisión**: `0` éxito (incluye campaña completada sin reejecutar), `2` error de uso, configuración o
  validación previa, `4` campaña pausada por límite o interrupción, `1` fallo inesperado del pipeline.
- **Racional**: distingue un error del operador de un fallo de ejecución y conserva el código `4` que ya
  devuelve `CampaignSummary` cuando la campaña queda pausada.
- **Alternativas consideradas**:
  - Todo distinto de cero como `1`: impide que un script distinga uso incorrecto de fallo de red.
  - `argparse` con `SystemExit(2)` sin control: no permite emitir JSON de error.

## 8. Resolución de rutas y raíz del proyecto

- **Decisión**: las rutas relativas de `--config` se resuelven contra la raíz del proyecto, no contra el
  directorio actual. Las rutas reportadas se muestran relativas al proyecto cuando sea posible.
- **Racional**: el comando debe funcionar igual desde la raíz, desde `scripts/` o desde el IDE; la
  reproducibilidad exige que la configuración no dependa del `cwd`.
- **Alternativas consideradas**:
  - Resolver contra el `cwd`: produce resultados distintos según dónde se invoque.
  - Exigir rutas absolutas: incómodo y no portable.

## 9. Concurrencia

- **Decisión**: confiar en el índice único parcial de `campaigns(status) WHERE status='running'` y
  traducir el error de la base de datos a un mensaje accionable. Antes de ejecutar, si la campaña objetivo
  está `running`, se rechaza; si otra campaña está en ejecución, el runner lo detecta al cambiar el estado.
- **Racional**: no se añade un sistema de bloqueos nuevo; se usa la garantía transaccional existente.
- **Alternativas consideradas**:
  - Archivo de bloqueo propio: otra fuente de verdad y riesgo de bloqueos huérfanos.
  - No detectar concurrencia: corrompe contadores y mezcla campañas.

## 10. Estrategia de pruebas

- **Decisión**: pruebas unitarias para parseo, validación, matriz de estados y renderizado; pruebas de
  contrato para los esquemas JSON; pruebas de integración con el servidor local de `tests/conftest.py` y
  una raíz temporal. Sin red externa.
- **Racional**: el proyecto ya tiene un servidor de fixtures y un `build_runner`; reutilizarlos mantiene
  las pruebas rápidas y deterministas.
- **Alternativas consideradas**:
  - Probar contra el sitio real: lento, frágil y dependiente de la red.
  - Solo pruebas unitarias: no valida la delegación ni el aislamiento del `--dry-run`.

## 11. Dependencias

- **Decisión**: no añadir dependencias. Se usa la biblioteca estándar (`argparse`, `dataclasses`,
  `pathlib`, `tempfile`, `time`, `json`) y los módulos existentes del proyecto.
- **Racional**: la constitución prioriza simplicidad y reproducibilidad; una fachada no justifica nuevas
  dependencias.
- **Alternativas consideradas**:
  - Añadir un framework de CLI: innecesario.
  - Añadir un motor de plantillas para la salida: la salida es texto y JSON simple.
