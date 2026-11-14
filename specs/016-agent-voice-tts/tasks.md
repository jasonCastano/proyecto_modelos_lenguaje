# Tasks: Voz del agente en español con síntesis natural (Phonon)

**Input**: Design documents from `/specs/016-agent-voice-tts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluidas. La spec las exige (FR-013, SC-007) y la constitución (§3.8) pide al menos una prueba por
módulo crítico. Todas corren sin red y sin el modelo (`FakeSynthesizer`), salvo las marcadas `@pytest.mark.voice`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/` (paquete nuevo `voice/`), configuración en `config/`.
- Frontend: `web/src/` (`lib/`, `components/`, `test/`).
- Pruebas Python: `tests/unit/voice/`, `tests/api/`, `tests/integration/voice/`.
- Comandos Python con `UV_PROJECT_ENVIRONMENT=.venv uv run ...` (la variable global apunta a otro proyecto).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencia, configuración, marcador de pruebas y verificación de la API real de Phonon (research R10).

- [X] T001 Agregar `ptts>=0.7.1` con `UV_PROJECT_ENVIRONMENT=.venv uv add "ptts>=0.7.1"`, que actualiza `pyproject.toml` y `uv.lock`. Verificar que importa en Python 3.14 y anotar en `specs/016-agent-voice-tts/research.md` (R10) la firma real: constructor de `ptts.TTS`, `synth`, `stream`, `sample_rate` y si existe una forma de listar o resolver voces por nombre.
- [X] T002 [P] Crear `config/voice.toml` con la sección `[voice]` exacta de `contracts/voice-config.md`: `enabled = true`, `engine = "phonon"`, `model = "hf://gradium/phonon-40m-es"`, `language = "es"`, `quant = "q8_0"`, `voice = "Rebeca"`, `voice_gender = "female"`, `max_chars = 600`, `warmup = true`.
- [X] T003 [P] Registrar el marcador en `pyproject.toml`: añadir a `markers` `"voice: requiere el modelo Phonon descargado (HF_TOKEN); excluida por defecto y en CI"` y cambiar `addopts` a `"-q -m 'not network and not voice'"`. Revisar que `.github/workflows/ci.yml` y el `Makefile` no lo pisen.
- [X] T004 [P] Añadir `HF_TOKEN=` sin valor a `.env.example`, con un comentario: «token de lectura de Hugging Face; aceptar las condiciones de gradium/phonon-40m-es».
- [X] T005 [P] Crear los paquetes vacíos `src/proyecto_modelos_lenguaje/voice/__init__.py`, `tests/unit/voice/__init__.py` y `tests/integration/voice/__init__.py`, con docstrings en español.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configuración, limpieza de texto, motor con estado, WAV y modelos de la API, que comparten las tres historias.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests (escribir primero; deben fallar)

