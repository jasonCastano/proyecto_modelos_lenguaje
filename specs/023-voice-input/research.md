# Research: Dictado por voz para Valer-IA Caña (spec 023)

**Fecha**: 2026-11-23 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Cada decisión sigue el formato *Decisión / Razón / Alternativas*. Las mediciones son de este equipo (20 hilos lógicos,
Windows 11, Python 3.14.7, sin GPU) con el script de banco descrito en R3.

## R1. Motor de reconocimiento: `faster-whisper` en el servidor

- **Decisión**: reconocer en el servidor con `faster-whisper` 1.2.1 (CTranslate2 4.8.4, CPU, `int8`). Pasa de la
  extra opcional `asr` a dependencia de runtime, junto con `av`.
- **Razón**:
  - Cumple FR-007: corre local, sin terceros, y no depende de la clave de DeepSeek, así que funciona en demo.
  - El proyecto ya lo usa para transcribir videos de la capa bronce (`transcription.py`, extra `asr`). `uv.lock` ya
    lo resuelve con ruedas `cp314` para Windows, Linux y macOS. No agrega una tecnología nueva, solo la promueve.
  - Trae Silero VAD integrado (ONNX, sobre `onnxruntime`, que ya es dependencia) para descartar silencio y ruido
    (FR-009).
  - Licencias: motor MIT, pesos de Whisper MIT y Silero VAD MIT, compatibles con el uso académico.
- **Alternativas**:
  - *Web Speech API del navegador*: en Chrome y Edge envía el audio a servicios de Google o Microsoft (incumple FR-007
    y la política de privacidad de la spec). Firefox no la soporta. No se puede evaluar de forma reproducible.
  - *Whisper con `transformers` o PyTorch*: la spec 016 descartó PyTorch por peso y tiempo de arranque; sin ventaja
    de calidad a igual modelo.
  - *Vosk / Kaldi*: más liviano, pero con peor puntuación y peor manejo de nombres propios. Requiere un modelo
    aparte por idioma.
  - *`whisper.cpp` (`pywhispercpp`)*: comparable en velocidad, pero sin VAD integrado ni ruedas `cp314` fiables
    en Windows.
  - *Servicios en la nube (Deepgram, OpenAI)*: incumplen FR-007 y agregan otra clave.

## R2. Modelo por defecto: `base` (int8) con vocabulario como `initial_prompt`

- **Decisión**: modelo `base` en `int8`, con `beam_size = 1`, `language = "es"`, `vad_filter = true`,
  `condition_on_previous_text = false` y el vocabulario propio como `initial_prompt` (R4). `small` queda como
  opción configurable para equipos más rápidos.
- **Razón**: banco con seis frases de demo sintetizadas con Phonon (2.0–6.6 s), más un silencio con ruido:

  | Modelo | Carga (en caché) | Latencia p50 / máx | WER sin vocabulario | WER con vocabulario | Silencio |
  |---|---|---|---|---|---|
  | `base` | ~1 s (19 s con descarga) | 0.45 / 0.46 s | 0.309 | **0.055** | vacío |
  | `small` | 1.2 s | 1.60 / 1.69 s | 0.245 | 0.123 | vacío |
  | `large-v3-turbo` | 144 s con descarga | 5.9 / 6.2 s | 0.079 | 0.079 | vacío |

  - `base` con vocabulario escribe bien «Océanos», «Mejillones América», «Fundación Manuelita» y «Educar uno a
    uno», y deja mucho margen para SC-003 (< 2 s para 10 s de habla).
  - `small` se acerca al límite de 2 s con intervenciones largas.
  - `large-v3-turbo` es inviable en CPU.
- **Advertencia**: la voz sintética es más limpia que una voz humana con micrófono de portátil. La evaluación
  (R11) mide además grabaciones humanas opcionales. Si `base` no cumple SC-001 con ellas, se cambia a `small` en
  la configuración, sin tocar código.
