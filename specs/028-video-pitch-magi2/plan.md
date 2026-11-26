# Implementation Plan: Video elevator pitch de Valer-IA generado con MAGI-2

**Branch**: `028-video-pitch-magi2` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/028-video-pitch-magi2/spec.md`

## Summary

Un video vertical de 57 s con formato de elevator pitch, generado con **MAGI-2 Preview** de Sand.ai. Se abre al
entrar a la web y explica qué es Valer-IA y cómo usarla.

Producción en tres etapas:

1. **Guion verificable**: `video/pitch/guion.toml`, con 6 bloques y sus fuentes del oro.
2. **Escenas I2V**: 6 clips de 10 s, generados una sola vez fuera de línea en una máquina alquilada de 8× H100.
   Parten de la imagen de referencia y de una indicación por escena, y se registran en `video/pitch/escenas.json`
   con revisión humana.
3. **Montaje**: ffmpeg une las escenas aprobadas recortadas a 9,5 s, añade la narración en español con la voz
   **Phonon** del proyecto y graba en el video el rótulo de IA y de proyecto académico. También genera los
   subtítulos WebVTT, la portada y la transcripción.

Un CLI `pml pitch` valida el guion, exporta las escenas para MAGI-2, narra, monta y comprueba el resultado.

En la web, un componente `PitchVideo` es el primer elemento de la entrada:

- arranca sin sonido y con subtítulos;
- se puede saltar en un paso;
- no se repite en la sesión;
- respeta el movimiento reducido;
- cae a portada y transcripción si el video falta.

El video viaja por Git LFS (research R6).

## Technical Context

**Language/Version**: Python 3.14 (CLI y validación, `uv`); TypeScript 5 + React 19 (web), Node 24. La generación
con MAGI-2 corre en su propio entorno (Docker oficial, Python 3.12 y CUDA) fuera del repositorio.

**Primary Dependencies**:

- **Generación** (fuera de línea): MAGI-2 Preview (Docker `sandai/magi-2-preview`, 8× H100 o H200).
- **Montaje**: ffmpeg (ya instalado; también lo usa la voz).
- **Narración**: voz Phonon del proyecto (spec 016).
- **Python y web**: sin dependencias nuevas.

**Storage**:

- `video/pitch/`: guion, manifiesto, transcripción y, por LFS, los clips aprobados y la narración.
- `web/public/media/`: video final y portada por LFS; subtítulos como texto.
- `docs/referencias/`: imagen y su ficha de origen.

**Testing**:

- pytest: validador del guion, manifiesto, exportación a `SAMPLES` y montaje con clips sintéticos generados por
  ffmpeg en la prueba.
- Vitest + Testing Library: `PitchVideo`.
- Playwright + axe-core: primera posición, saltar, sin desplazamiento de 360 a 1920 px, falta de video.

**Target Platform**: generación en Linux con 8 GPU Hopper (una vez). Montaje y web en Windows o Linux con ffmpeg.
Navegadores modernos de escritorio y teléfono.

**Project Type**: aplicación web (backend Python + SPA React) más un flujo de producción de medios.

**Performance Goals**:

- El video no bloquea la entrada: la portada aparece en menos de 1 s en local y el video carga con `preload="metadata"`.
- Archivo final ≤ 25 MB.
- JS de la web sigue ≤ 120 kB gzip.

**Constraints**:

- ≤ 60 s (FR-001).
- Narración y subtítulos en español.
- Sin logo de Manuelita.
- Rótulo de IA grabado en el video.
- Solo escenas aprobadas.
- La web funciona sin el video.
- La generación no corre en CI ni en la app.

**Scale/Scope**:

- 6 escenas y 1 video.
- 1 componente web nuevo y cambios en `Home`.
- 1 módulo Python (`pitch.py`) con su CLI.
- Unas 25 pruebas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §10: solo información pública, atribuida | ✅ | Guion con `unit_id` del oro y validador (R8). |
| §10: no presentarse como canal oficial de Manuelita | ✅ | Rótulo grabado en el video, portada y transcripción (R7). FR-010: sin logo y sin vocera. |
| §3.7: avatar original que no imita personas reales ni usa la marca | ⚠️ **Requiere confirmación** | La imagen de referencia es fotorrealista. La ficha de origen (R10) debe confirmar que es sintética y propia antes de generar; si no, se detiene la producción. |
| §10: uso de IA declarado; prompts no inventados | ✅ | Indicación, semilla y versión por escena (R9). Entrada en `docs/prompt_log.md`. |
| §3.7: entrada React servida por FastAPI; accesibilidad AA, `prefers-reduced-motion`, sin desplazamiento horizontal | ✅ | `PitchVideo` cumple FR-016 a FR-022. |
| Datos pesados por Git LFS | ✅ | `.mp4` y `.webp` del pitch por LFS (R6). |
| Tecnología nueva: actualizar la constitución en el mismo commit | ✅ | Enmienda **MINOR 2.3.0** (MAGI-2 como herramienta de producción fuera de línea y reglas del video), ADR 0032. Requiere la aprobación de jasonCastano. |
| Pruebas sin red ni claves | ✅ | Las pruebas usan clips sintéticos de ffmpeg. MAGI-2 y Phonon real quedan fuera (marcador `voice` para la voz real). |
| §4.3 autoría | ✅ | Commits a nombre de Robertto48. |

**Resultado**: pasa, con una condición previa (ficha de la imagen, R10) que la producción comprueba antes de correr.

**Re-check post-design**: sin desviaciones nuevas. El diseño mantiene la web independiente de MAGI-2 y añade solo
un componente y un módulo de producción. ✅

## Project Structure

### Documentation (this feature)

```text
specs/028-video-pitch-magi2/
├── spec.md
├── plan.md                 # este archivo
├── research.md             # R1–R10
├── data-model.md           # guion, escena, imagen de referencia, video
├── quickstart.md           # validación y runbook de producción
├── contracts/
│   ├── pitch-cli.md        # pml pitch validate|samples|narrate|assemble|check
│   ├── production-files.md # guion.toml, escenas.json, ficha de la imagen
│   └── web-ui.md           # PitchVideo en la entrada
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
video/pitch/                          # nuevo: producción del pitch
├── guion.toml                        # 6 bloques: texto narrado, claims [unit_id], tope de palabras
├── escenas.json                      # manifiesto: prompt, image, seed, model, revision, status, review
├── prompts/escena-0N.json            # caption estructurado de MAGI-2 por escena
├── escenas/escena-0N.mp4             # LFS: clips aprobados (salida de MAGI-2)
├── narracion/bloque-0N.wav           # LFS: voz Phonon por bloque
├── transcripcion.md                  # texto completo con la declaración
└── RUNBOOK.md                        # cómo generar en 8× H100 con la imagen Docker oficial

