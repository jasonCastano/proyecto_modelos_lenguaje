# Implementation Plan: Hablarle a Valer-IA Caña con la voz (dictado en la interfaz)

**Branch**: `023-voice-input` | **Date**: 2026-11-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-voice-input/spec.md`

## Summary

El visitante le habla a Valer-IA con el micrófono y su voz se convierte en texto en español en el **servidor del
proyecto**, sin terceros. La captura es PCM en el navegador, se envía como WAV de 16 kHz a `POST /api/stt` y se
transcribe con **faster-whisper `base` int8** más Silero VAD. El vocabulario de Manuelita se pasa como prompt inicial
y se aplican correcciones deterministas. El texto entra al chat como cualquier mensaje: el agente no distingue el
origen, así que todas las garantías de las specs 018–022 se mantienen.

1. **US1 (P1), dictar**:
   - botón de micrófono;
   - fin por silencio, manual o límite;
   - texto al campo, editable;
   - sin envío automático (R5–R7, R9).
2. **US2 (P1), estado y errores**:
   - indicador de grabación y nivel;
   - estados `GET /api/stt`;
   - mensajes por tipo de error;
   - degradación sin STT (R6, R13).
3. **US3 (P2), manos libres**:
   - envío al terminar;
   - reanudación tras la respuesta;
   - interrupción de la voz de Valer-IA;
   - cancelación y guarda de eco;
   - apagado por inactividad (R10).
4. **US4 (P3), traza y evaluación**:
   - `input` en `ChatRequest` y `TurnModel`;
   - línea «🎙 por voz» en la vista técnica;
   - `stt eval` con la batería sintetizada y grabaciones humanas opcionales (R9, R11).

En el banco inicial, `base` con vocabulario transcribe en 0.45 s, con WER 0.055 y vacío en silencio (R2).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript 5.9 y React 19 (frontend).

**Primary Dependencies**:
- `faster-whisper` 1.2.1 y `av`: pasan de la extra `asr` a runtime. Ya están en `uv.lock`, con ruedas `cp314`.
- CTranslate2 4.8.4 y `onnxruntime` (este ya era dependencia).
- En el navegador, Web Audio API (`getUserMedia`, `AudioWorklet`), sin librerías nuevas.

**Storage**:
- Nada en disco ni en `data/`.
- `TurnModel.input` en la entrada del turno del estado del hilo.
- Preferencia `manuelita.stt.handsfree` en `localStorage`.
- Modelo en la caché de Hugging Face.

**Testing**:
- pytest:
  - `stt/` (configuración, WAV, correcciones, `FakeTranscriber`, servicio y concurrencia);
  - API `/api/stt` (200, vacío, 400, 413, 415, 503 y ningún archivo creado);
  - `input` en el chat;
  - modelo real con marcador `voice`.
- Vitest: codificador WAV, detector de fin de habla, máquina de estados, guarda de eco, `MicButton` e integración
  con `ChatView` y la voz.
- Playwright (`make e2e`): audio falso de Chrome.
- Evaluación: `stt eval`.

**Target Platform**: servidor local o de despliegue con `uvicorn`, en CPU. Chrome, Edge y Firefox recientes por
`localhost` o HTTPS.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI de evaluación.

**Performance Goals**:
- Texto en menos de 2 s tras terminar de hablar, en el p90, para intervenciones de hasta 10 s (SC-003).
- Carga del modelo en caché menor de 3 s, con precalentamiento en segundo plano.

**Constraints**:
- WER ≤ 0.15 (SC-001).
- Vocabulario propio bien escrito ≥ 90 % (SC-002).
- 0 textos en silencio o ruido (SC-004).
- 0 ecos enviados (SC-005).
- 0 audios en disco (SC-006).
- Chat y voz intactos sin STT (SC-008).
- Pruebas sin red.

**Scale/Scope**:
- 1 subpaquete nuevo (`stt/`: config, engine, audio, text, log, eval y `__main__`).
- 2 endpoints y 1 campo de contrato (`input`).
- 1 archivo de configuración.
- 1 hook y 2 componentes web.
- Unas 40 frases de evaluación.
- Unas 35 pruebas nuevas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|---|---|---|
| I. Reproducibilidad | Configuración en `config/stt.toml`; versión del modelo y cuantización en el informe; batería generada con frases versionadas y semilla para los ruidos. | ✅ |
| II. Evaluación con línea base | `stt eval --models base small` compara modelos con métricas (WER, vocabulario, latencia, vacío); el banco de R2 incluye `large-v3-turbo` como referencia de calidad. | ✅ |
| III. Procedencia y ética de datos | Sin grabaciones de personas en el repositorio; las humanas son locales y opcionales (R3). | ✅ |
| IV. Experimentos versionados | `tests/fixtures/stt/phrases.jsonl` y el informe `docs/evaluacion_stt.*`. | ✅ |
| V. Simplicidad | Reutiliza `faster-whisper`, que ya usa el proyecto (extra `asr`), y el patrón de `voice/` (servicio, estado, precalentamiento, registro). WAV sin códec. Sin WebSocket. | ✅ |
| §3.1 (dependencias) | Promueve `faster-whisper` y `av` a runtime: es un cambio tecnológico, así que se actualiza la Constitución (v1.15.0) y el ADR 0027 en el mismo commit. | ✅ (con actualización) |
| §3.7 (aplicación web) | Micrófono en el chat; sin STT, el chat y la voz siguen igual. El registro del contacto no cambia. Se añade una viñeta. | ✅ (con actualización) |
| §3.8 (pruebas) | Motor `fake`; las pruebas del modelo real llevan el marcador `voice` y quedan fuera de CI. | ✅ |
| §3.9 (seguridad) | Límites de tamaño y duración, validación estricta del WAV, concurrencia acotada, errores sin detalles. | ✅ |
| §10 (privacidad) | El audio solo vive en memoria; no se registra texto ni audio; nota de privacidad junto al micrófono; el modelo corre local. | ✅ |
| §4.3 (autoría) | Commits del equipo; Claude prepara los cambios. | ✅ |

**Resultado**: PASS. Las enmiendas de §3.1, §3.7 y §10 y el ADR 0027 van en el commit de la funcionalidad.

**Re-check post-diseño (Phase 1)**: PASS.
- Contrato aditivo: dos endpoints nuevos; `input` opcional; `stt_available` en `health`.
- Los clientes actuales no cambian.
- `[stt] enabled = false` deja el sistema como en la spec 022.

## Project Structure

### Documentation (this feature)

```text
specs/023-voice-input/
├── plan.md, research.md (R1–R14), data-model.md, quickstart.md
├── contracts/stt-api.md     # GET/POST /api/stt, health, ChatRequest.input, CLI
├── contracts/ui.md          # micrófono, estados, mensajes, manos libres, traza
├── checklists/requirements.md
└── tasks.md                 # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/stt/          # NUEVO
├── __init__.py
├── config.py      # SttConfig, load_stt_config (TOML + MANUELITA_STT_*), validación
├── audio.py       # parse_wav16k (RIFF/PCM16/mono/16 kHz), límites, a float32
├── text.py        # initial_prompt del vocabulario, correcciones, recorte a 2000, filtro de ruido
├── engine.py      # Transcriber (Protocol), WhisperTranscriber, FakeTranscriber, SttService (estado,
│                  #   carga, precalentamiento, semáforo), get_stt_service
├── log.py         # log_stt: tiempos y tamaños, sin texto
├── eval.py        # batería sintetizada con Phonon, WER normalizado, vocabulario, latencias, informe
└── __main__.py    # --check, eval, transcribe
src/proyecto_modelos_lenguaje/transcription.py   # is_noise reutilizado (sin cambios de comportamiento)
src/proyecto_modelos_lenguaje/api.py             # GET/POST /api/stt; health.stt_available; precalentamiento
src/proyecto_modelos_lenguaje/api_models.py      # SttStatus, SttResult, InputMeta; ChatRequest.input, TurnModel.input
src/proyecto_modelos_lenguaje/agent/service.py   # pasa input a la entrada del turno y lo devuelve

