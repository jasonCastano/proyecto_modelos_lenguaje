# Contrato de UI: voz en el chat del agente (spec 016)

## Controles (`VoiceControls`, en la cabecera del chat)

| Elemento | `data-testid` | Comportamiento |
|----------|---------------|----------------|
| Botón activar/silenciar | `voice-toggle` | `aria-pressed` refleja si la voz está activada. Las etiquetas son «Voz activada» y «Voz silenciada». Al silenciar, se detiene la sesión en curso. La preferencia se guarda en `localStorage["manuelita.voice.muted"]`. |
| Botón detener | `voice-stop` | Visible solo mientras suena audio. Corta el audio en menos de 0,5 s y cancela las peticiones pendientes. |
| Aviso | `voice-unavailable` | Se muestra cuando `GET /api/voice` devuelve `available=false` o falla una síntesis con `503`. Texto: «La voz no está disponible: {detail}. El chat sigue funcionando por texto.». Mientras se muestra, el toggle queda deshabilitado. |
| Indicador | `voice-speaking` | Indicador discreto mientras suena audio (`aria-live="polite"`: «Leyendo respuesta…»). |

## Por turno (`ChatView`)

- Cada respuesta del agente terminada muestra un botón **«Escuchar»** (`data-testid="turn-listen"`) que lee la
  respuesta final (`turn.answer`) con una sesión nueva.
- La traza del turno agrega `🔊 primer audio X,X s` cuando la respuesta se leyó en vivo.

## Flujo en vivo

1. **Envío de la pregunta** (gesto del usuario): se detiene la sesión anterior, se crea o reanuda el `AudioContext`
   y se abre una sesión `live`.
2. **Evento `token`**: se pasa a `SentenceSegmenter.push`. Cada oración nueva se encola y se pide a `/api/tts`
   (hasta 2 peticiones en vuelo) con `thread_id` y `segment`. El audio se reproduce en orden de `segment`.
3. **Evento `done`**: se llama a `flush()` y se encola el resto. Si la respuesta final normalizada (sin citas ni
   espacios repetidos) no empieza con el texto ya encolado, se detiene la sesión y se lee `response.answer` desde
   el principio.
4. **Evento `error`, fin del streaming o desmontaje**: la sesión se detiene.
5. **Voz silenciada o no disponible**: los pasos 2 y 3 no hacen peticiones.

## Reglas

- Solo una sesión suena a la vez en la página.
- Si el navegador rechaza reproducir (`NotAllowedError`), aparece el botón «Reproducir voz»
  (`data-testid="voice-resume"`), que reanuda el `AudioContext`.
- Un `503` desactiva la voz durante la sesión del navegador y muestra el aviso. Cualquier otro error en una oración
  la salta y sigue con la siguiente.
- Nada de esto cambia el texto mostrado ni el contrato de `streamChat`.
