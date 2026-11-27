# Implementation Plan: Video elevator pitch de Valer-IA generado con MAGI-2

**Branch**: `028-video-pitch-magi2` | **Date**: 2026-11-25, revisado 2026-11-26 (API de Higgsfield) |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/028-video-pitch-magi2/spec.md`

## Summary

Un video vertical de 57 s con formato de elevator pitch, generado con **MAGI-2** de Sand.ai a través de la **API de
Higgsfield**. Se abre al entrar a la web y explica qué es Valer-IA y cómo usarla.

Producción en tres etapas:

1. **Guion verificable**: `video/pitch/guion.toml`, con 6 bloques y sus fuentes del oro.
2. **Escenas I2V**: 6 clips de 10 s generados una sola vez con `pml pitch generate`, que llama a
   `sand/magi-2/image-to-video` en Higgsfield desde el equipo del integrante (research R11–R14):
   - la imagen de referencia, normalizada a 1080×1920, es el primer cuadro de cada escena; así sale vertical;
   - autentica con `Authorization: Key <id>:<secreto>`, tomado de `HIGGSFIELD_API_KEY` en `.env`;
   - una calibración de 4 s, de unos 0,32 USD, confirma los nombres de los campos de duración y audio antes de
     gastar en las 6 escenas;
   - cada escena registra en `video/pitch/escenas.json` el trabajo, su costo y la revisión humana;
   - las 8× H100 con los pesos abiertos quedan como alternativa (`pml pitch samples` y el RUNBOOK).
3. **Montaje**: ffmpeg une las escenas aprobadas recortadas a 9,5 s, añade la narración en español con la voz
   **Phonon** del proyecto. También genera los subtítulos WebVTT, la portada y la transcripción. El video no lleva
   rótulo grabado; la declaración de IA va como texto junto al video en la web (R7, revisión 2026-11-26).

Un CLI `pml pitch` valida el guion, genera las escenas por la API (o las exporta para los pesos abiertos), narra,
monta y comprueba el resultado.

En la web, un componente `PitchVideo` es el primer elemento de la entrada:

- arranca sin sonido y con subtítulos;
- se puede saltar en un paso;
- no se repite en la sesión;
- respeta el movimiento reducido;
- cae a portada y transcripción si el video falta.

El video viaja por Git LFS (research R6).

## Technical Context

**Language/Version**: Python 3.14 (CLI y validación, `uv`); TypeScript 5 + React 19 (web), Node 24.

**Primary Dependencies**:

- **Generación** (una vez, desde el equipo del integrante): API de Higgsfield, modelo `sand/magi-2/image-to-video`.
  - **Cliente**: `httpx`, que ya es dependencia; sin el SDK `higgsfield-client` (R12).
  - **Campos confirmados**: `image_url`, `prompt`, `resolution: "1080p"` y `seed`.
  - **Duración y audio**: van en `config/pitch.toml` y se confirman con la calibración (R11).
  - **Imagen**: se sube por `POST /files/generate-upload-url` y se pasa como `public_url` (R13).
  - **Trabajo**: asíncrono. Se envía con `Idempotency-Key`, se consulta `status_url` cada 10 s y se descarga
    `video.url` (R14).
  - **Alternativa**: los pesos abiertos MAGI-2 Preview en Docker `sandai/magi-2-preview` con 8× H100.
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
- pytest con `httpx.MockTransport`: el cliente de Higgsfield sin red. Cubre subida, envío, estados, descarga,
  errores 401/403/429/`failed`/`nsfw`, tope de gasto, `--dry-run`, que no se regeneren escenas aprobadas y que la
  clave no aparezca en la salida (SC-009).
- Vitest + Testing Library: `PitchVideo`.
- Playwright + axe-core: primera posición, saltar, sin desplazamiento de 360 a 1920 px, falta de video.

**Target Platform**: generación por la API de Higgsfield, lanzada desde Windows o Linux con red (una vez). Montaje
y web en Windows o Linux con ffmpeg. Navegadores modernos de escritorio y teléfono.

**Project Type**: aplicación web (backend Python + SPA React) más un flujo de producción de medios.

**Performance Goals**:

- El video no bloquea la entrada: la portada aparece en menos de 1 s en local y el video carga con `preload="metadata"`.
- Archivo final ≤ 25 MB.
- JS de la web sigue ≤ 120 kB gzip.

**Constraints**:

- ≤ 60 s (FR-001).
- Narración y subtítulos en español.
- Sin logo de Manuelita.
- Declaración de IA visible junto al video y en la transcripción, no grabada.
- Solo escenas aprobadas.
- La web funciona sin el video.
- La generación no corre en CI ni en la app (FR-028).
- La clave solo se lee de `.env`; nunca se escribe en archivos, registros ni salida (FR-026).
- Gasto ≤ 20 USD con tope configurable, `--dry-run` y confirmación previa (FR-027, SC-008).
- Generación en serie: una solicitud a la vez.

**Scale/Scope**:

- 6 escenas y 1 video.
- 1 componente web nuevo y cambios en `Home`.
- 1 módulo Python (`pitch.py`) con su CLI, más el cliente `pitch_higgsfield.py`.
- Unas 25 pruebas, más unas 15 del cliente de Higgsfield.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §10: solo información pública, atribuida | ✅ | Guion con `unit_id` del oro y validador (R8). |
| §10: no presentarse como canal oficial de Manuelita | ✅ | Declaración visible junto al video y en la transcripción (R7). El video solo se publica en la web. FR-010: sin logo y sin vocera. |
| §3.7: avatar original que no imita personas reales ni usa la marca | ✅ | Ficha de origen confirmada el 2026-11-26: generada con IA, con derechos de uso, sin persona real ni marca (R10). `generate` también se niega a correr sin ella. |
| §10 y secretos: claves solo en `.env`, sin datos a terceros sin necesidad | ✅ | `HIGGSFIELD_API_KEY` solo en `.env`, redactada en errores (R12). A Higgsfield se suben solo la imagen sintética y los prompts de escena (R14). |
| §10: uso de IA declarado; prompts no inventados | ✅ | Indicación, semilla y versión por escena (R9). Entrada en `docs/prompt_log.md`. |
| §3.7: entrada React servida por FastAPI; accesibilidad AA, `prefers-reduced-motion`, sin desplazamiento horizontal | ✅ | `PitchVideo` cumple FR-016 a FR-022. |
| Datos pesados por Git LFS | ✅ | `.mp4` y `.webp` del pitch por LFS (R6). |
| Tecnología nueva: actualizar la constitución en el mismo commit | ✅ | La enmienda **2.3.0** (aún sin fusionar) se ajusta: MAGI-2 por la API de Higgsfield como herramienta de producción, con la clave en `.env`. El ADR 0032 se revisa. Requiere la aprobación de jasonCastano. |
| Pruebas sin red ni claves | ✅ | Clips sintéticos de ffmpeg y `httpx.MockTransport` para Higgsfield. La API real y Phonon real quedan fuera (marcadores `network` y `voice`). |
| §4.3 autoría | ✅ | Commits a nombre de Robertto48. |

**Resultado**: pasa. La condición previa (ficha de la imagen, R10) quedó cumplida el 2026-11-26.

**Re-check post-design (revisión Higgsfield)**: sin desviaciones. La web sigue sin depender de MAGI-2 ni de
Higgsfield. La única llamada de red nueva es un comando manual con tope de gasto, cubierto por pruebas sin red. ✅

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
│   ├── pitch-cli.md        # pml pitch validate|generate|samples|narrate|assemble|check
│   ├── production-files.md # guion.toml, escenas.json, ficha de la imagen
│   └── web-ui.md           # PitchVideo en la entrada
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
video/pitch/                          # nuevo: producción del pitch
├── guion.toml                        # 6 bloques: texto narrado, claims [unit_id], tope de palabras
├── escenas.json                      # manifiesto: prompt, image, seed, model, job (Higgsfield), status, review
├── calibracion/                      # clip de 4 s de la calibración (no va al montaje; ignorado por git)
├── prompts/escena-0N.json            # caption estructurado de MAGI-2 por escena
├── escenas/escena-0N.mp4             # LFS: clips aprobados (salida de MAGI-2)
├── narracion/bloque-0N.wav           # LFS: voz Phonon por bloque
├── transcripcion.md                  # texto completo con la declaración
└── RUNBOOK.md                        # Higgsfield paso a paso; 8× H100 como alternativa

config/pitch.toml                     # nuevo: modelo, URL base, campos, segundos, usd_per_second, max_usd, esperas
.env.example                          # HIGGSFIELD_API_KEY= (formato id:secreto), sin valor

docs/referencias/
├── avatar_ingenio_manuelita.png      # LFS: imagen de referencia
└── avatar_ingenio_manuelita.md       # ficha de origen y derechos (R10)

src/proyecto_modelos_lenguaje/
├── pitch.py                          # nuevo: validar guion, exportar SAMPLES, narrar, montar (ffmpeg), comprobar
├── pitch_higgsfield.py               # nuevo: cliente httpx (subir, enviar, consultar, descargar), costo, redacción
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
├── unit/test_pitch.py                # guion, manifiesto, SAMPLES, duración, ficha
├── unit/test_pitch_generate.py       # cliente Higgsfield con MockTransport, gasto, dry-run, redacción de la clave
├── integration/test_pitch_assemble.py  # montaje con clips sintéticos de ffmpeg
└── e2e/test_pitch.py                 # primera posición, saltar, sesión, falla, 360–1920 px
web/src/test/PitchVideo.test.tsx

.gitattributes                        # LFS para *.mp4, *.wav y *.webp del pitch y la imagen
docs/decisions/0032-video-pitch-magi2.md, CONSTITUTION.md (2.3.0), docs/prompt_log.md §3.24, README.md
```