- **Alternativas**: `tiny` (más rápido pero mucho peor en español); `distil-whisper` (solo inglés para las variantes
  pequeñas).
- **Notas (T043, 2026-11-23)**: la batería completa tiene 44 frases × 2 voces de Phonon, más 6 silencios y
  ruidos (`docs/evaluacion_stt.md`):
  - `base`: WER 0,048, vocabulario 97 %, p90 de 1,07 s en clips de hasta 10 s y 100 % de vacío; cumple SC-001 a
    SC-004 y queda como modelo configurado;
  - `small`: WER 0,027 y vocabulario 100 %, pero p90 de 2,9 s (no cumple SC-003).

## R3. Banco y evaluación sin guardar audio

- **Decisión**: la batería de evaluación se **genera** en cada corrida con Phonon a partir de frases versionadas en
  `tests/fixtures/stt/phrases.jsonl`, más clips de silencio y ruido generados con semilla. Las grabaciones humanas
  son opcionales: viven en un directorio local fuera del repositorio (`--audio-dir`) y no se versionan.
- **Razón**:
  - Reproducible (principio I).
  - Sin archivos de audio en el repositorio ni datos de voz de personas (FR-018, §10 de la Constitución).
  - Cubre el vocabulario propio con control exacto de la referencia.
- **Alternativas**:
  - *Versionar WAV grabados por el equipo*: datos biométricos en un repositorio público; descartado.
  - *Common Voice*: pesado, licencia de atribución por clip y sin el vocabulario de Manuelita.

## R4. Vocabulario propio

- **Decisión**: lista en `config/stt.toml` (`vocabulary`) que se une como `initial_prompt` («Manuelita, Valer-IA
  Caña, Palmira, …»). Se complementa con una corrección determinista posterior, `stt/text.py`, para variantes
  frecuentes (`valeria caña` → `Valer-IA Caña`, `manuelita` → `Manuelita`) definidas en la misma lista. Solo se
  corrigen palabras completas y sin distinguir mayúsculas.
- **Razón**: el prompt bajó el WER de 0.309 a 0.055 con `base`. La corrección garantiza la grafía de la marca de la
  asistente, que Whisper no puede inferir («Valer-IA»).
- **Alternativas**: el parámetro `hotwords` de faster-whisper (útil con `beam_size > 1`, más lento); ajuste fino del
  modelo (fuera de alcance).

## R5. Captura en el navegador: PCM 16 kHz en WAV, no `MediaRecorder`

- **Decisión**: capturar con `getUserMedia({ audio: { echoCancellation, noiseSuppression, autoGainControl } })` y un
  `AudioWorklet` que entrega muestras `Float32`. Al terminar, el cliente remuestrea a 16 kHz mono PCM16 y lo envía
  como `audio/wav`.
- **Razón**:
  - Formato único y sin códec. El servidor lo decodifica con la biblioteca estándar y `numpy`, sin depender de
    PyAV en la ruta caliente.
  - Firefox y Chrome difieren en los contenedores de `MediaRecorder` (ogg y webm).
  - El mismo flujo de muestras alimenta el medidor de nivel y el detector de fin de habla (R6).
  - 60 s × 16 kHz × 2 B ≈ 1.9 MB por grabación: aceptable en local.
- **Alternativas**: `MediaRecorder` con Opus (menos bytes, pero dos contenedores y decodificación con PyAV);
  streaming por WebSocket con resultados parciales (más complejidad; Whisper no es nativamente incremental).

## R6. Fin de habla y nivel: detector de energía en el cliente, VAD en el servidor

- **Decisión**:
  - El cliente calcula el RMS por bloques de 20 ms. Marca habla cuando el RMS supera un umbral adaptativo (ruido de
    fondo medido en los primeros 300 ms × 3, con un mínimo fijo). Termina tras `silence_ms = 1500` de silencio
    después de haber detectado al menos `min_speech_ms = 300` de habla, o al llegar a `max_seconds = 60`.
  - El servidor aplica Silero VAD (`vad_filter`) y descarta los segmentos con `no_speech_prob > 0.6`, o cuyo texto
    coincide con alucinaciones conocidas de Whisper (`transcription.is_noise`: «Subtítulos realizados por…»,
    «Gracias por ver…»).
  - Si no queda texto, la respuesta es `empty = true` (FR-009, SC-004).