docs/referencias/
├── avatar_ingenio_manuelita.png      # LFS: imagen de referencia
└── avatar_ingenio_manuelita.md       # ficha de origen y derechos (R10)

src/proyecto_modelos_lenguaje/
├── pitch.py                          # nuevo: validar guion, exportar SAMPLES, narrar, montar (ffmpeg), comprobar
└── cli.py                            # subcomando `pml pitch …`

web/public/media/
├── pitch-valeria.mp4                 # LFS: video final 1080×1920, ≤ 60 s
├── pitch-valeria.webp                # LFS: portada con la declaración
└── pitch-valeria.es.vtt              # subtítulos

web/src/
├── components/home/PitchVideo.tsx    # nuevo: video, saltar, sesión, reducido, falla, CTA final
├── data/pitch.ts                     # nuevo: transcripción y rutas del video
├── pages/Home.tsx                    # PitchVideo como primer elemento
└── styles/platform.css               # estilos del bloque del pitch

tests/
├── unit/test_pitch.py                # guion, manifiesto, SAMPLES, duración, rótulo, ficha
├── integration/test_pitch_assemble.py  # montaje con clips sintéticos de ffmpeg
└── e2e/test_pitch.py                 # primera posición, saltar, sesión, falla, 360–1920 px
web/src/test/PitchVideo.test.tsx

.gitattributes                        # LFS para *.mp4, *.wav y *.webp del pitch y la imagen
docs/decisions/0032-video-pitch-magi2.md, CONSTITUTION.md (2.3.0), docs/prompt_log.md §3.24, README.md
```

**Structure Decision**:

- La producción vive en `video/pitch/` como datos versionados, igual que `data/synthetic/`.
- La lógica reproducible está en `pitch.py` con su CLI. La generación con MAGI-2 queda documentada en
  `RUNBOOK.md` y se alimenta de lo que exporta `pml pitch samples`.
- La web solo consume archivos estáticos de `web/public/media/`.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| No hay acceso a 8× H100 o H200 | Presupuestar una sesión de alquiler de unas 2 horas (6 escenas más regeneraciones). Sin GPU, la producción se detiene; la web y las pruebas no dependen del video. |
| La presentadora no se parece entre escenas | I2V con la misma imagen como primer cuadro en todas las escenas. La revisión humana descarta las que se desvían (FR-013). |
| MAGI-2 pone texto o cifras falsas en pantalla | El caption de cada escena pide «sin texto en pantalla». La revisión lo verifica y el texto real va en subtítulos y rótulos del montaje. |
| El guion supera 57 s al narrar | `pml pitch check` mide cada `.wav` y falla si un bloque supera 9,5 s. Se recorta el texto, no se acelera. |
| La imagen resulta ser de una persona real | La ficha de origen bloquea la producción (R10). |

## Complexity Tracking

> Sin violaciones de la constitución que justificar. El único punto condicionado (imagen de referencia) se resuelve
> con la ficha de origen antes de generar.
