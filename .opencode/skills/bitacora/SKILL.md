---
name: Bitácora del Proyecto
description: Genera una bitácora fechada del proyecto RAG Ingenio Manuelita con el contexto de CONSTITUTION.md, el estado local y remoto de Git, el avance por fase, los objetivos cumplidos, los pendientes, la cascada secuencial de tareas con dependencias y puertas de calidad, y los próximos pasos. Úsala cuando el usuario pida "bitácora", "estado del proyecto", "avance", "qué falta", "qué sigue" o "tareas pendientes en orden".
---

# Bitácora del Proyecto

## Cuándo usarla

Usa esta skill cuando el usuario pida:

- "genera la bitácora", "registra el avance" o "documenta el estado";
- "¿cómo va el proyecto?", "¿qué falta?" o "¿qué sigue?";
- una revisión de cierre de fase o preparación de la sustentación.

## Requisitos

- Ejecutar desde la raíz del repositorio.
- `CONSTITUTION.md` debe existir; es la fuente de las reglas y fases.
- `git` debe estar disponible. `gh` es opcional: si falla, la bitácora marca el estado remoto como
  "sin verificar" en lugar de inventarlo.
- `uv` debe estar disponible para ejecutar pruebas y Ruff. Usa `--skip-checks` solo si el usuario pide una
  bitácora rápida.

## Flujo obligatorio

1. Ejecuta el generador:

   ```bash
   uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py
   ```

2. Lee la ruta impresa, por ejemplo `bitacora/2026-10-29.md`.
3. Verifica que el archivo exista y que la sección **Estado del repositorio** no contradiga la realidad. Si
   `gh` falló, no afirmes que el remoto está sincronizado.
4. Responde al usuario con un resumen de 6–8 líneas y la ruta del archivo. No repitas todo el documento.
5. No modifiques código, no hagas push y no borres bitácoras. Si el usuario pide guardar en Git, hazlo después
   de mostrar el resumen y con un mensaje Conventional Commits.
6. Si el generador falla, informa el error exacto y los comandos de diagnóstico; no inventes una bitácora.

## Reglas

- La bitácora es **append-only**: nunca sobrescribas un archivo existente. El script usa
  `YYYY-MM-DD.md` y, si ya existe, añade `-HHMM` o `-HHMMSS`.
- Toda cifra debe provenir del script o de un comando real. No estimes ni redondees a mano.
- Distingue siempre **local**, **remoto** y **sincronización**. Un commit local no es un commit publicado.
- Si el repositorio está sucio, indícalo; no ocultes cambios sin commit.
- La bitácora se escribe en español, con tono ejecutivo y secciones breves.
- La constitución canónica es `CONSTITUTION.md`; si falta o está desactualizada, repórtalo antes de generar.
- El script es de solo lectura sobre Git y el catálogo; la única escritura es el archivo de bitácora.

## Contenido esperado del archivo

1. Resumen ejecutivo (fase, avance, sincronización, corpus, prioridad).
2. Contexto de la constitución (versión, fecha, fase, reglas clave).
3. Estado del repositorio (rama, commit local/remoto, PRs, tags, sincronización).
4. Qué se ha hecho (commits desde la bitácora anterior y evidencia acumulada).
5. Avance por criterio (datos, LLM, app, documentación, repositorio, calidad).
6. Objetivos y metas cumplidos.
7. Pendientes y bloqueos priorizados.
8. **Cascada secuencial de tareas pendientes** (etapa, ID, dependencia, entregable, criterio de
   aceptación, responsable, tiempo y estado) más las **puertas de calidad** G1–G7.
9. Próximos pasos sugeridos (derivados de la cascada, en orden).
10. Riesgos y observaciones.
11. Evidencia de verificación.

## Cascada secuencial

La sección 8 no es una lista plana: es una cascada con dependencias y puertas. El generador la calcula
desde `CASCADE_STEPS` y `QUALITY_GATES` en `scripts/generate_bitacora.py`:

- Cada paso declara `id`, `stage`, `depends_on`, `deliverable`, `acceptance`, `checks`, `owner` y
  `estimate`.
- `checks` son las claves de la lista de verificación (por ejemplo `app`, `evaluation`, `tag`). El estado
  del paso se deriva de ellas:
  - **⛔ bloqueada**: alguna dependencia no está `done`.
  - **❌ pendiente**: dependencias cerradas pero un check está `pending`.
  - **🟡 parcial**: dependencias cerradas y al menos un check está `partial` o `unknown`.
  - **✅ completada**: todos los checks están `done`.
- El **camino crítico** se imprime como la secuencia de IDs; las tareas `done` se omiten de la tabla para
  que la bitácora muestre solo lo que falta.
- Las puertas `G1`–`G7` se evalúan sobre todos los pasos hasta su paso ancla: `✅` si todos están `done`,
  `⛔` si alguno está bloqueado y `❌` en otro caso.

### Cómo mantenerla

1. Si cambia el alcance del Módulo 1, edita `CASCADE_STEPS` y `QUALITY_GATES`; no escribas la tabla a mano.
2. Cada `TaskStep.checks` debe existir en la recolección de `Check`; si añades una clave nueva, agrega
   también su `Check` para que el estado no quede en `unknown`.
3. Respeta el orden lógico: un paso no puede depender de uno posterior ni de sí mismo.
4. No inventes estados: si un entregable no existe, el check debe ser `pending` o `partial` con evidencia.

## Diagnóstico

- `command not found: uv`: ejecutar `uv sync` y confirmar que `uv` está en el PATH.
- `gh` falla o no está autenticado: ejecutar `gh auth status`; la bitácora seguirá funcionando con Git local.
- `origin/main` no existe: confirmar `git remote -v` y `git fetch origin`.
- Bitácora duplicada: es intencional; cada llamada genera un archivo nuevo con la fecha y, si aplica, la hora.
- Para una prueba sin escribir: `--dry-run`. Para omitir pruebas/Ruff: `--skip-checks`. Para no consultar el
  remoto: `--no-fetch`.

## Archivos de la skill

- `scripts/generate_bitacora.py` — recolector y generador determinista.
- `SKILL.md` — este flujo.
