# Implementation Plan: Frontend profesional de Valer-IA, plataforma de agentes de Manuelita

**Branch**: `031-frontend-profesional-valeria` | **Date**: 2026-11-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/031-frontend-profesional-valeria/spec.md`

Tipo: **software** (plataforma de agentes de IA).
Reparto: hero `split` con el video pitch como visual · nav `nav-centre` · pie `footer-statement` · cierre
`close-type` · ritmo `dark-band` · botones `solid` · marca `wordmark` · un momento `letters-assemble` · paleta de
marca con los colores del logotipo (verde `#497536` para acciones, rojo anaranjado `#d64729`, naranja `#f39200` y
amarillo `#ffd100` en filetes y hojas) porque son los colores corporativos que pidió el integrante y ya identifican
las imágenes de la spec 030.

## Summary

Rediseño de las cuatro áreas de la web con la skill `design-taste-frontend`:

- **Entrada**: pasa de tablero técnico a sitio de producto, una sección por pantalla (research R6). El video pitch es
  el visual del hero, así que sigue siendo el primer elemento.
- **Agente, planificación y evidencia**: heredan el mismo sistema (tokens, tipo, botones, tarjetas, nav, pie, capa
  de hover y foco) sin perder ninguna capacidad.
- **Imágenes**: ilustraciones y glifos propios, la presentadora sintética y fotos sustitutas con licencia libre de
  Wikimedia Commons, citadas en el pie.
- **Inspiración**: la estructura y el tono de manuelita.com, sin su marca.
- **Implementación**: el kit de la skill no tiene licencia, así que sus reglas se reimplementan en el CSS y los
  componentes del proyecto; sus scripts (gate, copy-lint, fotos, capturas) se usan como herramientas externas.

## Technical Context

**Language/Version**: TypeScript 5.9, React 19, Vite 7; CSS propio (`web/src/styles/`)
**Primary Dependencies**: las actuales (`@fontsource-variable/archivo`, React). Sin dependencias nuevas de npm. Se
retiran `@fontsource-variable/bricolage-grotesque` y `public-sans` si ya no se usan.
**Storage**: fotos WebP en `web/public/media/fotos/` por Git LFS, con `CREDITOS.md`; datos de presentación en
`web/src/data/`.
**Testing**: Vitest + Testing Library (componentes), Playwright e2e (`tests/e2e`: plataforma, responsive, axe,
video pitch), gate de la skill sobre la entrada.
**Target Platform**: navegadores de escritorio y móvil, de 320 a 1920 px; servida por FastAPI (`make app`).
**Project Type**: web (SPA) sobre la API existente; la API no cambia.
**Performance Goals**: contenido principal de la entrada < 2,5 s en local (SC-004); fotos ≤ 200 KB a 1600 px; sin
desplazamiento de diseño (CLS < 0,1).
**Constraints**:
- AA en todo texto;
- sin scroll horizontal;
- reducir movimiento;
- sin logotipo de Manuelita;
- cifras solo del optimizador;
- declaración de IA junto al video y en el pie.

**Scale/Scope**: 4 rutas, unos 70 componentes TSX y 3 hojas de estilo (~3.900 líneas de CSS), 23 archivos de prueba
de Vitest y 9 de e2e.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla | Estado |
|---|---|
| §3.7 Aplicación web: cuatro áreas, video pitch primero y saltable, perfiles libres en la web, cifras del optimizador | ✅ Se conservan (FR-001, contrato). El video pasa a ser el visual del hero |
| §3.7 Identidad: una familia (Archivo), color fijo por producto, pictogramas propios, AA, 360–1920 sin scroll | ✅ Archivo se mantiene frente al reparto de la skill (R4). Se amplían colores y fotos: enmienda 2.6.0 |
| §10 Video con IA: declaración visible junto al video; sin la marca de Manuelita | ✅ Línea de aviso del hero y pie |
| §10 Todo recurso externo con fuente y licencia | ✅ Fotos con autor y licencia (R5). El kit sin licencia no se copia (R2) |
| No escribir en `data/` ni en el repo desde la app | ✅ Solo cambia la presentación |
| `make check` y `make e2e` en verde | ✅ Pruebas ajustadas en cada commit |
| Autoría (§4.3) | ✅ Commits como Robertto48, sin coautores |

**Post-diseño**: sin violaciones. Las desviaciones de la skill (fuente, kit, áreas fuera del gate) están
justificadas en research y quedan como exenciones con su motivo.

## Project Structure

### Documentation (this feature)

```text
specs/031-frontend-profesional-valeria/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/ui-contract.md
├── checklists/requirements.md
└── tasks.md                     # /speckit-tasks
```

### Source Code (repository root)

```text
web/
├── index.html                   # lang, data-type, metas, theme-color
├── public/media/fotos/          # WebP sustitutos (LFS) + CREDITOS.md
└── src/
    ├── styles/tokens.css        # paleta de marca (R3), escala, radios, alturas por pantalla
    ├── styles/global.css        # tipo Archivo, botones solid, tarjetas, foco, hover, reduce motion
    ├── styles/platform.css      # áreas de aplicación
    ├── data/products.ts         # productos con color y glifo (data-model)
    ├── data/photos.ts           # fotos con autor y licencia
    ├── components/shell/        # NavCentre, FooterStatement, AppShell
    ├── components/home/         # Hero (split + PitchVideo), AppFrame, ProfilesBento, Businesses,
    │                            # Statement (letters-assemble), PlanningBand (diagrama con pulsos),
    │                            # Guarantees, EvidenceTools, Faq, CloseType
    ├── components/brand/        # ProductGlyphs (+ palma, uva, mejillón si falta alguno)
    └── pages/                   # Home, Agent, Planning, Evidence
tests/e2e/                       # ajustes de textos y estructura
.gitignore                       # .taste-skill/
CONSTITUTION.md                  # 2.6.0
docs/decisions/0035-frontend-profesional.md
```

**Structure Decision**: se reescriben la entrada y la carcasa, y se reestilizan las tres áreas de aplicación
dentro de la SPA existente, sin cambiar rutas ni API. Así se protegen las pruebas de comportamiento, y los
cambios de texto se ajustan en el mismo commit.

## Complexity Tracking

| Desviación de la skill | Por qué | Alternativa descartada |
|---|---|---|
| Archivo en lugar de Mona Sans + Geist Mono | Constitución §3.7 y continuidad con las imágenes de la spec 030; se sirve sin red | Cambiar de familia: rompe la identidad aprobada y depende de Google Fonts |
| Kit no copiado; reglas reimplementadas | El kit no tiene licencia y el repo es MIT público | Copiar `system.css`/`system.js`: riesgo de licencia |
| Agente, planificación y evidencia fuera del gate | Son pantallas de trabajo; la regla de una sección por pantalla no aplica | Forzar el gate: deformaría las herramientas |
| Un solo momento | FR-010 y la página de 10 secciones | Dos momentos: más movimiento sin ganar comprensión |
