# ADR 0005 — Entrada canónica de scraping (`scrape_empresa.py`)

- **Estado**: aceptada
- **Fecha**: 2026-10-30
- **Autores**: Jason Alejandro Castaño, Roberto José Guerrero
- **Contexto**: Módulo 1, tarea M1-02 y rúbrica del curso

## Contexto

La rúbrica exige una entrada canónica `scripts/scrape_empresa.py` ejecutable con
`uv run python scripts/scrape_empresa.py`. El proyecto ya tenía un pipeline de bronce probado, pero la
ejecución requería conocer `pml campaign start`, `scripts/run_campaign.py`, los nombres de campaña y la
configuración. Esa complejidad dificultaba la reproducción por parte de un evaluador.

La constitución permite que la entrada sea un envoltorio del pipeline existente y prohíbe duplicar el
crawler, evadir `robots.txt` o escribir capas posteriores.

## Decisiones

1. **Fachada fina**: `scripts/scrape_empresa.py` solo importa `entrypoint.main`; la lógica de ejecución
   permanece en el pipeline de bronce.
2. **Orquestación compartida**: `campaign_service.start_campaign` construye catálogo, almacenamiento,
   fetcher y runner. Tanto `pml campaign start` como la entrada canónica usan la misma ruta.
3. **Campaña explícita**: `--campaign` es obligatorio para ejecutar. Sin argumentos se muestra ayuda y
   ejemplos, sin red ni estado, para evitar campañas largas accidentales.
4. **Matriz de estados**: crear si no existe; reanudar `planned`, `paused` y `failed`; rechazar `running`
   y `aborted`; no reejecutar `completed`.
5. **Dry-run aislado**: `--dry-run` ejecuta el pipeline contra una raíz temporal y la descarta. El
   catálogo y los artefactos reales no se tocan.
6. **Salida única**: un objeto con parámetros efectivos, resumen, políticas, duración y código de salida;
   en modo humano, una tabla legible.
7. **Códigos de salida**: `0` éxito, `2` error de uso/configuración, `4` campaña pausada, `1` fallo
   inesperado.
8. **Rutas portables**: las rutas relativas se resuelven contra la raíz del proyecto y se reportan
   relativas cuando es posible.
9. **Concurrencia**: se delega en el índice único de campañas `running` del catálogo, traduciendo el error
   a un mensaje accionable.
10. **Sin dependencias nuevas**: solo biblioteca estándar y módulos existentes.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| Reimplementar el crawler en el script | Duplica lógica, riesgos de política y divergencia |
| Renombrar `run_campaign.py` | Rompe referencias y no crea una interfaz nueva |
| Ejecutar una campaña por defecto sin `--campaign` | Riesgo de ejecuciones largas o destructivas |
| Modificar `CampaignRunner` para el dry-run | Afecta el núcleo y las pruebas existentes |
| Capturar la salida de `main` para combinarla | Frágil y difícil de testear |
| Usar un archivo de bloqueo propio | Otra fuente de verdad y bloqueos huérfanos |
| Añadir `click` o `typer` | Dependencia innecesaria para una sola entrada |

## Consecuencias

- El evaluador puede ejecutar y reproducir el scraping con un solo comando documentado.
- La CLI `pml campaign start` conserva su comportamiento y comparte la orquestación.
- El `--dry-run` es seguro para demos y validaciones.
- La salida es apta para automatización y validación contra JSON Schema.
- La entrada no sustituye la revisión de políticas ni la curaduría; solo ejecuta el bronce.

## Validación observada

- `uv run python scripts/scrape_empresa.py --help` y sin argumentos: código `0`, ayuda completa, sin red.
- `--dry-run --limit 1 --json`: `artifacts_stored=0`, sin campaña nueva en el bronce real.
- Pruebas unitarias, de contrato y de integración: campaña nueva, reanudación sin duplicados, fuente
  bloqueada, equivalencia con la ejecución directa y capas plata/oro sin cambios.
- `uv run ruff check .` y `uv run pytest -q` en verde.
- M1-02 marcada como completada en la bitácora.

## Licencias

Sin dependencias nuevas. Se reutilizan la biblioteca estándar y los módulos MIT del proyecto.