**Structure Decision**:

- La producción vive en `video/pitch/` como datos versionados, igual que `data/synthetic/`.
- La lógica reproducible está en `pitch.py` con su CLI.
- El acceso a Higgsfield va aparte, en `pitch_higgsfield.py`, para poder simularlo en pruebas y para que la clave no
  cruce otros módulos. `pml pitch samples` y el RUNBOOK conservan la vía de los pesos abiertos.
- La web solo consume archivos estáticos de `web/public/media/`.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Los nombres de los campos de duración o audio no son los supuestos (la API ignora campos desconocidos) | Calibración de 4 s antes de las 6 escenas; ffprobe verifica duración y audio. Los nombres se corrigen en `config/pitch.toml` (R11). |
| Higgsfield cambia el modelo, el precio o el esquema | Modelo y precio en `config/pitch.toml`. El comando valida contra `GET /models` que el modelo existe antes de cobrar. |
| Gasto fuera de control por reintentos | `Idempotency-Key` por escena, tope `max_usd`, confirmación previa, sin regenerar escenas aprobadas sin `--force` (R14). |
| Saldo insuficiente (403) o cola llena (429) | 403 detiene con un mensaje y no toca el manifiesto. 429 espera `Retry-After`. La escena queda `error` y se reintenta sola (R12). |
| La clave se filtra en una traza | Cliente propio con redacción en todo error y prueba de búsqueda de la clave (SC-009). |
| Higgsfield no disponible | Alternativa documentada con los pesos abiertos en 8× H100 (`pml pitch samples`, RUNBOOK). La web no depende del video. |
| La presentadora no se parece entre escenas | I2V con la misma imagen como primer cuadro en todas las escenas. La revisión humana descarta las que se desvían (FR-013). |
| MAGI-2 pone texto o cifras falsas en pantalla | El caption de cada escena pide «sin texto en pantalla». La revisión lo verifica y el texto real va en subtítulos y rótulos del montaje. |
| El guion supera 57 s al narrar | `pml pitch check` mide cada `.wav` y falla si un bloque supera 9,5 s. Se recorta el texto, no se acelera. |
| La imagen resulta ser de una persona real | La ficha de origen bloquea la producción (R10). Está confirmada desde el 2026-11-26. |

## Complexity Tracking

> Sin violaciones de la constitución que justificar. El único punto condicionado (imagen de referencia) se resuelve
> con la ficha de origen antes de generar.
