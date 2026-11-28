# Research: stickers de Valer-IA en WhatsApp (spec 034)

Fuentes: código instalado de `@openclaw/whatsapp` 2026.11.10 (`send-*.mjs`, `send-api-*.mjs`,
`light-runtime-api.js`, `active-listener-*.mjs`), `agent/models.py` (`RouteDecision.act`,
`RouteDecision.sentiment`), `channels/bridge.py`, plugin `valeria-bridge`, `docs/whatsapp/README.md` y las fichas de
cada sticker.

## R1. Cómo enviar un mensaje de tipo sticker

- **Decision**: usar la API pública del componente.
  - El plugin `valeria-bridge` importa en tiempo de ejecución el
    `light-runtime-api.js` del `@openclaw/whatsapp` instalado, ubicándolo igual que el parche de la spec 033 en
    `$OPENCLAW_STATE_DIR/npm/projects/openclaw-whatsapp-*/node_modules/@openclaw/whatsapp/dist/`.
  - Llama a `getActiveWebListener(accountId)?.sendSticker(to, buffer)`, que arma el mensaje nativo
    `{ sticker, mimetype: "image/webp" }`.
  - **Respaldo**: si el listener es `null` (otra instancia del módulo o gateway sin conexión) o la llamada falla,
    no se envía el sticker y la respuesta sigue igual (FR-009). Se registra `sticker_unavailable`.
- **Rationale**:
  - `sendMedia` del adaptador saliente, el que ya se usa para la voz, infiere el tipo «sticker» y lo convierte en
    **documento** (`inferWhatsAppMediaKind`); con un `.webp` llegaría como archivo o imagen.
  - `sendSticker` existe en la API del listener, pero ninguna acción del componente lo expone.
  - `getActiveWebListener` sí es exportación pública (`light-runtime-api.js`, `runtime-api.js`) y no requiere
    modificar código de terceros.
- **Alternatives considered**:
  - **Ampliar el parche de la spec 033** para que `sendMedia` produzca stickers: toca 2–3 funciones en dos
    archivos, con más riesgo. Queda como plan B si la verificación temprana muestra que el listener no es
    alcanzable.
  - **Enviarlo como imagen**: no es un sticker y rompe la naturalidad.
  - **CLI `openclaw message send --media`**: es el mismo camino de `sendMedia`, así que llega como documento.
- **Verificación temprana** (primera tarea de implementación): en el gateway real, con `VALERIA_BRIDGE_DEBUG=1`,
  registrar si `getActiveWebListener()` devuelve un listener con `sendSticker` y enviar un sticker de prueba al
  número de un operador.

## R2. Quién decide el sticker y con qué señales

- **Decision**: decide el **backend** (`channels/stickers.py`), de forma determinista, con señales que ya existen:
  - **acto del turno**: `turn.route.act`, con los valores `greeting`, `thanks`, `closing`, `minimal`,
    `complaint`, `about_assistant`, etc.;
  - **sentimiento**: `turn.route.sentiment`, con los valores `frustrated`, `angry`, `distressed`, etc.;
  - **inicio de conversación y presentación**: `conversation_start` e `introduced` (spec 038);
  - **resultado de aprobaciones**: guardar el perfil u olvidar (`_resolve`), y la ruta `planning`;
  - **idioma del turno** (spec 029), estado y evento de la respuesta, y avisos del turno (`sensitive_data`).

  El backend devuelve en la respuesta `sticker: {name, path, position}` y el plugin solo lo envía.
- **Rationale**: el backend ya conoce el hilo, la moderación y las reglas (límites, presentación); el plugin no
  tiene estado por conversación. Las decisiones son reproducibles y comprobables en pruebas, sin depender del
  modelo (supuesto de la spec).
- **Alternatives considered**: que el modelo elija el sticker con una etiqueta en su respuesta (variable, difícil
  de moderar y probar); que el plugin decida (sin acceso al estado del hilo).

## R3. Mapeo situación → sticker

| Situación (señal) | Sticker | Posición |
|---|---|---|
| Saludo y primer contacto (`act=greeting`, `conversation_start=first_contact`) | `valeria-bienvenido` | antes |
| Saludo al iniciar una conversación (`greeting`, `inactivity` o `restart`) | `valeria-hola` | antes |
| Saludo a mitad de conversación (`greeting` sin inicio) | `valeria-consulta` | después |
| Agradecimiento (`act=thanks`) | `valeria-gracias` | después |
| Despedida (`act=closing`) | `valeria-lindo-dia` | después |
| Asentimiento (`act=minimal` y texto de asentimiento: «ok», «dale», «perfecto», «entendido») | `valeria-pulgar` | después |
| Aprobó guardar su perfil (`save_preference` aprobado) | `valeria-gracias-confianza` | después |
| Olvidar datos aprobado, otra acción aprobada o plan entregado (`route=planning`) | `valeria-listo` | después |
| Espera larga (> 8 s sin respuesta) | `valeria-pensando` | antes (lo envía el plugin) |