config/stt.toml                                   # NUEVO
pyproject.toml / uv.lock                          # faster-whisper y av en runtime (la extra asr queda como alias)

web/src/
├── lib/dictation.ts        # NUEVO: encodeWav16k, EndpointDetector (RMS), echoSimilarity, tipos de error
├── lib/dictation-worklet.ts# NUEVO: AudioWorkletProcessor que publica bloques Float32
├── lib/useDictation.ts     # NUEVO: máquina de estados, normal y manos libres, integración con useVoice
├── lib/api.ts, lib/types.ts# getSttStatus, transcribe, InputMeta, TurnModel.input
├── components/MicButton.tsx# NUEVO: botón, nivel, estado, cancelar, manos libres, privacidad
├── components/ChatView.tsx # MicButton en el formulario; envío con input; línea 🎙 en turn-trace
└── test/dictation.test.ts, MicButton.test.tsx, ChatViewDictation.test.tsx

tests/
├── unit/stt/test_config.py, test_audio.py, test_text.py, test_engine.py
├── api/test_stt_api.py, test_chat_input.py
├── integration/stt/test_whisper_real.py      # marcador voice
├── e2e/test_dictation.py                      # Playwright con audio falso (PML_E2E=1)
└── fixtures/stt/phrases.jsonl

docs/
├── decisions/0027-dictado-local.md
├── evaluacion_stt.md / .json
├── README.md, demo.md (sección micrófono)
CONSTITUTION.md (v1.15.0: §3.1, §3.7, §10)
```

**Structure Decision**:
- `stt/` replica el diseño probado de `voice/` (configuración por TOML con variables, servicio con estados y
  precalentamiento, registro sin contenido, CLI `--check`), para que el equipo lo reconozca.
- El chat no cambia de flujo: la voz es otra forma de llenar el campo del mensaje. Lo nuevo en el contrato del chat
  es solo el metadato `input`.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
