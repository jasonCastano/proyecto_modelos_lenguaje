# Contrato UI: micrófono en el chat (spec 023)

## 1. Elementos

| `data-testid` | Elemento | Notas |
|---|---|---|
| `mic-button` | botón junto a `chat-input`, antes de `chat-send` | `aria-pressed` mientras escucha; `aria-label` «Hablar con Valer-IA» o «Terminar de hablar» |
| `mic-cancel` | botón «Cancelar» | visible solo mientras escucha |
| `mic-level` | barra o anillo de nivel | `role="meter"`, `aria-valuenow` de 0 a 100; respeta `prefers-reduced-motion` (sin animación, solo valor) |
| `mic-status` | texto de estado | `aria-live="polite"`: «Escuchando…», «Procesando…», «Preparando el micrófono…» y los errores |
| `mic-handsfree` | interruptor «Manos libres» | `role="switch"` |
| `mic-privacy` | nota | texto `privacy` de `GET /api/stt` (FR-019) |
| `turn-input` | en `turn-trace` (vista técnica) | «🎙 por voz · audio 2.0 s · reconocimiento 0.45 s · editado» (FR-022) |

- El micrófono aparece en la vista de visitante y en la técnica, en escritorio y en móvil (375 px sin desborde).
- No aparece si `navigator.mediaDevices` no existe o la página no es segura. Aparece deshabilitado, con el motivo
  en el `title` y en `mic-status`, si `GET /api/stt` dice `available = false` (FR-020).

## 2. Comportamiento

1. El permiso del micrófono se pide al primer clic, nunca al cargar (FR-002).
2. Al empezar a grabar se llama a `voice.stop()` si Valer-IA está hablando (FR-013).
3. **Modo normal**: la transcripción reemplaza el contenido del campo si estaba vacío; si no, se agrega con un
   espacio. El foco queda en el campo y nada se envía solo (FR-011). `edited` = el texto enviado difiere de la
   transcripción insertada.
4. **Manos libres** (FR-014 a FR-016):
   - la transcripción se muestra en el campo durante 400 ms y se envía;
   - el micrófono vuelve a escuchar cuando `voice.speaking` pasa a `false` tras la respuesta;
   - la voz del visitante encima de la de Valer-IA la interrumpe;
   - la guarda de eco (R10) descarta transcripciones parecidas a lo que ella dijo;
   - se apaga tras `handsfree_idle_seconds` sin voz.
5. Cambiar de pestaña (`visibilitychange` a `hidden`) cancela la grabación sin enviar (FR-005).
6. Mientras hay una petición de chat en curso, el micrófono puede grabar, pero en modo normal el texto solo se
   inserta y en manos libres se envía cuando termina la respuesta. Nunca hay dos envíos simultáneos.
7. Una nueva grabación descarta el resultado pendiente de la anterior (solo cuenta la última).

## 3. Mensajes (español, sin detalles técnicos)

| Error | Mensaje |
|---|---|
| `permission` | «Necesito permiso para usar el micrófono. Puedes habilitarlo en el candado de la barra de direcciones, o escribir tu mensaje.» |
| `no_device` | «No encontré un micrófono conectado. Puedes escribir tu mensaje.» |
| `insecure` / `unsupported` | (sin botón) |
| `unavailable` | «El dictado no está disponible en este momento. Puedes escribir tu mensaje.» |
| `busy` | «El dictado está ocupado; intenta de nuevo en unos segundos.» |
| `empty` | «No te entendí, ¿puedes repetirlo?» |
| `too_long` | «Llegaste al límite de 60 segundos; reconocí lo que alcanzaste a decir.» |
| `network` / `server` | «No pude convertir tu voz en texto. Intenta de nuevo o escribe tu mensaje.» |

## 4. Estilo

- Paleta del contrato UI existente.
- Estado «escuchando» con el acento verde de la marca y un punto rojo de grabación.
- El botón tiene 44 × 44 px mínimos.
