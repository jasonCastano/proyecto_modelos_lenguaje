---
name: Bitácora del Proyecto
description: Genera una bitácora fechada del proyecto RAG Ingenio Manuelita con el contexto de CONSTITUTION.md, el estado local y remoto de Git, el avance por fase, los objetivos cumplidos, los pendientes y los próximos pasos. Úsala cuando el usuario pida "bitácora", "estado del proyecto", "avance", "qué falta" o "qué sigue".
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
8. Próximos pasos sugeridos.
9. Riesgos y observaciones.
10. Evidencia de verificación.

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
