# ADR 0011 — Estandarización del repositorio y arquitectura viva

- **Estado**: aceptada
- **Fecha**: 2026-10-31
- **Autores**: Jason Alejandro Castaño
- **Contexto**: auditoría con `jan-project-standard`

## Contexto

El repositorio tenía una base funcional, pero la auditoría del estándar encontró faltantes de
gobernanza y documentación: `.editorconfig`, `Makefile`, `.pre-commit-config.yaml`, guía de
contribución, código de conducta, plantillas de PR e issues, Dependabot, labels e índice de
documentación. El README además conservaba estados obsoletos (app “pendiente”, datos “no
versionados”) y no incluía un diagrama de arquitectura interactivo.

La identidad del repositorio se verificó contra GitHub: cuenta `jasonCastano`, autor Jason
Alejandro Castaño, correo `jasonale3007@gmail.com` y remoto
`https://github.com/jasonCastano/proyecto_modelos_lenguaje.git`.

## Decisión

1. Adoptar el estándar `jan-project-standard` de forma **aditiva**, sin reemplazar README,
   constitución, licencia ni CI existentes.
2. Añadir `Makefile` como interfaz de comandos y `.pre-commit-config.yaml` para higiene, Ruff y
   `uv.lock`.
3. Incorporar gobernanza GitHub: plantilla de PR, formularios de issue, labels declarativas,
   Dependabot y workflow de sincronización de labels.
4. Documentar la contribución en `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` y `AGENTS.md`.
5. Generar `docs/arquitectura.json` y `docs/arquitectura.html` con **Archify** (tipo `dataflow`) y
   enlazar la captura desde el README.
6. Corregir la constitución: los datos de bronce, plata y oro se versionan por Git LFS; la
   cuarentena y los temporales no.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| Ejecutar el scaffolder con `--force` | Habría reemplazado README y constitución con plantillas. |
| Mantener solo `ruff check` | No verificaba formato ni higiene de archivos. |
| Diagrama Mermaid únicamente | No ofrece pan/zoom, búsqueda ni tema oscuro. |
| Commitear capturas de auditoría | Se generan localmente y no son documentación estable. |
| Añadir `ty` | El proyecto no lo usa; se mantiene el alcance simple. |

## Consecuencias

- `make check` y CI comparten lint, formato y pruebas.
- Los PR tienen checklist de constitución y pruebas.
- La arquitectura se regenera desde el JSON; el HTML no se edita a mano.
- El repositorio gana gobernanza sin cambiar el runtime de la app.
- El coste es una normalización de formato en archivos existentes y una imagen de ~134 KB.

## Validación

- `uv run pre-commit run --all-files`: OK.
- `make check`: 346 pruebas pasan, 9 omitidas.
- `archify finalize ... --quality showcase`: validate, deliver, check y browser-check en verde.
- `docs/arquitectura.visual-check.2048x1320.dark.png` generado y enlazado desde el README.
