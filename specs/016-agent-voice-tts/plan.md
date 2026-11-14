# Implementation Plan: Voz del agente en español con síntesis natural (Phonon)

**Branch**: `016-agent-voice-tts` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-agent-voice-tts/spec.md`

## Summary

El chat del agente responde hoy solo por texto, en streaming SSE (`/api/chat/stream`). Esta feature le da voz
femenina en español con el motor local **Phonon** (`ptts`, modelo `gradium/phonon-40m-es`):

1. **US1 (P1)**: el navegador corta en oraciones el texto que llega por streaming y pide cada oración a un endpoint
   nuevo, `POST /api/tts`, que la limpia (citas, Markdown, marcas internas) y la sintetiza en el servidor como WAV.
   Una cola de reproducción con Web Audio las encadena en orden mientras la respuesta se sigue generando. Al
   terminar el turno, si la respuesta final validada difiere del streaming, la voz se corrige y lee la final.
2. **US2 (P2)**: controles en el chat: silenciar/activar (persistido en el navegador), detener y «Escuchar» por
   respuesta; una nueva pregunta corta la lectura anterior.
3. **US3 (P3)**: el motor se carga perezosamente con estado explícito; si no está disponible, `/api/tts` responde
   `503`, `GET /api/voice` y `/api/health` lo informan y la UI deshabilita la voz sin afectar el chat.

Decisiones en [research.md](./research.md) R1–R9.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5.9 + React 19 (frontend)

**Primary Dependencies**:
- **Nueva**: `ptts` (≥ 0.7.1, enlace Python del runtime Rust de Phonon; MIT/Apache-2.0; sin PyTorch; depende solo
  de `numpy`).
- Existentes: FastAPI, Pydantic, la librería estándar `wave`; Web Audio API del navegador (sin dependencias npm
  nuevas).

**Storage**:
- Modelo de voz (~75 MB, q8) en la caché de Hugging Face del usuario, fuera del repositorio.
- Configuración en `config/voice.toml` (versionada).
- Registro `logs/voice.jsonl` en `MANUELITA_STATE_DIR` (sin audio ni texto completo).
- Preferencia de silencio en `localStorage` del navegador.

**Testing**:
- pytest: limpieza de texto, sintetizador simulado, codificación WAV, estado de disponibilidad, contrato de
  `/api/tts` y `/api/voice`, CLI `voice --check`; prueba con el modelo real marcada `@pytest.mark.voice`, excluida
  por defecto.
- Vitest: segmentador incremental, cola de reproducción (fetch y `AudioContext` simulados), controles y la
  integración con `ChatView`.

**Target Platform**: servidor local Windows/Linux/macOS (x86-64 con AVX2 o ARM64) con `make app`; navegador moderno
con Web Audio.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI auxiliar.

**Performance Goals**:
- Primera oración audible < 1,5 s después de que se cierra en pantalla (SC-001). El proveedor reporta ~20× tiempo
  real; en el i9-12900H se midió ~6× (~12 ms por carácter), por lo que el primer segmento se limita a 120
  caracteres (research R10). Medido: 10/10 < 1,5 s, mediana 0,67 s.
- Detener/silenciar < 0,5 s (SC-005).

**Constraints**:
- Sin red ni descarga del modelo en `make check`/CI (SC-007, FR-013).
- El texto de las respuestas no sale del servidor hacia servicios de voz externos (FR-011).
- La app no escribe en `data/` ni en el repositorio (FR-012).
- El chat y sus contratos actuales no cambian de comportamiento si la voz falla (FR-009).

**Scale/Scope**: demo con pocos usuarios simultáneos; oraciones de hasta 600 caracteres; 13 voces femeninas
seleccionables por configuración.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Integridad académica y autoría | Los commits los hace el equipo (regla §4.3). El ADR 0020 explica la decisión y los créditos del modelo. | ✅ |
| II. Reproducibilidad y entorno único | `ptts` se agrega con `uv add` y queda en `uv.lock`. Modelo, cuantización y voz se fijan en `config/voice.toml`. Hay un comando de verificación: `python -m proyecto_modelos_lenguaje.voice --check`. | ✅ |
| III. Procedencia, ética y legalidad | El modelo `phonon-40m-es` es CC BY-NC 4.0 y el uso académico no es comercial. La licencia queda en el ADR, la constitución y el README. No se clona ninguna voz real. | ✅ |
| IV. Generación anclada | La voz solo lee la respuesta ya validada o la que se muestra en el streaming; no genera contenido. Si la respuesta final cambia, la voz se corrige (R3). | ✅ |
| V. Evaluación empírica | Métricas SC-001 a SC-006 con procedimiento en `quickstart.md`. La latencia se mide en `voice.jsonl` y se muestra en la traza del turno. | ✅ |
| VII. Simplicidad | Una dependencia nueva, justificada en R1: sin PyTorch y sin servicios extra. Un endpoint nuevo y un módulo `voice/`. | ✅ (justificada) |
| 3.7 App web | La interfaz sigue en React servida por FastAPI y funciona en modo demo. La API no expone el token de Hugging Face. | ✅ |
| 3.8 Pruebas sin red | El sintetizador simulado se usa en las pruebas; el marcador `voice` se excluye por defecto y en la CI. | ✅ |
| 3.9 Seguridad | `HF_TOKEN` vive en `.env` (no versionado) y queda documentado en `.env.example` sin valor. | ✅ |
| Tamaño del repo | El modelo no se versiona, porque vive en la caché de HF. | ✅ |

**Resultado**: PASS. La dependencia nueva está justificada (VII) y se registra en el ADR 0020.

**Re-check post-diseño (Phase 1)**: PASS. Los contratos añaden dos endpoints y un campo opcional en
`HealthStatus`, con valor por defecto, sin romper los existentes. `/api/chat/stream` no cambia.

## Project Structure

### Documentation (this feature)

```text
specs/016-agent-voice-tts/
├── plan.md              # Este archivo
├── research.md          # Phase 0: decisiones R1–R9
├── data-model.md        # Phase 1: configuración, segmento, sesión de lectura, registro
├── quickstart.md        # Phase 1: guía de validación de punta a punta
├── contracts/
│   ├── tts-api.md               # POST /api/tts, GET /api/voice, cambios en /api/health
│   ├── voice-config.md          # config/voice.toml y variables de entorno
│   ├── voice-cli.md             # python -m proyecto_modelos_lenguaje.voice
│   └── ui-voice.md              # Comportamiento de la UI: cola, controles, estados
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks; no lo crea este comando)
```

### Source Code (repository root)

```text
config/voice.toml                     # NUEVO: motor, modelo, cuantización, voz, límites, warmup

