# Quickstart: validar el dictado por voz (spec 023)

Contratos: [stt-api.md](./contracts/stt-api.md) y [ui.md](./contracts/ui.md). Entidades: [data-model.md](./data-model.md).

## 0. Preparación

```bash
uv sync                                         # instala faster-whisper y av (ya en runtime)
UV_PROJECT_ENVIRONMENT=.venv uv sync            # si make check usa .venv y tu shell otro entorno
cd web && npm ci && cd ..
```

La primera carga descarga el modelo `base` (~145 MB) a la caché de Hugging Face. No requiere `HF_TOKEN`; la batería
sí lo requiere para sintetizar con Phonon.

## 1. Comprobación del motor

```bash
uv run python -m proyecto_modelos_lenguaje.stt --check
```

Esperado: `state: ready`, `model: base-int8`, carga en caché menor de 3 s y transcripción de un clip sintético
igual a la frase de prueba.

## 2. Pruebas sin red

```bash
uv run pytest tests/unit/stt tests/api/test_stt_api.py tests/api/test_chat_input.py
cd web && npx vitest run src/test/dictation.test.ts src/test/MicButton.test.tsx src/test/ChatViewDictation.test.tsx
```

Esperado: verde con `engine = "fake"`.

Cubre:
- validación del WAV;
- límites `413` y `415`;
- vacío en silencio;
- correcciones del vocabulario;
- `input` copiado a `turn.input`;
- ningún archivo creado;
- máquina de estados, guarda de eco e inserción en el campo.

## 3. API con el modelo real

```bash
uv run uvicorn proyecto_modelos_lenguaje.api:app --port 8020
curl -s http://127.0.0.1:8020/api/stt
curl -s http://127.0.0.1:8020/api/health          # incluye "stt_available": true
curl -s -X POST http://127.0.0.1:8020/api/stt -H "Content-Type: audio/wav" --data-binary @frase.wav
```

`frase.wav` se puede generar con `python -m proyecto_modelos_lenguaje.stt eval --export-sample`. Esperado: `200`
con `text`, `audio_ms` y `stt_ms` menor de 2000 ms. Un archivo MP3 devuelve `415`.

## 4. Evaluación (SC-001 a SC-004)

```bash
uv run python -m proyecto_modelos_lenguaje.stt eval --models base small
# opcional, grabaciones humanas locales (no se versionan):
uv run python -m proyecto_modelos_lenguaje.stt eval --audio-dir ~/grabaciones_stt
```

Esperado:
- `docs/evaluacion_stt.md` con WER ≤ 0.15, vocabulario ≥ 90 %, p90 < 2 s para clips de hasta 10 s y 100 % de vacío
  en silencio y ruido para el modelo configurado;
- código de salida 0.

## 5. Interfaz (manual o Playwright en el puerto 8020)

1. Abrir `http://127.0.0.1:8020/` en Chrome. Pulsar el micrófono: se pide el permiso solo ahora.
2. Decir «¿Qué produce Manuelita?» y callar. Tras ~1.5 s, el texto queda en el campo sin enviarse. Editar una palabra
   y enviar: la respuesta es la misma que escrita.
3. Pulsar el micrófono y luego «Cancelar»: no aparece texto.
4. Quedarse en silencio: «No te entendí, ¿puedes repetirlo?».
5. Activar «Manos libres» con la voz de Valer-IA activada. Mantener cuatro turnos hablando:
   - cada mensaje se envía solo;
   - el micrófono vuelve tras la respuesta;
   - hablar encima de ella la detiene;
   - su voz nunca aparece como mensaje.
6. `?vista=tecnica`: los turnos dictados muestran «🎙 por voz · audio … · reconocimiento …».
7. Con `MANUELITA_STT_ENABLED=0`, el micrófono aparece deshabilitado con su motivo, y el chat y la voz funcionan igual.
8. Móvil de 375 px: sin desborde horizontal y botón de al menos 44 px.

Playwright puede automatizar los pasos 2–4 y 6 con:
- `--use-fake-ui-for-media-stream`;
- `--use-fake-device-for-media-stream`;
- `--use-file-for-fake-audio-capture=<wav>`.

## 6. Privacidad (SC-006)

Después de los pasos 3–5, no hay archivos `.wav`, `.webm` ni `.ogg` nuevos en el repositorio, en `data/` ni en el
directorio temporal:

```bash
git status --short
find data -newer specs/023-voice-input/plan.md -type f
```

El registro `stt` contiene tiempos y tamaños, nunca el texto.

## 7. Calidad

```bash
UV_PROJECT_ENVIRONMENT=.venv make check
```