- [X] T006 [P] Pruebas de configuración en `tests/unit/voice/test_config.py`. Cubren la lectura de `config/voice.toml`, la prioridad de `MANUELITA_VOICE_ENABLED`, `MANUELITA_VOICE_ENGINE`, `MANUELITA_VOICE` y `MANUELITA_VOICE_WARMUP`, y el rechazo de `engine` fuera de `"phonon" | "fake"`, `quant` fuera de `ptts.available_quants()` (p. ej. `"q8"` o `"q4"`), `max_chars` fuera de 1–1000 y `voice` vacía.
- [X] T007 [P] Pruebas de limpieza en `tests/unit/voice/test_text.py`:
  - `clean_for_speech` aplica los pasos en este orden: (1) quita `[instrucción embebida omitida]`; (2) quita `[U\d+]` y `[U1, U2]`; (3) convierte `[texto](url)` en `texto` y quita las URLs; (4) quita `*`, `_`, `#`, `` ` ``, `>` y las viñetas al inicio de línea; (5) `%` → « por ciento », `&` → « y »; (6) colapsa los espacios.
  - El texto sin letras ni dígitos queda vacío.
  - `split_sentences` no corta en `Sr.`, `Dra.`, `etc.`, `p. ej.`, `No.` ni en `3.5`, y parte las oraciones de más de 600 caracteres por comas o espacios.
- [X] T008 [P] Pruebas de audio en `tests/unit/voice/test_audio.py`: `to_wav_bytes` produce un WAV válido (cabecera RIFF; leído con `wave`: mono, 16 bits, la `sample_rate` dada) y recorta los valores fuera de [-1, 1].
- [X] T009 [P] Pruebas del motor en `tests/unit/voice/test_engine.py`:
  - `FakeSynthesizer` es determinista y su duración es proporcional al texto.
  - El estado de `VoiceService` empieza en `loading`; pasa a `ready` tras cargar; queda en `disabled` si `enabled=false`; pasa a `unavailable` con un `detail` legible, sin traza ni ruta absoluta, si falla el import o la carga (simulados con monkeypatch).
  - Un error de síntesis deja el estado en `ready`.
  - Las llamadas concurrentes se serializan con el `Lock`.

### Implementation

- [X] T010 [P] Implementar `VoiceConfig` (dataclass congelada) y `load_voice_config()` en `src/proyecto_modelos_lenguaje/voice/config.py`. Lee `config/voice.toml` desde `PROJECT_ROOT`, aplica las variables `MANUELITA_VOICE_*` y valida según data-model.md.
- [X] T011 [P] Implementar `clean_for_speech(text) -> str` y `split_sentences(text, max_chars=600) -> list[str]` en `src/proyecto_modelos_lenguaje/voice/text.py`, con el orden de limpieza de data-model.md. Importar `OMITTED_MARKER` desde `agent/guard.py`, no duplicar la cadena.
- [X] T012 [P] Implementar `to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes` en `src/proyecto_modelos_lenguaje/voice/audio.py`, con `wave` e `io.BytesIO`: float32 → int16 con recorte. Agregar también `duration_ms(samples, sample_rate)`.
- [X] T013 Implementar en `src/proyecto_modelos_lenguaje/voice/engine.py`:
  - El `Protocol` `Synthesizer`, con `sample_rate: int`, `synth(text, voice) -> np.ndarray` y `voices() -> list[VoiceInfo]`.
  - `FakeSynthesizer` (24 kHz, tono o silencio de unos 60 ms por carácter; incluye un catálogo fijo con las 13 voces femeninas de research R4 y algunas masculinas).
  - `PhononSynthesizer`, que envuelve `ptts.TTS(config.model, lang=config.language, quant=config.quant)` según la firma verificada en T001 y mapea los errores de descarga, acceso o CPU a mensajes en español.
  - `VoiceService`, con estado `disabled|loading|ready|unavailable`, carga perezosa con `threading.Lock`, `warmup_async()`, `status() -> VoiceStatusData` y `synthesize(text, voice=None) -> SynthResult(samples, sample_rate, synth_ms, audio_ms)`.
  - El singleton `get_voice_service()`, con `reset_voice_service()` para las pruebas.
- [X] T014 Agregar los modelos Pydantic en `src/proyecto_modelos_lenguaje/api_models.py`:
  - `TtsRequest`, con `extra="forbid"`: `text: str` (min_length=1), `voice: str | None = None`, `thread_id: str | None = None`, `segment: int | None = Field(default=None, ge=0)`.
  - `VoiceStatus`, con los campos `available`, `state` (`Literal["disabled","loading","ready","unavailable"]`), `engine`, `model`, `voice`, `language`, `sample_rate: int | None`, `license` y `detail: str | None`.
  - `HealthStatus.voice_available: bool = False`.
- [X] T015 Implementar `log_voice(record)` en `src/proyecto_modelos_lenguaje/voice/log.py`. Agrega una línea JSON a `MANUELITA_STATE_DIR/logs/voice.jsonl` con `ts`, `thread_id`, `segment`, `voice`, `chars`, `synth_ms`, `audio_ms`, `status` (`"ok" | "empty" | "error" | "unavailable"`) y `error`. Nunca guarda el texto ni el audio, y traga los errores de E/S. Reutiliza la resolución del directorio de estado de `agent/config.py`.

**Checkpoint**: `VoiceService` sintetiza con el motor simulado y reporta su estado; T006–T009 pasan.

---

## Phase 3: User Story 1 - Escuchar la respuesta del agente mientras se genera (Priority: P1) 🎯 MVP

**Goal**: mientras el texto llega por streaming, cada oración completa se sintetiza en el servidor y suena en orden con voz femenina en español, sin pronunciar citas ni marcas. Funciona en modo demo y real y en las dos variantes (FR-001…FR-005, FR-008, FR-011, FR-012, FR-014).

**Independent Test**: quickstart §3, fila «Voz en vivo». Con `MANUELITA_VOICE_ENGINE=fake`, Vitest verifica que la primera petición a `/api/tts` sale antes del evento `done` y que el audio se encola en orden. Con el motor real, la pregunta «¿Qué produce Manuelita?» suena mientras el texto aparece.

### Tests for User Story 1 ⚠️

- [X] T016 [P] [US1] Prueba de contrato de `POST /api/tts` en `tests/api/test_voice_api.py`, con `MANUELITA_VOICE_ENGINE=fake` y `MANUELITA_VOICE_WARMUP=0`:
  - `200` devuelve `audio/wav` válido con `X-Voice`, `X-Synth-Ms`, `X-Audio-Ms` y `Cache-Control: no-store`.
  - Un texto con solo `[U2]` devuelve `204`.
  - Más de 600 caracteres devuelve `422 text_too_long`; una voz fuera del catálogo, `422 unknown_voice`; un campo extra, `422`.
  - El texto que llega al sintetizador ya está limpio, y se espía con monkeypatch.
  - Se escribe una línea en `voice.jsonl` bajo un `MANUELITA_STATE_DIR` temporal, sin el texto.
  - Funciona sin `DEEPSEEK_API_KEY`.
- [X] T017 [P] [US1] Pruebas del segmentador y la cola en `web/src/test/voice.test.ts`:
  - `SentenceSegmenter.push`/`flush` con fragmentos que cortan palabras y oraciones a la mitad, abreviaturas y decimales.
  - `VoicePlayer` con `fetch` y `AudioContext` simulados: como máximo 2 peticiones en vuelo, reproducción en orden de `segment` aunque las respuestas lleguen desordenadas, un `204` se salta, y `firstAudioMs` se mide desde que se cierra la primera oración.
- [X] T018 [P] [US1] Casos de voz en `web/src/test/ChatViewVoice.test.tsx` con `streamChat` simulado:
  - La primera llamada a `/api/tts` ocurre antes de `done`.
  - Las oraciones se piden en orden con `thread_id` y `segment`.
  - Si `done.response.answer` difiere del streaming, se detiene la cola y se pide la respuesta final desde `segment` 0.
  - La traza del turno muestra «🔊 primer audio».

### Implementation for User Story 1

- [X] T019 [US1] Agregar `POST /api/tts` en `src/proyecto_modelos_lenguaje/api.py` según `contracts/tts-api.md`:
  - Valida `max_chars` y la voz contra `service.voices()`, limpia con `clean_for_speech` y sintetiza con `get_voice_service()`.
  - Responde con `Response(content=to_wav_bytes(...), media_type="audio/wav")` y las cabeceras; `204` si el texto queda vacío; `500 voice_error` (`retryable: true`) si falla la síntesis.
  - Registra con `log_voice` y usa el formato de error `{"error": {...}}` existente.
- [X] T020 [US1] Agregar `GET /api/voice` (`response_model=VoiceStatus`) en `src/proyecto_modelos_lenguaje/api.py`. Llama a `warmup_async()` en el arranque de la app solo si `config.warmup` y el motor no es `fake`, sin bloquear el inicio.
- [X] T021 [P] [US1] Agregar a `web/src/lib/types.ts` el tipo `VoiceStatus` y a `web/src/lib/api.ts` las funciones `getVoice()` y `synthesize({text, threadId, segment, voice}, signal) -> Promise<ArrayBuffer | null>`; `null` para `204`, y para `503` lanza `ApiClientError` con code `voice_unavailable`.
- [X] T022 [US1] Implementar en `web/src/lib/voice.ts`:
  - `SentenceSegmenter`, según las reglas de data-model.md.
  - `VoicePlayer`, con una cola ordenada por `segment`, prefetch de 2, `decodeAudioData`, reproducción encadenada con `AudioBufferSourceNode`, `AbortController` por sesión, una única sesión activa, `stop()` en menos de 0,5 s (`source.stop()` y abort) y medición de `firstAudioMs`.
  - Una función `normalizeForCompare(text)` que quita `[U#]` y colapsa los espacios.
- [X] T023 [US1] Crear el hook `useVoice()` en `web/src/lib/useVoice.ts`. Consulta `getVoice()` al montar; expone `enabled`, `available`, `speaking`, `detail`, `startLive(threadId)`, `pushToken(text)`, `finishLive(finalAnswer)`, `speak(text, threadId)` y `stop()`; crea o reanuda el `AudioContext` en el gesto de envío.
- [X] T024 [US1] Integrar en `web/src/components/ChatView.tsx`:
  - Al enviar, `stop()` y luego `startLive`.
  - En los eventos `token`, `pushToken(event.text)`.
  - En `done`, `finishLive(response.answer)` con la regla de corrección de research R3.
  - En `error` o al desmontar, `stop()`.
  - Mostrar «🔊 primer audio X,X s» en `turn-trace` cuando haya medición.
- [X] T025 [US1] Prueba con el modelo real en `tests/integration/voice/test_phonon_real.py` (`@pytest.mark.voice`): `VoiceService` con el motor `phonon` llega a `ready`, la voz configurada existe y es femenina en el catálogo, una oración en español produce un WAV de 24 kHz con duración > 0, y la síntesis de una oración de unos 100 caracteres tarda menos de 1,0 s en CPU.

**Checkpoint**: US1 funcional. Con el motor simulado en CI y con Phonon en local, la respuesta suena por oraciones mientras se genera.

---

## Phase 4: User Story 2 - Controlar la voz (Priority: P2)

**Goal**: silenciar o activar con persistencia, detener, «Escuchar» por turno, y que una nueva pregunta corte la lectura anterior (FR-006, FR-007; contrato `ui-voice.md`).

**Independent Test**: quickstart §3, fila «Controles». En Vitest:
- `voice-stop` detiene el audio y aborta las peticiones.
- Con `voice-toggle` silenciado no hay llamadas a `/api/tts` y el estado sobrevive al remontaje (`localStorage`).
- `turn-listen` pide la respuesta guardada.
- Un segundo envío detiene la sesión anterior.

### Tests for User Story 2 ⚠️

- [X] T026 [P] [US2] Pruebas en `web/src/test/VoiceControls.test.tsx`:
  - El toggle cambia `aria-pressed` y escribe `localStorage["manuelita.voice.muted"] = "1"`.
  - La lectura de `localStorage` va en `try/catch`: si lanza, la voz queda activada solo en la sesión.
  - `voice-stop` solo es visible mientras suena audio.
  - `voice-speaking` tiene `aria-live="polite"`.
- [X] T027 [P] [US2] Casos en `web/src/test/ChatViewVoice.test.tsx`:
  - Silenciado no llama a `/api/tts`.
  - `turn-listen` lee `turn.answer` completo.
  - Una nueva pregunta durante la lectura llama a `stop()` antes de la primera petición nueva.
  - `NotAllowedError` muestra `voice-resume`.

### Implementation for User Story 2

- [X] T028 [US2] Crear `web/src/components/VoiceControls.tsx`, con `voice-toggle`, `voice-stop`, `voice-speaking` y `voice-resume` según `contracts/ui-voice.md`, textos en español y estilos con las variables de la paleta existente en `web/src/styles` (o el CSS global actual).
- [X] T029 [US2] Añadir al hook `web/src/lib/useVoice.ts` la preferencia persistente (`manuelita.voice.muted`, `"1"` = silenciado, con `try/catch`). Al silenciar llama a `stop()`; agrega el manejo de `NotAllowedError` con `resume()`.
- [X] T030 [US2] Integrar en `web/src/components/ChatView.tsx`: `VoiceControls` en la cabecera del chat y el botón «Escuchar» (`turn-listen`) en cada turno terminado, que llama a `speak(turn.answer, threadId)`.

**Checkpoint**: US1 y US2 funcionan; la voz se controla sin afectar el texto.

---

## Phase 5: User Story 3 - Degradación segura cuando la voz no está disponible (Priority: P3)

**Goal**: sin motor o con una falla, el chat sigue igual por texto, la UI avisa y el estado del servidor lo informa (FR-009, FR-010; SC-006).

**Independent Test**: quickstart §3, fila «Sin voz». Con `MANUELITA_VOICE_ENABLED=0`:
- `GET /api/voice` devuelve `available=false, state="disabled"`.
- `/api/health` devuelve `voice_available=false`.
- `/api/tts` responde `503 voice_unavailable`.
- La UI muestra `voice-unavailable` y el chat responde.

### Tests for User Story 3 ⚠️

- [X] T031 [P] [US3] Pruebas en `tests/api/test_voice_api.py`:
  - `GET /api/voice` en los estados `ready` (motor simulado), `disabled` y `unavailable` (import simulado fallando), sin token, rutas absolutas ni trazas en `detail`.
  - `POST /api/tts` devuelve `503` con `{"error": {"code": "voice_unavailable", "retryable": false, "action": "continuar sin voz"}}`.
  - `/api/health` incluye `voice_available` en sus tres ramas.
  - `/api/chat` y `/api/chat/stream` responden igual con la voz desactivada.
- [X] T032 [P] [US3] Casos en `web/src/test/ChatViewVoice.test.tsx`:
  - `getVoice()` con `available=false` muestra `voice-unavailable` con el `detail`, deshabilita el toggle y no llama a `/api/tts`.
  - Un `503` a mitad de una respuesta detiene la voz, muestra el aviso y deja el texto completo.
  - Un `500` en una oración la salta y sigue con la siguiente.

### Implementation for User Story 3

- [X] T033 [US3] En `src/proyecto_modelos_lenguaje/api.py`:
  - `/api/tts` responde `503 voice_unavailable` si el estado es `disabled` o `unavailable`.
  - `health()` rellena `voice_available` en las tres ramas con `get_voice_service().status().available`, sin forzar la carga.
  - `observability()` agrega `"voice": {available, state, voice}`.
- [X] T034 [US3] En `web/src/lib/useVoice.ts` y `web/src/components/VoiceControls.tsx`:
  - Un `503` o `available=false` desactiva la voz durante la sesión y muestra el aviso «La voz no está disponible: {detail}. El chat sigue funcionando por texto.».
  - Otros errores se saltan oración por oración.
- [X] T035 [US3] Implementar la CLI `src/proyecto_modelos_lenguaje/voice/__main__.py` según `contracts/voice-cli.md`, con `--check`, `--list-voices`, `--say TEXTO`, `-o`, `--voice` y `--json`. Códigos de salida: 0 OK, 1 argumentos o síntesis, 2 no disponible. Sin `-o` escribe en un archivo temporal y nunca en `data/`.
- [X] T036 [P] [US3] Pruebas de la CLI en `tests/unit/voice/test_cli.py`, con `MANUELITA_VOICE_ENGINE=fake`:
  - `--check --json` sale con 0 y `engine: fake`.
  - `--say` con `-o` en `tmp_path` produce un WAV válido.
  - `MANUELITA_VOICE_ENABLED=0 --check` sale con 2.
  - `--list-voices` marca la voz configurada.

**Checkpoint**: las tres historias funcionan de forma independiente; la voz nunca rompe el chat.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Elección de la voz, documentación, gobernanza y verificación completa.

- [X] T037 Elegir la voz (research R4):
  - Con el motor real, generar la misma respuesta típica con las 13 voces femeninas: `uv run python -m proyecto_modelos_lenguaje.voice --say ... --voice <nombre> -o <scratch>/<nombre>.wav`, fuera del repositorio.
  - Presentarlas al equipo, fijar la elegida en `config/voice.toml` y registrar la elección en `research.md` (R4).
- [X] T038 [P] Escribir `docs/decisions/0020-voz-phonon.md`, ADR con:
  - La síntesis en el servidor frente a WASM.
  - La síntesis por oración sobre el streaming existente y la corrección con la respuesta final.
  - La licencia CC BY-NC 4.0 del modelo y las voces, y MIT/Apache-2.0 del motor.
  - El uso de `HF_TOKEN` y las alternativas rechazadas (Transformers/PyTorch, `speechSynthesis`, audio dentro del SSE).
- [X] T039 [P] Actualizar `CONSTITUTION.md`: versión menor, fecha 2026-11-14; agregar `ptts`/Phonon al stack con su justificación (VII), la licencia del modelo (III, §3.9) y `HF_TOKEN` en secretos; mencionar en §3.7 que el chat tiene voz y se puede silenciar.
- [X] T040 [P] Actualizar `README.md` (voz del agente, prerrequisito `HF_TOKEN`, comando `voice --check`, créditos y licencia del modelo), `docs/demo.md` (guion de la demo con voz y qué hacer si no hay modelo) y `CLAUDE.md` (comando de la CLI de voz y marcador `voice`).
- [ ] T041 [P] Si `docs/arquitectura.json` describe los componentes de runtime, agregar el nodo «Voz (Phonon, `/api/tts`)» y regenerar `docs/arquitectura.html` con el flujo existente del proyecto (Archify).
- [X] T042 Ejecutar `UV_PROJECT_ENVIRONMENT=.venv make check` (Ruff, formato, pytest sin red ni modelo, Vitest y build web) y corregir hasta que quede en verde.
- [X] T043 Ejecutar la prueba con el modelo real: `UV_PROJECT_ENVIRONMENT=.venv uv run pytest -o addopts="" -m voice tests/integration/voice`. Requiere `HF_TOKEN` y las condiciones aceptadas; si faltan, documentarlo como bloqueo para el usuario.
- [X] T044 Validación manual con `quickstart.md` §3: los seis escenarios con `make app`, midiendo SC-001 sobre 10 preguntas de la rúbrica con `voice.jsonl` y la traza «primer audio». Anotar los resultados en `specs/016-agent-voice-tts/quickstart.md` (sección de resultados).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias. T001 va primero porque fija la firma real de `ptts`, que usa T013.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de US1, porque reutiliza `VoicePlayer` y `useVoice` (T022, T023).
- **US3 (Phase 5)**: la parte del backend (T031, T033, T035, T036) depende solo de Foundational; la parte de la UI (T032, T034) depende de T023.
- **Polish (Phase 6)**: depende de las historias que se quieran entregar. T037, T043 y T044 requieren el modelo real.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Backend (endpoint) antes que el cliente (`api.ts`), el cliente antes que `voice.ts` y `useVoice`, y estos antes que `ChatView`.

### Parallel Opportunities

- Setup: T002, T003, T004 y T005 en paralelo, después de T001.
- Foundational: las pruebas T006–T009 en paralelo; luego T010, T011 y T012 en paralelo, seguidos de T013, T014 y T015.
- US1: las pruebas T016, T017 y T018 en paralelo; T021 en paralelo con T019 y T020.
- US3: el backend (T031, T033, T035, T036) puede avanzar en paralelo con US2.
- Polish: T038, T039, T040 y T041 en paralelo.

## Parallel Example: User Story 1

```bash
# Pruebas de US1 en paralelo (archivos distintos):
Task: "T016 Contrato POST /api/tts en tests/api/test_voice_api.py"
Task: "T017 Segmentador y cola en web/src/test/voice.test.ts"
Task: "T018 Casos de voz en vivo en web/src/test/ChatView.test.tsx"

# Implementación en paralelo:
Task: "T019 POST /api/tts en api.py"
Task: "T021 getVoice/synthesize en web/src/lib/api.ts"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 (Setup) y Fase 2 (Foundational).
2. Fase 3 (US1): la voz suena en vivo por oraciones.
3. **Parar y validar**: quickstart §1 sin red y §3 «Voz en vivo» con Phonon.
4. Demo posible: el agente ya «habla».

### Incremental Delivery

1. Setup + Foundational → motor simulado probado.
2. US1 → voz en vivo (MVP).
3. US2 → controles (silenciar, detener, escuchar).
4. US3 → degradación segura y CLI de diagnóstico.
5. Polish → voz definitiva elegida, ADR, constitución, documentación y verificación.

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- `make check` y la CI nunca descargan el modelo; solo las pruebas `@pytest.mark.voice` lo usan.
- Los commits, push y PR los hace el equipo (CONSTITUTION §4.3), salvo autorización explícita.
- No escribir audio ni el modelo en `data/` ni en el repositorio.
