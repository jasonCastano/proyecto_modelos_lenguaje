# ADR 0020 — Voz del agente con Phonon

- **Estado**: aceptada
- **Fecha**: 2026-11-14
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0016 (agente con LangGraph), ADR 0019 (blindaje); `specs/016-agent-voice-tts/` (spec, plan,
  research R1–R10, tasks).

## Contexto

El equipo pidió que el agente tenga voz: en español, preferiblemente femenina, y que la respuesta se escuche **en
tiempo real** mientras se genera en el chat. El motor solicitado es **Phonon** (Gradium): un modelo de síntesis de
voz de unos 40M de parámetros que corre en CPU y tiene un modelo en español (`gradium/phonon-40m-es`) con 13 voces
femeninas.

El chat ya entrega la respuesta por streaming SSE (`/api/chat/stream`). La voz no debía cambiar ese contrato, ni el
grafo del agente, ni romper el chat si falla.

## Decisión

1. **Síntesis en el servidor con `ptts`**, el runtime oficial de Phonon en Rust con enlace Python:
   - No necesita PyTorch y solo depende de `numpy`, que ya estaba en el proyecto.
   - El modelo (~75 MB, q8) se descarga una vez a la caché de Hugging Face con `HF_TOKEN`, fuera del repositorio.
2. **Por oraciones sobre el streaming existente**:
   - El navegador corta en oraciones el texto que llega por SSE y pide cada una a `POST /api/tts`, con hasta dos
     peticiones adelantadas.
   - Reproduce las oraciones en orden con Web Audio, mientras la respuesta se sigue generando.
3. **El servidor limpia el texto** antes de sintetizar (`voice/text.py`): quita citas `[U#]`, la marca de oración
   neutralizada, Markdown y URLs. La voz nunca lee marcas internas ni el contenido de los documentos recuperados.
4. **Corrección con la respuesta final**: si la respuesta validada del turno difiere de lo recibido por streaming
   (respuesta descartada, respaldo sin evidencia o ruta clásica), la voz se corta y lee la respuesta final.
5. **Degradación segura**:
   - `VoiceService` tiene un estado explícito (`disabled|loading|ready|unavailable`) y carga el modelo de forma
     perezosa, con precarga en un hilo al arrancar.
   - Sin motor, `/api/tts` responde `503 voice_unavailable`, y `GET /api/voice` y `/api/health` lo informan.
   - La interfaz muestra un aviso y el chat sigue por texto.
6. **Pruebas sin red**: un `FakeSynthesizer` determinista cubre la suite y la CI. Las pruebas con el modelo real se
   marcan `voice` y quedan fuera por defecto.
7. **Voz oficial**: **Rebeca** (`Sx8m6WdXBG06zwZT`), femenina, del catálogo de español de México. El equipo la
   eligió el 2026-11-14 después de escuchar las 13 voces femeninas en español. Es configurable en
   `config/voice.toml` o con `MANUELITA_VOICE`.

## Alternativas consideradas

- **Phonon en el navegador (WASM, `phonon-tts`)**: rechazada. El paquete npm solo carga el modelo de 31M en inglés.
  Servir el modelo en español desde la app choca con su licencia no comercial y con el acceso condicionado.
- **Ruta Transformers (`GradiumPhononTTSForConditionalGeneration`)**: rechazada. Requiere PyTorch y Transformers
  desde git, cientos de MB para lo mismo.
- **Audio dentro del mismo SSE del chat**: rechazada. Acopla dos fallas, obliga a base64 y rompe el contrato y las
  pruebas existentes.
- **`speechSynthesis` del navegador como respaldo**: rechazada. No es Phonon y la voz depende del sistema operativo.
- **Leer solo al final de la respuesta**: rechazada. No cumple «en tiempo real».

## Consecuencias

- **Dependencia nueva**: `ptts`, justificada (Principio VII). Las ruedas cubren Windows, Linux y macOS; en x86-64
  se necesita una CPU con AVX2.
- **Licencia**: el modelo y las voces de `phonon-40m-es` son **CC BY-NC 4.0**, compatible con el uso académico del
  curso pero no con un uso comercial. El motor `ptts` es MIT/Apache-2.0.
- **Primera ejecución**: requiere aceptar las condiciones del modelo en Hugging Face y definir `HF_TOKEN` en `.env`.
  Sin eso, la voz queda «no disponible» con un motivo legible.
- **Registro**: cada oración sintetizada se registra en `MANUELITA_STATE_DIR/logs/voice.jsonl` con tiempos y sin
  texto. La traza del turno muestra el tiempo hasta el primer audio.
- **Limitación**: la síntesis se serializa con un `Lock`. Basta para la demo, pero varios usuarios simultáneos
  esperarían en cola.