src/proyecto_modelos_lenguaje/
├── voice/                            # NUEVO paquete
│   ├── __init__.py
│   ├── config.py      # VoiceConfig (lee config/voice.toml + env MANUELITA_VOICE_*)
│   ├── text.py        # clean_for_speech(), split_sentences() (referencia y pruebas)
│   ├── engine.py      # Synthesizer (Protocol), PhononSynthesizer, FakeSynthesizer, VoiceService
│   │                  #   (carga perezosa con Lock, estado available/reason, warmup)
│   ├── audio.py       # to_wav_bytes(float32, sample_rate) con la librería estándar `wave`
│   ├── log.py         # registro en MANUELITA_STATE_DIR/logs/voice.jsonl
│   └── __main__.py    # CLI: --check, --list-voices, --say TEXTO [-o out.wav] [--voice]
├── api.py             # + POST /api/tts, GET /api/voice, warmup al arrancar, health.voice_available
└── api_models.py      # + TtsRequest, VoiceStatus; HealthStatus.voice_available

web/src/
├── lib/voice.ts               # NUEVO: SentenceSegmenter, VoicePlayer (cola, prefetch, AbortController)
├── lib/useVoice.ts            # NUEVO: hook (estado, preferencia en localStorage, disponibilidad)
├── components/VoiceControls.tsx # NUEVO: silenciar/activar, detener, aviso de no disponible
├── components/ChatView.tsx    # tokens → segmentador; done → corrección; botón «Escuchar» por turno
└── lib/types.ts, lib/api.ts   # VoiceStatus, getVoice(), synthesize()

tests/
├── unit/voice/test_text.py, test_engine.py, test_audio.py, test_config.py, test_cli.py
├── api/test_voice_api.py              # contrato de /api/tts y /api/voice con FakeSynthesizer
├── integration/voice/test_phonon_real.py  # @pytest.mark.voice: modelo real, voz femenina, WAV válido
web/src/test/voice.test.ts, VoiceControls.test.tsx, ChatView.test.tsx (+ casos de voz)

docs/decisions/0020-voz-phonon.md     # NUEVO: ADR (servidor vs. WASM, licencia, oraciones)
CONSTITUTION.md, README.md, docs/demo.md, .env.example, pyproject.toml (marcador voice), uv.lock
```

**Structure Decision**: La voz vive en un paquete propio, `voice/`, desacoplado del agente: el grafo, el prompt y
`/api/chat/stream` no cambian. La integración pasa por un endpoint HTTP y por la capa de UI, para que una falla de
voz no pueda afectar un turno del agente. La limpieza del texto la hace solo el servidor; el navegador solo corta
oraciones.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dependencia nueva `ptts` (Principio VII) | Es el motor Phonon que pidió el equipo, y la síntesis natural en español no existe en el stack actual. | La ruta Transformers exige PyTorch y es mucho más pesada. Phonon en WASM no soporta el modelo en español desde el paquete npm. `speechSynthesis` no es Phonon y su calidad depende del sistema operativo. |
