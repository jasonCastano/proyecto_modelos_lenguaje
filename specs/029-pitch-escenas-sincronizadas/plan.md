# Implementation Plan: Pitch v2 con escenas sincronizadas a la narración

**Branch**: `029-pitch-escenas-sincronizadas` | **Date**: 2026-11-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/029-pitch-escenas-sincronizadas/spec.md`

## Summary

La versión 2 del pitch cambia la producción de la 028 en tres puntos:

1. **Planos**: cada escena pasa de un clip a uno o más planos.
2. **Sincronía**: lo que se ve sigue a la narración.
3. **Duración**: cada escena dura su narración más una pausa.

El enfoque técnico:

- **Momentos sincronizados en el guion**: palabra → qué se ve.
- **Tiempos de cada palabra**: salen de la narración ya sintetizada, con el reconocedor local del proyecto
  (faster-whisper con tiempos por palabra; sin red).
- **Iconos y vista de perfiles**: gráficos propios (SVG → PNG transparente) que el montaje superpone y anima en el
  instante de cada palabra.
- **Eventos de los planos generados** (la presentadora entra, las personas llegan): se anotan en la revisión con su
  segundo dentro del clip. El montaje ajusta la velocidad del plano, entre 0,8× y 1,25×, para que caigan sobre su
  palabra.
- **Proveedor**: el modelo queda en `config/pitch.toml`. MAGI-2 por Higgsfield es la vía principal, a 0,08 USD/s.
  Desde el 2026-11-26 por la tarde, la API responde `403 model_unavailable` (research R1). Antes de gastar, un
  sondeo sin costo decide. Si MAGI-2 sigue sin estar disponible, el integrante elige la alternativa: Kling 4.0 a
  1080p es la recomendada.
- **Publicación sin perder la v1**: la v2 se monta como borrador fuera de `web/`. Solo `pml pitch publish` la copia
  a la web, después de aprobarla y validarla.

## Technical Context

**Language/Version**: Python ≥ 3.14 (uv); TypeScript/React 19 solo para regenerar `web/src/data/pitch.ts`
**Primary Dependencies**:
- ya presentes: ffmpeg/ffprobe, httpx, voz Phonon (spec 016), faster-whisper (spec 023), Playwright (grupo dev,
  para rasterizar los gráficos);
- sin dependencias nuevas.

**Storage**: archivos versionados
- texto: `video/pitch/guion.toml`, `escenas.json` (esquema v2), `sincronia.json`, `prompts/plano-*.json`,
  `graficos/*.svg`;
- por LFS: los clips `.mp4`, la narración `.wav` y los PNG de los gráficos;
- borrador en `video/pitch/borrador/`, ignorado por Git.

**Testing**: pytest
- clips sintéticos de ffmpeg;
- `httpx.MockTransport` para Higgsfield;
- tiempos de palabras inyectados con un alineador falso.

El reconocedor real queda con el marcador `voice`, y la API real con `network`.
**Target Platform**: equipo del integrante (Windows/Linux) para producir; la web no cambia.
**Project Type**: CLI de producción fuera de línea + recurso estático de la web.
**Performance Goals**:
- alinear las 6 narraciones en menos de 1 min en CPU;
- montar en menos de 5 min.

**Constraints**:
- video de 60 s o menos;
- sincronía de ±0,5 s;
- pausas de 0,3 a 0,8 s;
- gasto total de 20 USD o menos (quedan 14,56);
- 1080×1920 y 25 MB o menos;
- sin texto generado, salvo los gráficos del montaje.

**Scale/Scope**:
- 6 escenas y 8 planos;
- unos 57 s generados;
- 14 momentos sincronizados (6 iconos, 5 aliados, 3 de la oficina) más la entrada de la escena 01 y la vista de
  perfiles.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla | Estado | Nota |
|---|---|---|
| Principio I (reproducibilidad) | ✅ | Cada plano registra modelo, indicación, semilla y trabajo. Los tiempos de palabras se guardan en `sincronia.json`, y el montaje es determinista a partir de esos archivos. |
| Principio III y §10 (procedencia, marca) | ✅ | Las afirmaciones sobre Manuelita salen del oro. La oficina es genérica, sin logotipos ni letreros (FR-014). Los gráficos son propios, sin marca Manuelita. Las cinco personas son sintéticas. |
| §10 (declaración de IA) | ✅ | Sin cambios: la declaración es texto de la web junto al video. |
| §3.7 (avatar original) | ✅ | La ficha de la imagen de la 028 sigue vigente. Las personas nuevas se describen sin parecido con personas reales. |
| Principio V (simplicidad) | ✅ | Se reutilizan ffmpeg, faster-whisper y Playwright; no hay dependencias nuevas. |
| Secretos | ✅ | La clave sigue solo en `.env`. Si se cambia de modelo, se usa la misma clave de Higgsfield. |
| Pruebas sin red | ✅ | Alineador falso, transporte simulado y clips sintéticos. |
| Tecnología nueva → constitución en el mismo commit | ⚠️ condicional | Con MAGI-2 basta el ADR 0033, que trata la composición en planos y la sincronía. Si se usa otro modelo, la regla §3.7 y §10 que nombra MAGI-2 se enmienda (2.4.0) en el mismo commit. Requiere la aprobación de jasonCastano. |
| §4.3 autoría | ✅ | Commits a nombre de Robertto48. |

**Resultado**: pasa, con la condición registrada en Complexity Tracking.

**Re-check post-design**: sin desviaciones nuevas. La web no cambia de código, solo de recurso y datos, y la v1
sigue publicada hasta `publish`. ✅

## Project Structure

### Documentation (this feature)

```text
specs/029-pitch-escenas-sincronizadas/
├── spec.md
├── plan.md              # este archivo
├── research.md          # R1–R10
├── data-model.md        # guion v1.2.0, escenas.json v2, sincronia.json, gráficos
├── quickstart.md        # validación sin red, producción y mediciones
├── contracts/
│   ├── pitch-cli.md     # comandos nuevos y cambiados
│   └── production-files.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
config/pitch.toml                       # [models.*] por proveedor, pausa, límites de reajuste
src/proyecto_modelos_lenguaje/
├── pitch.py                            # carga v2, narrate sin tope fijo, assemble por planos, publish
├── pitch_sync.py                       # NUEVO: align (palabras→tiempos), línea de tiempo, reajuste de planos
├── pitch_graphics.py                   # NUEVO: SVG→PNG con Playwright y filtros overlay de ffmpeg
├── pitch_higgsfield.py                 # modelos por modo (image/reference/text), sondeo sin costo
└── cli.py                              # pml pitch align | graphics | probe | publish; generate --shot
video/pitch/
├── guion.toml                          # 1.2.0 con [[block.cue]]
├── escenas.json                        # esquema v2: escenas → planos
├── sincronia.json                      # NUEVO: tiempos por palabra y por momento
├── prompts/plano-01a.json …            # NUEVO: un caption por plano
├── graficos/*.svg (+ png/ por LFS)     # NUEVO: iconos y tarjetas de perfil
├── planos/plano-01a.mp4 …              # NUEVO (LFS)
└── borrador/                           # ignorado: montaje v2 antes de publicar
tests/
├── unit/test_pitch_sync.py             # NUEVO
├── unit/test_pitch_graphics.py         # NUEVO
├── unit/test_pitch.py, test_pitch_generate.py   # esquema v2, multi-modelo
└── integration/test_pitch_assemble.py  # montaje por planos, overlays, pausas, publish
docs/decisions/0033-pitch-v2-sincronia.md
```

**Structure Decision**: proyecto único. La sincronía y los gráficos van en módulos nuevos para no hacer crecer
`pitch.py`, que ya tiene unas 1.050 líneas. La web solo recibe el nuevo `.mp4`, `.vtt`, `.webp` y `pitch.ts`.

## Plan de planos (borrador; se fija en `escenas.json`)

| Escena | Narración est. + pausa | Planos | Modo | Segundos pedidos |
|---|---|---|---|---|
| 01 gancho | 7,8 + 0,5 | 01a trapiche tradicional funcionando en un cañaduzal, sin personas | texto | 5 |
| | | 01b la presentadora sale de la caña por la derecha, levanta la vista y sonríe; acercamiento lento | referencia | 6 |
| 02 problema | 7,9 + 0,5 | 02 la presentadora mira la tablet pensativa, sin paneles (iconos en el montaje) | imagen (referencia) | 9 |
| 03 solucion | ~12,6 + 0,5 | 03a la presentadora al centro; entran tres personas por la izquierda y dos por la derecha y se ubican a su lado | referencia | 10 |
| | | 03b gira la tablet hacia la cámara; primer plano de su cara | imagen (último cuadro de 03a) | 5 |
| 04 diferencia | 5,1 + 0,5 | 04 oficina ejecutiva genérica; redacta un informe y al final mira a la cámara y asiente (iconos de citar, calcular y confirmar en el montaje) | referencia | 6 |
| 05 uso | 7,1 + 0,5 | 05 camina entre la caña y explica con la mano, sin paneles (tarjetas de perfil en el montaje) | imagen (referencia) | 8 |
| 06 accion | 6,8 + 0,5 | 06 las cinco personas a los lados se despiden con la mano; la presentadora invita; la cámara se aleja | imagen (último cuadro de 03a) | 8 |
| **Total** | **~50,3 s** | **8 planos** | | **57 s** |

Costo estimado de los 57 s, sin regeneraciones:

| Modelo | Costo |
|---|---|
| MAGI-2 | 4,56 USD |
| Kling 4.0 1080p | unos 10,70 USD |
| Calibración de modos nuevos (2 × 4 s) | de 0,64 a 1,50 USD |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Posible cambio de modelo (enmienda 2.4.0) | MAGI-2 responde `403 model_unavailable` en la API desde el 2026-11-26 | Esperar sin alternativa puede dejar la v2 bloqueada sin fecha. El cambio solo se aplica si el sondeo falla y el integrante lo confirma. |
| Reajuste de velocidad de los planos (0,8×–1,25×) | Los modelos no garantizan el segundo exacto de un evento dentro del clip | Pedir un plano por cada evento costaría unos 14 planos más (de 4 a 9 USD extra) y cortaría el movimiento continuo |
