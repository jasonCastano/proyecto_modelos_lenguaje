# Tasks: Hablarle a Valer-IA Caña con la voz (dictado en la interfaz)

**Input**: Design documents from `/specs/023-voice-input/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluidas. La spec pide una evaluación reproducible (FR-023) y metas verificables:
- reconocimiento: WER, vocabulario, latencia y vacío en silencio (SC-001 a SC-004);
- 0 ecos enviados (SC-005);
- 0 audios en disco (SC-006);
- chat intacto sin STT (SC-008).

Las pruebas usan `engine = "fake"` y no necesitan red ni modelo. Las que requieren el modelo real llevan el marcador
`voice` y las de navegador `PML_E2E=1`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

- Backend:
  - `src/proyecto_modelos_lenguaje/stt/` (abreviado `stt/`);
  - API en `src/proyecto_modelos_lenguaje/api.py` y `api_models.py`;
  - configuración en `config/stt.toml`.
- Frontend: `web/src/`.
- Pruebas: `tests/unit/stt/`, `tests/api/`, `tests/integration/stt/`, `tests/e2e/` y `web/src/test/`.
- Contratos:
  - [contracts/stt-api.md](./contracts/stt-api.md) (abreviado A);
  - [contracts/ui.md](./contracts/ui.md) (abreviado U);
  - [data-model.md](./data-model.md) (abreviado DM).
- Comandos: `UV_PROJECT_ENVIRONMENT=.venv uv run …` (ver research R14).
- Patrón de referencia: `src/proyecto_modelos_lenguaje/voice/` (config, engine, log y `__main__`), que `stt/` replica.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, configuración y esqueleto del subpaquete.

- [X] T001 Promover `faster-whisper>=1.2.1` y `av>=14,<20` de `[project.optional-dependencies].asr` a `[project].dependencies` en `pyproject.toml`. Dejar `asr = []` como alias vacío para no romper `uv run --extra asr` de `scripts/transcribe_youtube.py`. Ejecutar `uv lock` y `UV_PROJECT_ENVIRONMENT=.venv uv sync`, y comprobar `python -c "import faster_whisper, av"`.
- [X] T002 [P] Crear `config/stt.toml` con la sección `[stt]` y los defectos de DM §1:
  - `enabled = true`, `engine = "whisper"`, `model = "base"`, `compute_type = "int8"`, `cpu_threads = 0`;
  - `language = "es"`, `beam_size = 1`;
  - `vocabulary` (Manuelita, Valer-IA Caña, Palmira, Valle del Cauca, Fundación Manuelita, Océanos, Mejillones América, Laredo, Aceites Manuelita, Ingenio Manuelita, Educar Uno a Uno, Línea Ética);
  - `corrections` (`"valeria caña" = "Valer-IA Caña"`, `"valeria" = "Valer-IA"`, `"manuelita" = "Manuelita"`, `"oceanos" = "Océanos"`);
  - `no_speech_threshold = 0.6`, `max_seconds = 60`, `max_bytes = 2097152`;
  - `silence_ms = 1500`, `min_speech_ms = 300`, `handsfree_idle_seconds = 60`;
  - `max_concurrent = 2`, `queue_timeout_seconds = 10`, `warmup = true`.

  Comentarios en español: licencia MIT del modelo y variables `MANUELITA_STT_*`.
- [X] T003 [P] Crear el esqueleto `src/proyecto_modelos_lenguaje/stt/__init__.py` (docstring de la spec 023 y exportaciones públicas), `tests/unit/stt/__init__.py` y `tests/integration/stt/__init__.py`.
- [X] T004 [P] Crear `tests/fixtures/stt/phrases.jsonl` con unas 40 líneas `{"id", "text", "vocab": [...], "kind": "speech"}`:
  - 12 preguntas de demo («¿Qué produce Manuelita?»…);
  - 8 de charla («hola Valer-IA Caña, ¿cómo estás?»);
  - 8 con números y años;
  - 12 con nombres del vocabulario (Océanos, Mejillones América, Palmira, Fundación Manuelita…).

  Duración de 1 a 12 s al leerlas. Agregar 6 entradas `{"id", "kind": "silence"|"noise", "seconds", "seed"}`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: motor, API y contratos de datos que necesitan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

### Tests (escribir primero; deben fallar)

- [X] T005 [P] Pruebas en `tests/unit/stt/test_config.py`:
  - defectos de DM §1;
  - el TOML sobrescribe los defectos y `MANUELITA_STT_ENABLED`, `MANUELITA_STT_ENGINE`, `MANUELITA_STT_MODEL` y `MANUELITA_STT_WARMUP` tienen prioridad;
  - validaciones que producen `SttConfigError`:
    - `engine` fuera de `whisper`/`fake`;
    - `compute_type` fuera de `int8`/`int8_float32`/`float32`;
    - `beam_size` fuera de 1–5;
    - `max_seconds` fuera de 1–120;
    - `max_bytes` < 44 + 16000·2·`max_seconds`;
    - `silence_ms` fuera de 300–5000;
    - `min_speech_ms` fuera de 100–2000;
    - `handsfree_idle_seconds` fuera de 10–600;
    - `max_concurrent` fuera de 1–8;
    - `queue_timeout_seconds` fuera de 1–60;
    - más de 60 términos o un término de más de 40 caracteres en `vocabulary`;
    - `initial_prompt` de más de 600 caracteres.
- [X] T006 [P] Pruebas en `tests/unit/stt/test_audio.py`:
  - `parse_wav16k` acepta RIFF/WAVE PCM 16 bits mono a 16000 Hz y devuelve `float32` en [-1, 1] con `audio_ms` correcto;
  - rechaza con `UnsupportedAudioError` el estéreo, 44.1 kHz, PCM 8/24 bits, float, MP3 o bytes basura, y un `data` truncado;
  - `EmptyAudioError` para cuerpo vacío o 0 muestras;
  - `AudioTooLargeError` si supera `max_bytes` o `max_seconds`;
  - helper `encode_wav16k(samples)` para las pruebas, en el mismo módulo.
- [X] T007 [P] Pruebas en `tests/unit/stt/test_text.py`:
  - `initial_prompt(vocabulary)` une con «, », termina en punto y respeta 600 caracteres;
  - `apply_corrections` reemplaza solo palabras completas, sin distinguir mayúsculas ni tildes («valeria caña» → «Valer-IA Caña», «manuelitas» no cambia);
  - `clip_message` recorta a 2000 caracteres en un límite de palabra e informa `truncated`;
  - `is_noise` (de `transcription.py`) descarta «Subtítulos realizados por la comunidad de Amara.org» y «¡Gracias por ver!».
- [X] T008 [P] Pruebas en `tests/unit/stt/test_engine.py`:
  - `FakeTranscriber` devuelve vacío con RMS < 0.01 y si no, una frase fija o el texto codificado en la etiqueta de la prueba (`audio_marker`);
  - `SttService`:
    - estados `disabled` / `loading` / `ready` / `unavailable` con `detail` sin rutas;
    - `ensure_loaded` es idempotente;
    - `warmup_async` no bloquea;
    - con `max_concurrent = 1`, una segunda transcripción espera y pasado `queue_timeout_seconds` lanza `SttBusyError`;
    - `transcribe()` devuelve `Transcription(text, empty, truncated, language, audio_ms, stt_ms, model)` con correcciones y recorte aplicados;
    - descarta segmentos con `no_speech_prob > no_speech_threshold`.
  - `WhisperTranscriber` probado con un `WhisperModel` simulado (sin red) que verifica los parámetros:
    - `language`, `beam_size`, `vad_filter=True`, `condition_on_previous_text=False`;
    - `initial_prompt` del vocabulario;
    - `cpu_threads`.
- [X] T009 [P] Pruebas de contrato en `tests/api/test_stt_api.py` con `MANUELITA_STT_ENGINE=fake` (A §1–§3):
  - `GET /api/stt`: campos exactos, `privacy` no vacío y parámetros del cliente;
  - `POST /api/stt` con WAV de voz simulada → 200 con `text`, `empty=false`, `audio_ms` y `stt_ms`;
  - WAV de silencio → 200 `empty=true`, `text=""`;
  - cuerpo vacío → 400 `stt_empty_audio`;
  - más de `max_bytes` → 413 `stt_too_large`;
  - MP3 o estéreo → 415 `stt_unsupported_format`;
  - servicio deshabilitado → 503 `stt_unavailable` con `retryable=true`;
  - ocupado → 503 `stt_busy`;
  - excepción del motor → 500 `stt_error` sin traza;
  - `GET /api/health` incluye `stt_available`;
  - **SC-006**: tras 5 peticiones no hay archivos nuevos en `tmp_path` (cwd cambiado con `monkeypatch.chdir`), en `tempfile.gettempdir()` (comparar listados antes y después) ni en `data/`;
  - el registro `stt` (caplog) no contiene el texto reconocido.

### Implementation

- [X] T010 Implementar `stt/config.py` (`SttConfig` congelado, `SttConfigError`, `load_stt_config(path=None)` con TOML y variables) para que pase T005. Replicar `voice/config.py` (`_flag`, `FALSE_VALUES`, `TRUE_VALUES`). `CONFIG_PATH = PROJECT_ROOT / "config" / "stt.toml"`.
- [X] T011 [P] Implementar `stt/audio.py` para que pase T006:
  - `parse_wav16k(data: bytes, *, max_bytes, max_seconds) -> tuple[np.ndarray, int]` con `wave` de la biblioteca estándar sobre `io.BytesIO` (nunca archivos);
  - errores `EmptyAudioError`, `UnsupportedAudioError` y `AudioTooLargeError`;
  - `encode_wav16k(samples: np.ndarray) -> bytes`.
- [X] T012 [P] Implementar `stt/text.py` (`initial_prompt`, `apply_corrections`, `clip_message` con `MAX_MESSAGE_CHARS = 2000` y `is_noise` reexportado de `transcription.py`) para que pase T007.
- [X] T013 [P] Implementar `stt/log.py` con `log_stt(*, thread_id, audio_ms, stt_ms, bytes, model, status, chars, error=None)`, con el mismo formato y logger que `voice/log.py`. Nunca recibe ni registra el texto.
- [X] T014 Implementar `stt/engine.py` para que pase T008:
  - `Transcriber(Protocol).transcribe(samples) -> list[Segment]`;
  - `FakeTranscriber` y `WhisperTranscriber(config)`:
    - carga perezosa `WhisperModel(config.model, device="cpu", compute_type=…, cpu_threads=…)`;
    - errores de descarga o carga traducidos a un `detail` legible, como `voice/engine.py::_friendly_load_error`.
  - `SttService` con estado, `threading.Lock` de carga, `threading.BoundedSemaphore(max_concurrent)` con `acquire(timeout=queue_timeout_seconds)`, `warmup_async()`, `status()` y `transcribe(samples, audio_ms)`:
    - aplica `no_speech_threshold`, `is_noise`, `apply_corrections` y `clip_message`;
    - mide `stt_ms` con `perf_counter`.
  - `get_stt_service()` singleton y `reset_stt_service()` para pruebas.
- [X] T015 Agregar a `src/proyecto_modelos_lenguaje/api_models.py` (A §1–§4, `extra="forbid"`):
  - `SttStatus` (`available`, `state` literal `disabled|loading|ready|unavailable`, `engine`, `model`, `language`, `detail: str | None`, `max_seconds`, `silence_ms`, `min_speech_ms`, `handsfree_idle_seconds`, `privacy`);
  - `SttResult` (`text`, `empty`, `truncated`, `language`, `audio_ms`, `stt_ms`, `model`);
  - `InputMeta`:
    - `source: Literal["voice"]`;
    - `audio_ms: int = Field(ge=0, le=120_000)`;
    - `stt_ms: int = Field(ge=0, le=60_000)`;
    - `edited: bool = False`, `handsfree: bool = False`.
  - `stt_available: bool = False` en `HealthStatus`.
- [X] T016 Implementar en `src/proyecto_modelos_lenguaje/api.py`:
  - `GET /api/stt` → `SttStatus`;
  - `POST /api/stt`:
    - lee `await request.body()` con tope `max_bytes + 1` y revisa `Content-Type: audio/wav` o `audio/x-wav`;
    - `parse_wav16k` → `service.transcribe`;
    - mapea los errores a A §2 con el formato de error existente (`_error(...)` o el helper que usa `/api/tts`);
    - llama a `log_stt` con la cabecera `X-Thread-Id`, si viene.
  - `stt_available` en `/api/health`;
  - precalentamiento en el arranque junto a `_voice_warmup()` cuando `warmup = true`.

  Debe pasar T009.
- [X] T017 [P] Implementar `stt/__main__.py` con `--check`:
  - imprime estado, modelo, `load_ms`;
  - transcribe un clip sintético (Phonon si está disponible; si no, avisa y transcribe un clip de silencio);
  - código de salida 0 si `ready`.

  Dejar los subcomandos `eval` y `transcribe ARCHIVO.wav` como stubs que se completan en T040.
- [X] T018 [P] Agregar `getSttStatus()` y `transcribe(wav: Blob, threadId)` en `web/src/lib/api.ts`:
  - `transcribe` hace POST binario con `Content-Type: audio/wav`;
  - errores tipados con `code`.

  Agregar `SttStatus`, `SttResult` e `InputMeta` en `web/src/lib/types.ts`, y `input?: InputMeta | null` en el tipo del turno.

**Checkpoint**: `pytest tests/unit/stt tests/api/test_stt_api.py` en verde; `python -m proyecto_modelos_lenguaje.stt --check` muestra `ready` con el modelo real.

---

## Phase 3: User Story 1 - Dictar una pregunta y enviarla (Priority: P1) 🎯 MVP

**Goal**: pulsar el micrófono, hablar y obtener el texto en el campo del mensaje, editable y sin envío automático.

**Independent Test**: en modo demo y real, dictar cinco preguntas de la demo; el texto aparece en `chat-input`; editar una palabra y enviar; la respuesta es igual a la del texto escrito (spec, US1).

### Tests for User Story 1

- [X] T019 [P] [US1] Pruebas en `web/src/test/dictation.test.ts`:
  - `encodeWav16k`:
    - remuestrea 48000 → 16000 Hz, encabezado RIFF correcto, PCM16 mono;
    - 1 s a 48 kHz da 32044 bytes;
    - satura en ±1.
  - `EndpointDetector`:
    - con bloques de 20 ms, el ruido base de los primeros 300 ms fija el umbral (×3, mínimo fijo);
    - no termina antes de `min_speech_ms` de habla;
    - termina tras `silence_ms` de silencio posterior a la habla (`reason="silence"`);
    - termina en `max_seconds` (`reason="limit"`);
    - expone `level` de 0 a 100.
- [X] T020 [P] [US1] Pruebas en `web/src/test/MicButton.test.tsx`, con `getUserMedia`, `AudioContext` y `AudioWorkletNode` simulados y `fetch` falso:
  - el permiso se pide solo al primer clic (FR-002);
  - mientras escucha, `aria-pressed=true`, `mic-status` «Escuchando…» y `mic-cancel` visible;
  - segundo clic: `processing` y luego `onTranscript(text, meta)`;
  - `mic-cancel` y `visibilitychange` a `hidden` no llaman a `transcribe` (FR-005);
  - al empezar llama a `voice.stop()` (FR-013).
- [X] T021 [P] [US1] Pruebas en `web/src/test/ChatViewDictation.test.tsx`:
  - la transcripción llena `chat-input` vacío o se agrega con un espacio si ya había texto, sin enviar (FR-011);
  - al enviar, `streamChat` recibe `input = {source: "voice", audio_ms, stt_ms, edited}`, con `edited=true` si el texto cambió;
  - un mensaje escrito después no lleva `input`;
  - una segunda grabación descarta el resultado pendiente de la primera.
- [X] T022 [P] [US1] Pruebas en `tests/api/test_chat_input.py`:
  - `POST /api/chat` y `/api/chat/stream` (modo demo) con `input` válido → el turno devuelto incluye `input` idéntico, y la ruta, la respuesta y las citas son iguales que sin `input` (FR-012);
  - `source="text"` o `audio_ms=-1` → 422;
  - sin `input` → `turn.input is None`;
  - `GET /api/threads/{id}` devuelve el `input` del turno;
  - el registro del contacto (`contact`) no cambia.

### Implementation for User Story 1

- [X] T023 [P] [US1] Crear `web/src/lib/dictation-worklet.ts`, un `AudioWorkletProcessor` (`dictation-capture`) que publica bloques `Float32Array` por `port.postMessage`. Registrarlo con `audioWorklet.addModule` usando una URL de módulo de Vite (`new URL("./dictation-worklet.ts", import.meta.url)`) y verificar que `npm run build` lo empaqueta.
- [X] T024 [US1] Implementar `web/src/lib/dictation.ts` (`encodeWav16k`, `EndpointDetector`, `DictationError` con `code` `permission | no_device | insecure | unsupported | unavailable | busy | too_long | empty | network | server`, y `ERROR_MESSAGES` en español textuales de U §3) para que pase T019.
- [X] T025 [US1] Implementar `web/src/lib/useDictation.ts` en modo normal, siguiendo DM §6:
  - estados `idle`, `requesting`, `listening`, `processing`, `ready` y `error`;
  - `getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}})`, `AudioContext` y el worklet;
  - detector de fin, `transcribe` y `onTranscript(text, meta)`;
  - cancelación por `cancel()` y `visibilitychange`;
  - descartar resultados de grabaciones anteriores (contador de generación);
  - liberar las pistas y cerrar el contexto al terminar;
  - recibe `voice: VoiceControl` y llama a `voice.stop()` al empezar.
- [X] T026 [US1] Crear `web/src/components/MicButton.tsx` (U §1): `mic-button` de al menos 44 × 44 px y `mic-cancel`. No se renderiza si `navigator.mediaDevices?.getUserMedia` falta o `!window.isSecureContext`. Estilos en el CSS del chat con la paleta existente. Debe pasar T020.
- [X] T027 [US1] Integrar en `web/src/components/ChatView.tsx`:
  - `MicButton` dentro de `console-form`, entre `chat-input` y `chat-send`;
  - `onTranscript` inserta el texto según U §2.3 y guarda `pendingInput` (meta y texto insertado);
  - `submit` pasa `input` a `streamChat`/`sendChat` (agregar `input?: InputMeta` a `SendChatInput` y al cuerpo en `web/src/lib/chat.ts`) solo si el mensaje proviene de una transcripción, con `edited` calculado;
  - limpiar `pendingInput` al enviar o al borrar el campo.

  Debe pasar T021.
- [X] T028 [US1] Backend del `input`:
  - `ChatRequest.input: InputMeta | None = None` y `TurnModel.input: InputMeta | None = None` en `api_models.py`;
  - pasar `payload.input` desde `api.py` (`chat`, `chat_stream`) a `ChatService.chat` y `open_stream` en `src/proyecto_modelos_lenguaje/agent/service.py`;
  - guardarlo en la entrada del turno del estado del hilo (la misma estructura que devuelve `getThread`) y devolverlo en el turno;
  - el grafo no lo lee.

  Debe pasar T022.

**Checkpoint**: US1 completa. Dictar → texto en el campo → enviar funciona en demo con `engine=fake` (pruebas) y con Whisper real (manual, quickstart §5.2–5.3).

---

## Phase 4: User Story 2 - Saber qué está pasando con el micrófono (Priority: P1)

**Goal**: estado visible (escuchando, nivel, procesando, preparando), errores claros en español y degradación sin STT.

**Independent Test**: permiso concedido, denegado, sin micrófono, silencio y servicio de STT apagado; en cada caso se ve el mensaje y el chat por texto sigue funcionando (spec, US2).

### Tests for User Story 2

- [X] T029 [P] [US2] Ampliar `web/src/test/MicButton.test.tsx`:
  - `mic-level` con `role="meter"` y `aria-valuenow` que sigue al detector;
  - `prefers-reduced-motion` sin animación;
  - `NotAllowedError` → mensaje `permission` de U §3;
  - `NotFoundError` → `no_device`;
  - respuesta `empty=true` → «No te entendí, ¿puedes repetirlo?» con el campo intacto;
  - 503 `stt_busy` → `busy`;
  - `fetch` rechazado → `network`;
  - límite → `too_long` con el texto insertado;
  - `GET /api/stt` con `available=false`: botón deshabilitado con `title` y `mic-status` = motivo;
  - `state="loading"`: «Preparando el micrófono…» y reintento del estado cada 3 s;
  - `mic-privacy` muestra `privacy`.
- [X] T030 [P] [US2] En `tests/api/test_stt_api.py`, agregar la prueba de **SC-008**: con `MANUELITA_STT_ENABLED=0`, `/api/chat/stream` y `/api/tts` responden igual que antes; `/api/health` → `stt_available=false` y `ok` sin cambios.

### Implementation for User Story 2

- [X] T031 [US2] Completar en `web/src/components/MicButton.tsx`:
  - `mic-level` (meter), `mic-status` (`aria-live="polite"`) y `mic-privacy`;
  - consultar `getSttStatus()` al montar y cada 3 s mientras esté `loading`;
  - deshabilitar con motivo si `available=false`;
  - mapear `DictationError.code` a `ERROR_MESSAGES`, mostrarlos en `mic-status` y limpiarlos a los 6 s o al siguiente clic.

  Debe pasar T029.
- [X] T032 [US2] En `web/src/lib/useDictation.ts`:
  - exponer `level` (0–100, a 15 fps como máximo) y `status`;
  - traducir excepciones de `getUserMedia` (`NotAllowedError` → `permission`, `NotFoundError`/`OverconstrainedError` → `no_device`, `SecurityError` → `insecure`) y códigos HTTP de A §2 a `DictationError`;
  - el campo de texto y `chat-send` nunca se deshabilitan por el estado del micrófono.

**Checkpoint**: US1 y US2 completas; es el MVP demostrable.

---

## Phase 5: User Story 3 - Conversación manos libres con Valer-IA (Priority: P2)

**Goal**: el mensaje se envía al terminar de hablar, el micrófono vuelve tras la respuesta, hablar encima la interrumpe y la voz de Valer-IA nunca se envía como mensaje.

**Independent Test**: cuatro turnos solo por voz con altavoces; cada mensaje se envía solo, la interrupción funciona y 0 ecos enviados (spec, US3; SC-005).

### Tests for User Story 3

- [X] T033 [P] [US3] Pruebas en `web/src/test/dictation.test.ts` de `echoSimilarity(transcript, spokenText)`:
  - normaliza minúsculas, tildes y puntuación, y quita etiquetas `[U1]`;
  - ratio de tokens comunes: > 0.6 para una transcripción parcial de lo dicho por Valer-IA y < 0.3 para una pregunta distinta;
  - `isEcho` usa el umbral 0.6.
- [X] T034 [P] [US3] Pruebas en `web/src/test/ChatViewDictation.test.tsx` (manos libres), con temporizadores falsos y `voice` simulado:
  - `mic-handsfree` activo → la transcripción se ve 400 ms en el campo y se envía con `input.handsfree=true` (FR-014);
  - el micrófono vuelve a `listening` cuando `voice.speaking` pasa de `true` a `false` tras la respuesta;
  - durante `voice.speaking`, un nivel ≥ 2× umbral durante 250 ms llama a `voice.stop()` y empieza a grabar;
  - una transcripción similar a la última respuesta hablada se descarta sin enviar (FR-015);
  - 60 s sin voz → manos libres se apaga (FR-016);
  - con una petición en curso, la transcripción espera a que termine antes de enviarse (nunca dos envíos simultáneos);
  - la preferencia se lee y guarda en `localStorage` `manuelita.stt.handsfree` con `try/catch` (FR-017).

### Implementation for User Story 3

- [X] T035 [US3] Agregar `echoSimilarity` e `isEcho` a `web/src/lib/dictation.ts` (pasa T033).
- [X] T036 [US3] Extender `web/src/lib/useDictation.ts` con el modo manos libres (DM §6, research R10):
  - `handsfree` y `setHandsfree` persistidos;
  - ciclo `waiting_reply → speaking → listening` observando `voice.speaking` y la respuesta en curso;
  - umbral de interrupción ×2 durante 250 ms mientras habla Valer-IA → `voice.stop()`;
  - guarda de eco con el texto de la última respuesta hablada (lo provee `ChatView`);
  - temporizador de inactividad `handsfree_idle_seconds` (de `GET /api/stt`);
  - el micrófono queda abierto entre turnos solo en manos libres.
- [X] T037 [US3] En `web/src/components/MicButton.tsx`, agregar `mic-handsfree` (`role="switch"`). En `ChatView.tsx`, enviar automáticamente en manos libres tras 400 ms con `input.handsfree=true`, encolar si hay una petición en curso y pasar a `useDictation` el texto hablado del último turno. Debe pasar T034.

**Checkpoint**: US1–US3 completas; conversación por voz en ambos sentidos.

---

## Phase 6: User Story 4 - Ver el reconocimiento en la vista técnica y evaluarlo (Priority: P3)

**Goal**: la línea «🎙 por voz» en la vista técnica (FR-022) y la evaluación reproducible del reconocimiento (FR-023).

**Independent Test**: dos mensajes dictados y uno escrito en `?vista=tecnica`: solo los dictados muestran origen, duración y reconocimiento; `stt eval` produce el informe con las metas (spec, US4).

### Tests for User Story 4

- [X] T038 [P] [US4] En `web/src/test/ChatViewDictation.test.tsx`:
  - con `technical`, un turno con `input` muestra `turn-input` dentro de `turn-trace`: «🎙 por voz · audio 2,0 s · reconocimiento 0,45 s», más «· editado» o «· manos libres»;
  - sin `technical`, o en un turno sin `input`, no aparece.
- [X] T039 [P] [US4] Pruebas en `tests/unit/stt/test_eval.py` (sin red, con `FakeTranscriber` y un sintetizador falso):
  - `normalize_for_wer` (minúsculas, tildes, puntuación, números a palabras en español: «2024» → «dos mil veinticuatro», «1-1» → «uno uno»);
  - `wer` (distancia de edición sobre tokens);
  - `vocab_hits` (aparición exacta de cada término esperado en la hipótesis normalizada sin tildes);
  - percentiles por tramo de duración (≤ 5 s, 5–10 s, > 10 s);
  - `empty_rate_on_silence`;
  - `targets`:
    - SC-001: WER ≤ 0.15;
    - SC-002: vocabulario ≥ 0.90;
    - SC-003: p90 < 2000 ms en clips ≤ 10 s;
    - SC-004: vacío = 1.0.
  - el informe JSON sigue DM §8 y el Markdown no tiene espacios al final de línea;
  - `--audio-dir` lee pares `nombre.wav` + `nombre.txt` y no publica la hipótesis sin `--include-human-text`.

### Implementation for User Story 4

- [X] T040 [US4] Implementar `src/proyecto_modelos_lenguaje/stt/eval.py`:
  - cargar `tests/fixtures/stt/phrases.jsonl`;
  - sintetizar cada frase con Phonon (`get_voice_service()`, voces `--voices`, por defecto Rebeca y una segunda voz del catálogo) y remuestrear a 16 kHz;
  - generar los clips de silencio y ruido con su semilla;
  - transcribir por modelo (`--models`, cada uno con su `SttService` aislado);
  - calcular métricas y `targets`;
  - escribir `docs/evaluacion_stt.{md,json}` (`--json-out`).

  Completar `stt/__main__.py` con `eval [--models] [--voices] [--audio-dir] [--include-human-text] [--json-out] [--export-sample]` (exit 1 si el modelo configurado no cumple los `targets`) y `transcribe ARCHIVO.wav`. Debe pasar T039.
- [X] T041 [US4] Agregar `turn-input` en `turn-trace` de `web/src/components/ChatView.tsx` (U §1), con formato `es-CO` de un decimal. Debe pasar T038.
- [X] T042 [P] [US4] Crear `tests/integration/stt/test_whisper_real.py` (marcador `voice`): con el modelo `base` real, «¿Qué produce Manuelita?» sintetizada con Phonon se transcribe con «Manuelita» bien escrita en menos de 2 s, y un silencio de 3 s da `empty`. Registrar el marcador en el docstring si hace falta, sin cambiar `addopts`.
- [X] T043 [US4] Ejecutar `uv run python -m proyecto_modelos_lenguaje.stt eval --models base small` con el modelo real. Guardar `docs/evaluacion_stt.{md,json}`. Si `base` no cumple SC-001 a SC-004, ajustar `config/stt.toml` (`model`, `vocabulary`, `corrections`, `no_speech_threshold`) y repetir; registrar los resultados en `research.md` §R2 (notas).

**Checkpoint**: todas las historias completas y medidas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T044 [P] Crear `tests/e2e/test_dictation.py` (requiere `PML_E2E=1`; ver `tests/e2e/conftest.py`):
  - Chrome con `--use-fake-ui-for-media-stream`, `--use-fake-device-for-media-stream` y `--use-file-for-fake-audio-capture=<wav>`;
  - el WAV se genera en `tmp_path` con `stt eval --export-sample` o con Phonon, y se borra al terminar;
  - con `MANUELITA_STT_ENGINE=fake`:
    - pulsar `mic-button` deja texto en `chat-input`;
    - `mic-cancel` no deja texto;
    - `?vista=tecnica` muestra `turn-input` tras enviar;
  - vista móvil de 375 px sin desborde.
- [X] T045 [P] Crear el ADR `docs/decisions/0027-dictado-local.md`:
  - contexto;
  - decisión (faster-whisper `base` int8 en el servidor, WAV 16 kHz, VAD, vocabulario, privacidad);
  - alternativas de R1 (Web Speech API, Vosk, `whisper.cpp`, nube);
  - consecuencias (+~50 MB de dependencias, modelo de 145 MB en la caché de Hugging Face, licencia MIT).
- [X] T046 Actualizar `CONSTITUTION.md` a v1.15.0 (encabezado, pie y registro de enmiendas):
  - §3.1: dictado con faster-whisper, modelo en la caché de Hugging Face, licencia MIT, ADR 0027;
  - §3.7: viñeta del micrófono (texto al campo, manos libres opcional, el chat y la voz siguen sin STT);
  - §10: el audio se procesa en memoria y no se guarda ni se registra, sin servicios de terceros.
- [X] T047 [P] Actualizar `README.md` (sección de voz: dictado, `config/stt.toml`, `stt --check`, `stt eval`) y `docs/demo.md` (guion de demostración con micrófono y manos libres, y qué hacer si el navegador niega el permiso).
- [X] T048 [P] Agregar la entrada del registro de cambios o de evaluación en `docs/prompt_log.md` (§3.20: STT sin prompts del LLM, con el `initial_prompt` del vocabulario y su SHA, y los resultados de T043), porque el vocabulario actúa como prompt del reconocedor.
- [X] T049 Ejecutar `UV_PROJECT_ENVIRONMENT=.venv make check` (ruff, pytest, vitest y build) y corregir lo que falle. Revisar que `npm run build` incluya el worklet y que `ruff format` no deje cambios.
- [X] T050 Recorrido visual con Playwright y Chrome en el puerto 8020 (nunca 8000), con audio falso:
  - vistas de visitante, técnica y móvil;
  - estados del micrófono (escuchando, procesando, error, deshabilitado con `MANUELITA_STT_ENABLED=0`);
  - sin errores de consola;
  - capturas en el scratchpad.
- [X] T051 Validar la privacidad según quickstart §6 (SC-006): sin `.wav`, `.webm` ni `.ogg` nuevos en el repositorio, `data/` ni el temporal; el registro `stt` sin texto. Recorrer quickstart §1–§7 y marcar lo verificado.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational.
- **US2 (Phase 4)**: depende de US1, porque extiende `MicButton` y `useDictation`. Juntas forman el MVP.
- **US3 (Phase 5)**: depende de US1 (`useDictation`) y usa los estados de US2.
- **US4 (Phase 6)**:
  - T038 y T041 dependen de US1 (T027, T028);
  - T039, T040, T042 y T043 solo dependen de Foundational y pueden avanzar en paralelo con US1–US3.
- **Polish (Phase 7)**: después de las historias deseadas; T049–T051 al final.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- Bibliotecas (`dictation.ts`) → hook (`useDictation.ts`) → componentes (`MicButton`, `ChatView`).
- Backend del `input` (T028) antes de la verificación de extremo a extremo.

### Parallel Opportunities

- **Setup**: T002, T003 y T004 en paralelo.
- **Foundational**: T005–T009 (pruebas) en paralelo; luego T011, T012, T013, T017 y T018 en paralelo (T010 antes de T014; T014 y T015 antes de T016).
- **US1**: T019–T022 en paralelo; T023 en paralelo con T024.
- **US4**: T039, T040 y T042 en paralelo con las fases web de US1–US3.
- **Polish**: T044, T045, T047 y T048 en paralelo.

---

## Parallel Example: Foundational

```text
Task: "T005 pruebas de configuración en tests/unit/stt/test_config.py"
Task: "T006 pruebas de WAV en tests/unit/stt/test_audio.py"
Task: "T007 pruebas de texto en tests/unit/stt/test_text.py"
Task: "T008 pruebas del motor en tests/unit/stt/test_engine.py"
Task: "T009 pruebas de contrato en tests/api/test_stt_api.py"
```

## Parallel Example: User Story 1

```text
Task: "T019 pruebas de encodeWav16k y EndpointDetector en web/src/test/dictation.test.ts"
Task: "T020 pruebas de MicButton en web/src/test/MicButton.test.tsx"
Task: "T021 pruebas de integración en web/src/test/ChatViewDictation.test.tsx"
Task: "T022 pruebas de input en tests/api/test_chat_input.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 (Setup) y Phase 2 (Foundational): el motor y la API funcionan; `stt --check` en `ready`.
2. Phase 3 (US1): dictar al campo y enviar.
3. Phase 4 (US2): estados y errores. **Parar y validar** con quickstart §5.1–5.4 y §5.7: es el MVP demostrable.