El mapeo vive en `config/stickers.toml` (situación → archivo, posición, texto visible e idioma) y el equipo lo
puede ajustar (FR-002).

## R4. Moderación

- **Decision**, en orden de evaluación:
  1. **Interruptores**: stickers apagados (`[channels] stickers = false`) o modo demo de pruebas sin archivos →
     nada.
  2. **Exclusiones**:
     - `status` distinto de `answered`, o con `event` de error, límite, `stale` o bloqueo;
     - aviso `sensitive_data` en el turno;
     - sentimiento `frustrated`, `angry` o `distressed`;
     - acto `complaint`;
     - respuesta factual (rutas con herramientas o citas), salvo `planning` → `listo`.
  3. **Idioma**: en inglés, solo stickers sin texto (`pulgar`).
  4. **Moderación del hilo**:
     - no si la respuesta anterior llevó sticker, salvo la despedida;
     - como máximo `stickers_per_conversation` (4);
     - no repetir el mismo, salvo `pulgar`.
  5. **Un sticker por respuesta**: si hay varias situaciones, gana la de mayor prioridad (acción > despedida >
     agradecimiento > saludo > asentimiento).
- **Rationale**: FR-004 a FR-008 y US2; el orden hace verificable cada regla.

## R5. Estado por conversación

- **Decision**: tabla aditiva `channel_stickers(thread_id, sticker, turn_no, sent_at)` en `channels.sqlite3`, más
  el contador de turnos atendidos del hilo, que se deriva de `channel_threads` o de una columna `turns`.
  - El backend registra el sticker al **decidirlo**, no al entregarlo: el plugin no informa de vuelta.
  - Si la entrega falla, el sticker cuenta igual; es la opción conservadora, porque enviará menos y no más.
- **Rationale**: sobrevive a reinicios y es la base de la moderación; no guarda contenido.

## R6. Orden y entrega en el plugin

- **Decision**:
  - **`position: "before"`**: el plugin envía el sticker y luego devuelve el texto, como la voz hoy.
  - **`position: "after"`**: el plugin devuelve el texto y programa el sticker 1,5 s después, sin esperar, para que
    llegue detrás del texto.
  - **Con voz**: el orden es voz, texto y luego sticker.
  - **Errores**: nunca bloquean la respuesta; los logs no llevan el destinatario (`maskDigits`).
- **Rationale**: FR-010. `before_dispatch` entrega el texto al retornar, así que «después» se logra con un envío
  diferido.

## R7. «Pensando»

- **Decision**: lo resuelve el plugin.
  - Al llamar al backend arma un temporizador de `stickerThinkingMs` (8000 ms por defecto, configuración del
    plugin).
  - Si la respuesta no ha llegado cuando vence, envía `valeria-pensando`, como máximo una vez cada 10 minutos por
    remitente (memoria del plugin).
  - Al llegar la respuesta, el temporizador se cancela.
  - El backend publica la ruta del archivo en `GET /api/channels/stickers/pensando`. Más simple: la ruta del
    repositorio se pasa en la configuración del plugin (`stickersDir`).
- **Rationale**: FR-011. Solo el plugin sabe cuánto lleva esperando.
- **Alternatives considered**: que el backend responda dos veces (el contrato es una respuesta por mensaje).

## R8. Archivos y formato

- **Decision**: la fuente única es `docs/whatsapp/stickers/*.webp` (spec 030).
  - El backend valida al cargar el catálogo que cada archivo existe, pesa ≤ 500 KB y es WebP (`RIFF…WEBP`).
  - Un archivo que falte desactiva solo ese sticker y lo avisa en el registro.
  - `ops check` agrega `stickers` (N disponibles y estado del interruptor).
- **Rationale**: FR-001; una pieza dañada no debe tumbar el canal.

## R9. Registro

- **Decision**: `ChannelLogRecord.sticker` con el nombre del sticker o `null`, y `event: "sticker_unavailable"`
  cuando el plugin no pudo enviar el sticker. Esto último solo aparece en el log del plugin, que va con
  `maskDigits`.
- **Rationale**: FR-013; sin contenido de la conversación.
