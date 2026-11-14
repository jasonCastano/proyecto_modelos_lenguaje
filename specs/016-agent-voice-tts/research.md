# Research: Voz del agente en español con Phonon (spec 016)

Fecha: 2026-11-14. Fuentes: [gradium/phonon-40m-es](https://huggingface.co/gradium/phonon-40m-es),
[gradium/phonon-voices](https://huggingface.co/gradium/phonon-voices), [ptts en PyPI](https://pypi.org/project/ptts/)
(v0.7.1), [gradium-ai/xn-ptts](https://github.com/gradium-ai/xn-ptts). Verificación local: equipo de desarrollo con
Intel Core i9-12900H (AVX2), Windows 11, Python 3.14.

## R1. Dónde se sintetiza: servidor (Python) o navegador (WASM)

- **Decision**: síntesis en el **servidor** con el paquete Python `ptts` y un endpoint `POST /api/tts` que devuelve
  el audio de una oración.
- **Rationale**:
  - El paquete npm `phonon-tts` solo carga el modelo de 31M (inglés) desde Hugging Face; el modelo en español
    `phonon-40m-es` habría que servirlo nosotros, y su licencia CC BY-NC y el acceso con aceptación de condiciones
    complican redistribuirlo al navegador.
  - En el servidor el modelo se descarga una vez a la caché de Hugging Face (fuera del repositorio, FR-012) con el
    token local, igual que la clave de DeepSeek: nada sale del servidor (FR-011).
  - Encaja con la arquitectura actual (FastAPI expone todo, la SPA solo consume) y se prueba con pytest con un
    sintetizador simulado (FR-013).
  - `ptts` es Rust con enlace Python: **sin PyTorch**, una sola dependencia (`numpy`, ya presente) y ruedas
    `cp39-abi3` para Windows/Linux/macOS, compatibles con Python 3.14.
- **Alternatives considered**:
  - WASM en el navegador: menos carga del servidor, pero problemas de licencia/distribución y del modelo no
    soportado por el paquete npm. Rechazada.
  - Ruta Transformers (`GradiumPhononTTSForConditionalGeneration`): exige PyTorch (cientos de MB) y Transformers
    desde git. Rechazada por simplicidad (Principio V).
  - Servidor WebSocket u OpenAI-compatible de Phonon en Docker: un servicio más que operar. Rechazada.
  - Voz del navegador (`speechSynthesis`) como respaldo: no es Phonon y la voz depende del sistema operativo.
    Rechazada; si Phonon no está disponible, el chat sigue solo por texto (FR-009).

## R2. Cómo se logra el «tiempo real»: oraciones mientras llega el streaming

- **Decision**: el navegador acumula los eventos `token` del streaming SSE existente (`/api/chat/stream`), corta
  **oraciones completas** con un segmentador incremental y pide cada oración a `/api/tts` en orden, con hasta 2
  peticiones adelantadas; reproduce la cola con Web Audio, una oración detrás de otra.
- **Rationale**:
  - El modelo de lenguaje produce texto más lento de lo que Phonon lo sintetiza (proveedor: ~20× tiempo real en un
    núcleo de CPU, primer audio en ~10 ms en Apple; en x86 esperamos el mismo orden), así que una oración de ~3 s de
    audio se sintetiza en ~0,15–0,3 s: la voz empieza en cuanto se cierra la primera oración (SC-001 < 1,5 s).
  - Sintetizar por oración da prosodia natural (el modelo entona la oración completa) y permite detener, saltar y
    volver a escuchar con granularidad simple.
  - Desacopla la voz del contrato del chat: `/api/chat/stream` no cambia y la voz falla sin afectar el turno (FR-009).
- **Alternatives considered**:
  - Mezclar audio en el mismo SSE del chat: acopla dos fallas, obliga a base64 y complica las pruebas existentes.
    Rechazada.
  - Esperar la respuesta final y leerla completa: incumple «en tiempo real». Rechazada.
  - Streaming de audio dentro de la oración (`tts.stream`, tramas de 80 ms): mejora poco la latencia con oraciones
    cortas y complica la reproducción en el navegador. Se deja como mejora futura; el motor lo soporta.

## R3. Qué texto se lee y qué pasa si la respuesta final cambia

- **Decision**:
  - El navegador corta oraciones; el **servidor limpia** cada oración antes de sintetizar
    (`voice/text.py: clean_for_speech`): quita citas `[U#]`, la marca `[instrucción embebida omitida]`, Markdown
    (`**`, `#`, viñetas, enlaces → solo el texto del enlace), URLs y símbolos; normaliza `%` → «por ciento» y
    espacios. Si no queda texto pronunciable responde `204`.
  - Al llegar el evento `done`, el navegador compara la respuesta final validada con el texto del streaming. Si
    coinciden (normalizadas), termina de leer lo que falta. Si **no coinciden** (respuesta descartada por fuga del
    prompt, respaldo sin evidencia, aprobación pendiente), **detiene** la cola y lee la respuesta final.
- **Rationale**: el servidor es la única autoridad de limpieza (probada en pytest, igual para el botón «Escuchar»).
  La comparación final garantiza que la voz termina diciendo lo mismo que el turno guardado; el audio nunca dice más
  que lo que ya se mostró en pantalla en el streaming.
- **Alternatives considered**: esperar a `done` antes de hablar (pierde el tiempo real); limpiar en el navegador
  (duplica reglas en dos lenguajes). Rechazadas.

## R4. Voz por defecto

- **Decision final (2026-11-14, T037)**: la voz oficial del agente es **Rebeca** (`Sx8m6WdXBG06zwZT`, español
  de México, femenina). El equipo la eligió después de escuchar las 13 muestras.
- **Decision inicial**: voz femenina del catálogo de **español de México**; valor provisional `Ximena`, configurable en
  `config/voice.toml`. Durante la implementación se escuchan las 6 voces femeninas de México y las 7 de España con
  una respuesta típica del agente y el equipo fija la definitiva (tarea explícita).
- **Rationale**: la spec pide voz femenina en español; el acento latinoamericano es el más cercano al público
  colombiano. El motor resuelve la voz por nombre o identificador del catálogo.
- **Catálogo femenino**: España: Noa, Lucía-Sol, Candela, Celia, Alba, Alicia, Nerea. México: Rebeca, Regina, Danae,
  Azucena, Jimena, Ximena.
- **Alternatives considered**: la voz del ejemplo oficial (`Iker`, masculina, España) — incumple la preferencia.

## R5. Disponibilidad, carga y concurrencia del motor

- **Decision**:
  - `ptts` entra como dependencia normal del proyecto (rueda pequeña, sin PyTorch).
  - El modelo se carga **perezosamente** en un singleton protegido por un `Lock`, con precalentamiento opcional en un
    hilo al arrancar la app (`voice.warmup = true`), para que la primera oración no pague la carga.
  - Si `ptts` no importa, el modelo no se puede descargar (falta `HF_TOKEN` o no se aceptaron las condiciones), la
    CPU no es compatible o `voice.enabled = false`, el estado es **no disponible** con un motivo legible;
    `/api/tts` responde `503 voice_unavailable` y la UI deshabilita la voz (FR-009, FR-010).
  - La síntesis se serializa con el `Lock` (no se documenta que el objeto sea seguro entre hilos); con oraciones de
    ~0,2 s eso alcanza para la demo con pocos usuarios.
- **Rationale**: el chat nunca depende de la voz; la falla es explícita y diagnosticable con
  `python -m proyecto_modelos_lenguaje.voice --check`.
- **Alternatives considered**: dependencia opcional (extra `voice`): obliga a dos caminos de instalación y a que la
  CI no ejercite la importación. Rechazada.

## R6. Formato de audio

- **Decision**: `audio/wav` PCM 16 bits mono a la frecuencia del modelo (24 kHz), una respuesta HTTP por oración.
- **Rationale**: `AudioContext.decodeAudioData` lo decodifica en todos los navegadores sin librerías; una oración
  pesa ~48 KB por segundo de audio, irrelevante en local. Escribir el WAV con la librería estándar (`wave`) desde el
  arreglo `float32` evita dependencias.
- **Alternatives considered**: Opus/MP3 (necesita codificador), PCM crudo por chunks (necesita AudioWorklet). Rechazadas.

## R7. Pruebas sin red ni modelo

- **Decision**:
  - `FakeSynthesizer` determinista (silencio o tono de duración proporcional al texto) inyectado por variable de
    entorno `MANUELITA_VOICE_ENGINE=fake` o por dependencia en las pruebas de la API.
  - Pruebas con el modelo real marcadas `@pytest.mark.voice` y excluidas por defecto (`addopts`), como `network`.
  - Vitest con `fetch` y `AudioContext` simulados para el segmentador, la cola y los controles.
- **Rationale**: SC-007 y la regla del proyecto: las pruebas unitarias y de contrato pasan sin red.

## R8. Observabilidad de la voz

- **Decision**: cada petición a `/api/tts` registra en `voice.jsonl` del directorio de estado
  (`MANUELITA_STATE_DIR`, el mismo de `turns.jsonl`): `thread_id`, índice de la oración, voz, caracteres,
  milisegundos de síntesis, duración del audio y error. El navegador envía `thread_id` y `segment` en la petición y
  mide el tiempo hasta el primer audio, que muestra en la traza del turno (`🔊 primer audio X s`).
- **Rationale**: FR-014 sin guardar audio ni texto completo; reutiliza el directorio de estado que ya está fuera de
  `data/` y del repositorio.
- **Alternatives considered**: trazas LangSmith (la voz no es una llamada al LLM; añadiría ruido). Rechazada.

## R9. Licencia y acceso

- **Decision**: documentar en ADR 0020 y en `CONSTITUTION.md` que los pesos y voces de `phonon-40m-es` son
  CC BY-NC 4.0 (uso académico no comercial) y que el motor `ptts` es MIT/Apache-2.0. `HF_TOKEN` se añade como
  variable opcional en `.env.example` (nunca versionada con valor).
- **Rationale**: FR-015 y la política de secretos del proyecto.

## R10. Verificación de la API real de `ptts` 0.7.1 (2026-11-14)

- `uv add "ptts>=0.7.1"` dejó `ptts` 0.7.1 en `pyproject.toml` y `uv.lock`, con rueda `cp39-abi3-win_amd64`
  compatible con Python 3.14. La instalación en `.venv` quedó pendiente por procesos `uv` huérfanos de esta sesión
  que retienen el bloqueo de la caché. Basta con `uv sync`.
- La API se inspeccionó importando la rueda descomprimida fuera del proyecto:
  - `TTS(model=None, device=None, quant=None, voice=None, temperature=0.3, seed=..., *, lang, ...)`.
  - `synth(text, *, voice=None, ...) -> np.ndarray float32`, `stream(text, *, voice=None, ...)`,
    `save(path, text, *, voice=None)`, `sample_rate` y `voices` (nombres registrados).
  - `ptts.catalog_voices()` devuelve `name`, `voice_id`, `language` y `description` sin descargar el modelo.
  - `ptts.available_quants()` devuelve `f32, q8_0, q8_1, q8k, q6k, q5_0, q5_1, q5k, q4_0, q4_1, q4k`.
  - `build_info()` reporta `avx: True` y 20 hilos en el equipo de desarrollo.
- **Ajustes al diseño**:
  - La cuantización por defecto pasa de `q8`, que no es válida, a `q8_0`.
  - El catálogo de voces se lee con `catalog_voices()`, filtrado a español.
  - El género sale de las fichas de las voces, porque el catálogo no lo trae.
- **Catálogo verificado**: 102 voces, 25 en español, con los mismos nombres e ID de R4.
- **Acceso condicionado confirmado**: sin `HF_TOKEN`, `TTS("hf://gradium/phonon-40m-es")` lanza
  `OSError ... Authentication required ... GatedRepo ... set HF_TOKEN`. `VoiceService` lo traduce a «falta
  HF_TOKEN o no se aceptaron las condiciones…».

### Rendimiento medido (2026-11-14) y ajuste del diseño

- Phonon ya caliente en el i9-12900H sintetiza a **~0,17 del tiempo real (unas 6×)**, no a las ~20× que
  reporta el proveedor en Apple M5: ~12 ms por carácter. El primer fragmento de `stream()` llega en ~50 ms.
- Con oraciones completas, una primera oración de ~200 caracteres tardaba ~2 s, y solo 7/10 preguntas cumplían
  SC-001.
- **Ajuste**: el segmentador limita **solo el primer segmento** de cada respuesta a 120 caracteres
  (`FIRST_SEGMENT_CHARS`), cortando en una coma o en un espacio. Los siguientes no cambian, porque se
  sintetizan mientras suena el anterior (6× más rápido que el tiempo real). Resultado: 10/10 < 1,5 s.
- La precarga sintetiza «Hola.» después de cargar, porque la primera síntesis en frío es ~2× más lenta.
- Queda como mejora futura servir el audio de la primera oración en streaming (`tts.stream`) con un
  AudioWorklet, para bajar el primer audio a ~0,1 s.