### Incremental Delivery

1. MVP (US1 + US2) → demo «hablarle a Valer-IA».
2. Evaluación (T039, T040, T043) en paralelo, para fijar el modelo con datos antes de afinar la interfaz.
3. US3 (manos libres) → conversación por voz en ambos sentidos.
4. US4 (traza) y Polish (ADR, Constitución, documentación, `make check`, recorrido visual y privacidad).

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- El audio nunca toca el disco en el código de producción. Las pruebas pueden escribir WAV solo en `tmp_path`.
- El registro `stt` nunca contiene texto reconocido.
- No commitear; la autoría es del equipo (`CONSTITUTION.md` §4.3).
- No tocar el servidor del puerto 8000; las pruebas visuales usan el 8020.
- La Constitución (v1.15.0) y el ADR 0027 van en el mismo commit que la funcionalidad.

## Notas de implementación (2026-11-23)

- **Worklet**: el procesador de captura se registra desde una URL `blob:` con su código como texto
  (`web/src/lib/dictation-worklet.ts`), no con `new URL(..., import.meta.url)`. Así funciona igual en desarrollo,
  en `web/dist` y en las pruebas, sin depender de cómo Vite empaquete los worklets.
- **Guarda de eco**: compara **pares de palabras seguidas** sin palabras funcionales, no palabras sueltas.
  Con palabras sueltas, «¿Qué produce Manuelita?» se descartaba como eco de «Manuelita produce azúcar…».
