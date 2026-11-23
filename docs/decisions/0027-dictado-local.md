# ADR 0027 — Dictado por voz local con faster-whisper

- **Estado**: aceptada
- **Fecha**: 2026-11-23
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0020 (voz con Phonon), ADR 0021 (avatar local), ADR 0025 (entrega por frases);
  `specs/023-voice-input/` (spec, plan, research R1–R14, contratos, tasks).

## Contexto

Desde la spec 016, Valer-IA Caña habla: lee sus respuestas en voz alta, frase por frase, con el avatar moviendo la
boca. El visitante, en cambio, solo podía escribir. La spec 023 pide que pueda hablarle con el micrófono. Esa voz
debe convertirse en texto en español y entrar al mismo chat, con las mismas reglas, revisiones y citas.

Restricciones:
- el audio del visitante es un dato personal y no debe salir a terceros (§10);
- el dictado debe funcionar en modo demo, sin la clave de DeepSeek;
- las pruebas deben correr sin red (§3.8);
- el equipo de la sustentación solo tiene CPU.

## Decisión

1. **Reconocimiento en el servidor** con `faster-whisper` 1.2.1 (CTranslate2, CPU, `int8`). Ya era una extra
   opcional del proyecto (`asr`, para transcribir videos de la capa bronce) y pasa a dependencia de runtime junto
   con `av`.
2. **Modelo `base`**, con `beam_size = 1` y Silero VAD (`vad_filter`). El vocabulario propio (Manuelita, Valer-IA
   Caña, Océanos, …) se pasa como prompt inicial y se aplican correcciones deterministas de la grafía de la marca.
   `small` queda como opción en `config/stt.toml`.
3. **Captura en el navegador**:
   - `getUserMedia` con cancelación de eco, supresión de ruido y control de ganancia, más un `AudioWorklet` que
     entrega bloques de 20 ms;
   - el fin de habla se detecta por energía (1,5 s de silencio tras hablar);
   - el cliente envía **WAV PCM16 mono a 16 kHz** a `POST /api/stt`: un único formato sin códec, en vez de los
     contenedores de `MediaRecorder`, que cambian según el navegador.
4. **Privacidad**:
   - el audio se procesa en memoria (`io.BytesIO` → `numpy`) y se descarta;
   - el registro `stt.jsonl` guarda tiempos y tamaños, nunca texto;
   - la interfaz lo dice junto al micrófono.
5. **Integración**:
   - el texto dictado es un mensaje normal: en modo normal va al campo para revisarlo, y en manos libres se envía
     solo;
   - `ChatRequest.input` lleva solo metadatos (origen, duración, tiempo de reconocimiento) para la vista técnica;
   - el grafo no lo lee.
6. **Manos libres**:
   - el micrófono queda abierto;
   - hablar encima de Valer-IA la interrumpe (umbral ×2 durante 250 ms);
   - una guarda de eco descarta transcripciones que repiten pares de palabras de su última respuesta;
   - el modo se apaga tras un minuto sin voz.

## Alternativas descartadas

- **Web Speech API del navegador**: en Chrome y Edge envía el audio a servicios de Google o Microsoft, Firefox no la
  soporta y no se puede evaluar de forma reproducible.
- **Whisper con PyTorch / `transformers`**: la spec 016 ya descartó PyTorch por peso y arranque; no mejora la
  calidad a igual modelo.
- **Vosk / Kaldi**: más liviano, pero con peor puntuación y peores nombres propios.
- **`whisper.cpp`**: velocidad comparable, pero sin VAD integrado ni ruedas fiables para Python 3.14 en Windows.
- **Servicios en la nube** (Deepgram, OpenAI): envían el audio a terceros y agregan otra clave.
- **`large-v3-turbo`**: WER 0.079 frente a 0.055 de `base` con vocabulario en el banco inicial, pero tarda 5,8 s por
  frase en CPU.

## Consecuencias

- Unos 50 MB más de dependencias (CTranslate2 y PyAV). El modelo `base` (~145 MB) se descarga a la caché de Hugging
  Face la primera vez, sin `HF_TOKEN`, y nunca al repositorio. Licencias MIT (motor, pesos de Whisper y Silero VAD).
- El servidor precarga el modelo en segundo plano al arrancar. La interfaz muestra «Preparando el micrófono…»
  mientras carga, y el botón queda deshabilitado, con su motivo, si el dictado no está disponible. El chat y la voz
  de salida no dependen del dictado.
- La evaluación (`python -m proyecto_modelos_lenguaje.stt eval`) sintetiza la batería con Phonon en cada corrida:
  no se versiona audio. Las grabaciones humanas son opcionales y locales.
- Las pruebas usan el motor `fake`. Las del modelo real llevan el marcador `voice`.
- Los navegadores solo permiten el micrófono por `localhost` o HTTPS: un despliegue remoto necesita TLS.