- **Razón**: la detección en el cliente da respuesta inmediata en la interfaz y no requiere enviar audio continuo.
  El VAD del servidor es la garantía contra el texto inventado.
- **Alternativas**: Silero VAD en el navegador con `onnxruntime-web` (otro modelo de 2 MB y WASM; posible mejora
  futura); fin solo manual (peor experiencia en manos libres).

## R7. API: `POST /api/stt` sincrónico, con un único modelo compartido

- **Decisión**:
  - `POST /api/stt` recibe el WAV en el cuerpo (`Content-Type: audio/wav`, máximo 2 MB y 60 s) y responde JSON con
    `text`, `empty`, `audio_ms`, `stt_ms`, `model` y `truncated`.
  - `GET /api/stt` expone el estado (`available`, `state`, `model`, `detail`). `/api/health` agrega `stt_available`.
  - El modelo se carga una vez (`SttService`, análogo a `VoiceService`), con precalentamiento opcional en segundo
    plano al arrancar, y un semáforo limita las transcripciones simultáneas (`max_concurrent = 2`). El resto espera
    con tiempo límite (`queue_timeout_seconds`) y responde `503 stt_busy`.
- **Razón**:
  - Es la forma de `/api/tts`, que el equipo ya conoce.
  - Las intervenciones son cortas y la latencia total es menor que la del modelo de lenguaje.
  - CTranslate2 usa varios hilos por transcripción; limitar la concurrencia evita degradar a todos.
- **Alternativas**: WebSocket con parciales (R5); cola asíncrona con trabajos (innecesaria a esta escala).

## R8. Privacidad: el audio nunca toca el disco

- **Decisión**:
  - El cuerpo se lee a memoria (`bytes`), se decodifica a `numpy` y se pasa a `WhisperModel.transcribe` como
    arreglo. No hay archivos temporales.
  - Los registros (`stt/log.py`, análogo a `voice/log.py`) guardan solo duración, tiempos, tamaño, modelo, estado y
    número de caracteres, nunca el texto ni el audio.
  - La traza de LangSmith no recibe el audio: el endpoint no está instrumentado y el texto entra a LangChain como
    cualquier mensaje.
  - Una prueba verifica que una transcripción no crea archivos en el directorio de trabajo ni en el temporal
    (SC-006).
- **Razón**: FR-018, FR-019 y §10 de la Constitución.
- **Alternativas**: archivos temporales con borrado (riesgo de residuos si el proceso cae).

## R9. Integración con el chat: el texto dictado es un mensaje normal, con metadatos de entrada

- **Decisión**:
  - El cliente pone la transcripción en el campo del mensaje (modo normal) o la envía directamente (manos libres).
  - `ChatRequest` gana el campo opcional `input: { source: "voice", audio_ms, stt_ms, edited }`. El servidor lo
    valida y lo copia a `TurnModel.input` y a la entrada del turno en el estado del hilo, para la vista técnica (US4,
    FR-022), sin que afecte el enrutamiento, la revisión ni el registro del contacto (FR-012).
  - El registro del contacto no guarda nada nuevo: §3.7 limita sus etiquetas.
- **Razón**: un único camino para todos los mensajes; el agente no distingue entre voz y texto, así que las
  garantías de las specs 018–022 se mantienen sin cambios.
- **Alternativas**: un endpoint `/api/chat/voice` que reciba audio y responda (duplicaría el flujo de chat y la
  lógica de streaming); mostrar los datos técnicos solo desde el estado del cliente (se pierden al recargar el hilo).

## R10. Manos libres: conmutación por turnos, cancelación de eco y guarda de eco