- **Manos libres**: además de `busy` y `speaking`, `ChatView` pasa un contador de respuestas (`replies`). Una
  respuesta muy rápida puede no dejar ver nunca `busy = true`. Si no llega respuesta, un temporizador de 3 s
  vuelve a escuchar. En una interrupción, el detector arranca con la voz que ya se oyó (`EndpointDetector.seed`).
- **Alucinaciones cortas**: «¡Gracias por ver!» y similares se descartan comparando el texto completo
  (`STT_HALLUCINATIONS`). «gracias» a secas sigue siendo un mensaje válido.
- **Pruebas**: `tests/conftest.py` fuerza también `MANUELITA_STT_ENGINE=fake`, y el servidor de E2E usa
  `PML_E2E_STT_ENGINE` (por defecto `fake`).
- **Batería**: se agregaron 4 frases largas (`l01`–`l04`, de 8,7 a 13 s) para medir los tramos de 5–10 s y de más de
  10 s; la síntesis de Phonon dejaba todas las demás por debajo de 5 s.
- **T043**: una corrida con la CPU ocupada en paralelo duplicó la latencia. El informe publicado es de una corrida
  sin carga: `base`, con WER 0,048, vocabulario 97 % y p90 de 1,07 s, cumple SC-001 a SC-004.
- **T044**: las 3 pruebas E2E del dictado pasan. En la suite E2E completa fallan 2 pruebas de `test_chat.py`, de
  la spec 014, que buscan la ruta y la tarjeta de aprobación en la vista de visitante. Desde la spec 018 esos
  elementos solo se muestran en `?vista=tecnica`: es un fallo previo, ajeno a esta spec, y la suite E2E no corre
  en CI.
- **T050**: el recorrido en el puerto 8020 usó el modelo real y Chrome con un micrófono simulado que dice
  «¿Qué produce Manuelita?» con la voz de Phonon:
  - la transcripción fue exacta en las vistas de visitante y técnica;
  - la traza muestra «🎙 por voz · audio 3,2 s · reconocimiento 0,69 s»;
  - móvil sin desborde;
  - con `MANUELITA_STT_ENABLED=0`, el botón queda deshabilitado con su motivo y el chat por texto funciona;
  - 0 errores de consola.
