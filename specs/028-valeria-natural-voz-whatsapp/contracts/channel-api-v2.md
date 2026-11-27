# Contrato v2: API del canal (cambios sobre la spec 024)

Las reglas de acceso no cambian: solo loopback y `X-Channel-Token` (comparación en tiempo constante); `403
channel_forbidden`, `503 channel_disabled`.

## 1. `POST /api/channels/messages` (ampliado)

Petición (campos nuevos en **negrita**; los demás como en la spec 024):

```json
{
  "channel": "whatsapp",
  "message_id": "3EB0C4A1F2...",
  "sender": "+573001234567",
  "kind": "audio",
  "text": "¿qué produce manuelita?",
  "input_mode": "voice",
  "language_hint": "es",
  "received_at": "2026-11-28T13:05:12Z"
}
```

- **`input_mode`**: `text` | `voice` (por defecto `text`; `voice` si `kind = audio`).
- **`language_hint`**: `es` | `en` | null.
- `text` es requerido para `kind ∈ {text, audio}`; en `audio` contiene la transcripción.

Respuesta `200` (campo nuevo `voice`, opcional):

```json
{
  "status": "answered",
  "messages": ["Manuelita produce *azúcar*, bioetanol… [1]\n\nFuentes:\n[1] Informe de Sostenibilidad…"],
  "voice": {
    "audio_path": "C:\\Users\\…\\state\\channels\\voice\\5b1f….ogg",
    "language": "es",
    "duration_ms": 18400,
    "mime": "audio/ogg; codecs=opus"
  },
  "thread_id": "6f1c…",
  "route": "documental",
  "tools": ["search_documents"],
  "latency_ms": 9321
}
```

Reglas:

| Situación | `messages` | `voice` |
|---|---|---|
| Pregunta por texto, `reply_format = auto` o `text` | Respuesta con citas y fuentes | ausente |
| Pregunta por voz, `reply_format = auto` o `voice` | Respuesta con citas y fuentes | guion hablado |
| Pregunta por texto, `reply_format = voice` | Respuesta con citas y fuentes | guion hablado |
| Pregunta por voz, `reply_format = text` | Respuesta con citas y fuentes | ausente |
| Acción pendiente / confirmación / reinicio | Texto natural | guion corto si la entrada fue voz |
| Audio sin transcripción | «No te escuché bien…» (natural) | ausente |
| Falla la síntesis | Texto + frase breve de disculpa | ausente (se registra `voice_error`) |

- `busy` deja de usarse: los mensajes de una misma persona esperan en cola (≤ 60 s) y se responden en orden.
> **Spec 030**: con voz, la respuesta trae además `sources_messages` (solo el bloque de fuentes). El plugin
> entrega ese texto si la nota de voz llegó y `messages` (respuesta completa) si no. Ver
> [channel-voice-text.md](../../030-voz-solo-fuentes-texto/contracts/channel-voice-text.md).

- Ningún texto de `messages` sugiere comandos (contrato [conversation.md](conversation.md)).
- Timeout del puente: 90 s; si vence, el plugin no maneja el turno (modo degradado, solo texto).

## 2. `POST /api/channels/transcriptions` (nuevo)

Lo llama el CLI de transcripción que ejecuta OpenClaw. Solo loopback + `X-Channel-Token`.

- Cuerpo: el audio crudo (`Content-Type: application/octet-stream`; Ogg/Opus, MP3, WAV o M4A, ≤ 16 MB,
  ≤ 120 s). Se eligió cuerpo crudo y no `multipart/form-data` para no añadir `python-multipart`; se
  decodifica con PyAV propio porque `faster_whisper.decode_audio` falla con PyAV 19.
- Respuesta `200`: `{"text": "…", "language": "es", "audio_ms": 6400, "latency_ms": 1800}`.
- Sin habla: `200` con `text: ""`.
- Errores: `400 audio_invalid`, `413 audio_too_long`, `503 stt_unavailable`.
- El audio se procesa en memoria; no se guarda ni se registra su texto.

## 3. CLI `python -m proyecto_modelos_lenguaje.channels.transcribe_cli <ruta>`

- Lee `VALERIA_CHANNEL_TOKEN` y `VALERIA_BACKEND_URL` (por defecto `http://127.0.0.1:8000`).
- Escribe la transcripción en stdout (una línea, UTF-8) y sale con 0; sin habla → stdout vacío y 0.
- Si el backend no responde en 20 s, transcribe en proceso con el servicio de la spec 023.
- Error irrecuperable → código 1 y mensaje en stderr (OpenClaw prueba el siguiente modelo o entrega el
  `<media:audio>` original, que el backend responde pidiendo repetir).

## 4. Plugin `valeria-bridge` (cambios)

- `messageKind`: un `content` que empieza por el bloque `[Audio]` (formato confirmado en la prueba S1) se envía
  como `kind: "audio"`, `input_mode: "voice"` y `text` = transcripción extraída.
- Si la respuesta trae `voice`, el plugin envía primero la nota de voz al remitente (ruta confirmada en S2) y
  después devuelve `{ handled: true, text }`. Si el envío del audio falla, registra el error y entrega igual el
  texto.
- `timeoutMs` por defecto 90.000.