- **Decisión**: máquina de estados en el cliente (`useDictation`):
  - Ciclo `idle → listening → processing → sent → waiting_reply → speaking → listening`.
  - Mientras Valer-IA habla, el micrófono sigue abierto, con cancelación de eco del navegador y un umbral de
    interrupción más alto (×2 el de habla durante 250 ms seguidos). Si se supera, se llama a `voice.stop()` y se
    empieza a grabar (FR-013, FR-014).
  - **Guarda de eco**: antes de enviar en manos libres, si la transcripción se parece en más de 0.6 (tokens
    normalizados) a lo que Valer-IA dijo en ese turno, se descarta en silencio (FR-015, SC-005).
  - Apagado tras 60 s sin voz del visitante (FR-016).
  - La preferencia se guarda en `localStorage` (`manuelita.stt.handsfree`).
- **Razón**: la cancelación de eco del navegador elimina la mayor parte de la voz de los altavoces. La guarda cubre
  los restos, sobre todo en portátiles con altavoces fuertes.
- **Alternativas**: cerrar el micrófono mientras ella habla (impide interrumpirla, que es parte de US3).

## R11. Evaluación: `python -m proyecto_modelos_lenguaje.stt eval`

- **Decisión**:
  - Frases (unas 40) en `tests/fixtures/stt/phrases.jsonl`, de 1 a 12 s, con preguntas de demo, charla, números y
    nombres del vocabulario, más 6 clips de silencio y ruido.
  - Se sintetizan con dos voces de Phonon y se mide:
    - WER, con normalización de minúsculas, tildes, puntuación y números («2024» ≡ «dos mil veinticuatro»);
    - acierto de nombres del vocabulario (SC-002);
    - latencia p50/p90 por tramo de duración (SC-003);
    - tasa de vacío en silencio y ruido (SC-004).
  - Informe en `docs/evaluacion_stt.{md,json}`, con modelo, cuantización y configuración.
  - `--audio-dir` agrega grabaciones humanas (`nombre.wav` + `nombre.txt`) no versionadas.
  - `--models base small` compara modelos (principio II: línea base).
- **Razón**: FR-023 y principios I y II de la Constitución.

## R12. Pruebas sin red ni modelo

- **Decisión**:
  - `engine = "fake"` (`FakeTranscriber`): devuelve el texto de un encabezado de prueba o una frase fija según la
    energía del audio; silencio → vacío.
  - Las pruebas con el modelo real llevan el marcador `voice` (excluido por defecto y en CI, como las de Phonon).
  - Vitest simula `getUserMedia`, el `AudioWorklet` y `fetch`.
  - Playwright usa el flag de Chrome `--use-fake-device-for-media-stream` con un WAV generado (`--use-file-for-fake-audio-capture`).
- **Razón**: la Constitución exige que las pruebas unitarias y de contrato pasen sin red (§3.8).

## R13. Disponibilidad y degradación

- **Decisión**:
  - Si `[stt] enabled = false`, falta el modelo o falla la carga, `GET /api/stt` devuelve `available = false` con un
    motivo legible. La interfaz oculta el micrófono (navegador sin soporte) o lo deshabilita con el motivo
    (servidor sin STT) (FR-020).
  - La descarga del modelo (~145 MB para `base`) va a la caché de Hugging Face, como Phonon; nunca al repositorio.
  - El modelo es público: no requiere `HF_TOKEN`.
- **Razón**: SC-008. La voz de salida y el chat no deben depender del dictado.

## R14. Entorno de `uv`

- **Observación**: en algunos equipos, `UV_PROJECT_ENVIRONMENT` apunta a un entorno fuera del repositorio, y
  `make check` usa `UV_PROJECT_ENVIRONMENT=.venv`. El paquete debe estar instalado en el entorno que usa cada
  comando.
- **Decisión**: al promover `faster-whisper` y `av` a runtime, `uv sync` los instala en el entorno activo. La
  `quickstart` indica sincronizar el entorno de la aplicación y el de `make check`.
