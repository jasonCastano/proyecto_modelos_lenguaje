# Research: voz, idioma único y formato ordenado en WhatsApp (spec 029)

Evidencia (2026-11-27): tres notas de voz reales (`C:\Users\JCastano\Downloads\pruebas valeria`), su
transcripción local con el dictado del proyecto, `channels.jsonl` (solo metadatos) y el código de OpenClaw
2026.11.10 instalado (`dist/format-*.mjs`, `dist/dispatch-from-config-*.mjs`).

## R1. Por qué las notas de voz llegaron como texto (Historia 1)

- **Hallazgos**:
  - OpenClaw sí transcribió: las respuestas atienden la pregunta de cada audio y la transcripción local coincide.
  - `channels.jsonl` registra las tres como `kind: text`, `input_mode: text`, `voice_sent: false`.
  - `formatMediaUnderstandingBody` arma el bloque `[Audio]\nUser text:\n…\nTranscript:\n<texto>`.
  - El hook recibe `content: hookContext.content` y `body: bodyForAgent ?? body`
    (`dispatch-from-config-*.mjs`). El plugin usa `content ?? body` y solo reconoce el audio si el texto
    **empieza** por `[Audio]` o es exactamente `<media:audio>`.
  - Conclusión probable: el bloque no llega al inicio de `content` (OpenClaw antepone un encabezado del
    mensaje, que incluye el número del remitente) o llega solo la transcripción. En ambos casos el plugin la
    clasifica como texto.
- **Decision**:
  1. **Captura de verificación (primera tarea, con el teléfono)**: con `VALERIA_BRIDGE_DEBUG=1` el plugin
     registra la *forma* de `content` y de `body`: longitud, si contiene `[Audio]`, `Transcript:`,
     `<media:audio>` y en qué posición, con los dígitos enmascarados. Nunca el texto completo ni el número.
  2. **Detección robusta** en `valeria-bridge`:
     - es voz si `[Audio]`, `Transcript:` o `<media:audio>` aparece **en cualquier parte** de `content` o de
       `body`;
     - la transcripción es lo que sigue al último `Transcript:` (o a `[Audio]` si no hay etiqueta), sin el
       encabezado ni los metadatos;
     - `kind: "audio"`, `input_mode: "voice"`.
  3. **Nunca se reenvía el encabezado**: al backend solo llega la transcripción (o el texto escrito), sin
     números ni marcas del gateway.
- **Rationale**: arregla las dos fallas con un solo cambio (sin voz y aviso falso, R2), sin depender del formato
  exacto del encabezado, y se confirma con datos reales antes de declararlo resuelto.
- **Alternatives considered**: leer el adjunto con el hook `message_received` (más permisos y cambio mayor a un
  día de la sustentación); pedir a OpenClaw solo la transcripción (no hay opción documentada).

## R2. Aviso de seguridad falso y robótico (Historia 3)

- **Hallazgos**:
  - El aviso sale de `prompts/conduct.md` § `sensitive_notice` y lo antepone `graph._lead()` cuando
    `pii_notice` (de `privacy.find_pii` sobre el mensaje original) incluye `credit_card`, `document` o `phone`.
  - En las pruebas la persona no dijo ningún número. El disparador más probable es el número del remitente
    dentro del encabezado de la nota de voz (R1), detectado por `PHONE_PATTERN`.
  - El texto actual es robótico: enumera categorías, abre la respuesta y afirma «no los guardé».
- **Decision**:
  1. **Disparador**: solo `credit_card` y `document` (y frases de contraseña:
     «mi contraseña es…» / «my password is…»).
     - Un teléfono no dispara el aviso: compartirlo es legítimo para pedir contacto y ya se redacta.
     - Los metadatos del canal ya no llegan al texto (R1).
  2. **Una vez por conversación**: bandera `sensitive_notice_given` en el estado del hilo; se vuelve a dar solo
     si se comparte un dato sensible nuevo en un turno posterior.
  3. **Texto natural por idioma**, nuevas secciones de `prompts/conduct.md` (1.2 → 1.3):
     - `sensitive_notice` (es): «Ojo: por aquí no hace falta que compartas datos como tarjetas o documentos;
       para lo que necesites me basta con tu pregunta.»
     - `sensitive_notice_en` (en): «Just so you know, there's no need to share card or ID details here;
       your question is all I need.»
  4. **Ubicación**: al final de la respuesta, como cierre amable, no como apertura.
- **Rationale**: FR-007 a FR-010; mantiene la protección real y elimina el falso positivo.
- **Alternatives considered**: quitar el aviso (pierde la protección); dejar el teléfono como disparador (lo
  dispararía cualquier solicitud de contacto legítima).

## R3. Un solo idioma por respuesta (Historia 2)

- **Hallazgos**: el modelo ya respondió el cuerpo en inglés. Lo que quedó en español son los textos fijos:
  - el aviso (`conduct.md`);
  - el encabezado «Fuentes:» y «Fuentes sintéticas (demostración):» (`channels/format.py`);
  - la marca «(respuesta abreviada; pídeme más detalle)»;
  - los prefijos de `care.prefixes` en español.
- **Decision**:
  - **Idioma del turno**: `channels.intents.language_of(texto, pista)`, con el idioma de la conversación como
    respaldo para mensajes cortos. Viaja al agente (`language`) y al formateador.
  - **Formateador** `to_whatsapp(..., language)`:
    - encabezados «Fuentes:»/«Sources:» y «Fuentes sintéticas (demostración):»/«Synthetic sources (demo):»;
    - marca de respuesta abreviada en el idioma.
  - **Prefijos fijos de `_lead`**: en inglés se usa la variante `_en` si existe; si no, el prefijo se omite y el
    modelo cubre ese gesto (el bloque `Atención:` ya lleva `Idioma: en`).
  - **Textos del canal** (`bridge.TEXTS`): ya son bilingües (spec 028); se verifican en la revisión automática
    (R5).
- **Rationale**: FR-004 a FR-006 sin cambiar el comportamiento en español.
- **Alternatives considered**: traducir con el modelo cada texto fijo (latencia y costo); dejar el encabezado en
  español (viola FR-005).

## R4. Bloque de fuentes ordenado (Historia 4)

- **Hallazgos**:
  - `format.sources_block` recorta el título a 80 caracteres pero **conserva los saltos de línea**. Por eso
    `[5] Índice\n1.\n2.\n…` (el título de la unidad viene del PDF).
  - `number_citations` numera por etiqueta (`U3`, `F1`…). Dos etiquetas con el mismo documento y página
    reciben dos números ([1] y [2] en la prueba 10.08.56).
- **Decision**:
  1. `clean_title(title, url)`:
     - une espacios y saltos de línea en uno solo;
     - quita viñetas y numeraciones sueltas (`1.`, `2.`) y prefijos de índice («Índice», «Contenido»,
       «Tabla de contenido»);
     - si queda vacío, demasiado corto (< 4 letras) o dominado por números, usa el **nombre del documento**
       tomado del archivo del enlace (`Informe-de-Sostenibilidad-Manuelita-2013-2014_digitalA.pdf` →
       «Informe de Sostenibilidad Manuelita 2013-2014»); si no hay archivo, usa el dominio;
     - máximo 80 caracteres con «…».
  2. **Dedupe por (URL, página)**: las etiquetas con la misma fuente comparten número. El texto se renumera
     (`[U1]`, `[F2]` → `[1]`) y las citas repetidas en la misma frase se colapsan (`[1][1]` → `[1]`).
  3. **Formato fijo de línea**: `[n] Título, p. X — URL`; numeración consecutiva desde 1; sin líneas vacías
     dentro del bloque.
  4. **División en mensajes**: el bloque de fuentes nunca se parte. Si no cabe con el cuerpo, va completo en el
     último mensaje (comportamiento de la spec 024 que se conserva).
- **Rationale**: FR-011 a FR-014; arreglo determinista y probado, sin tocar la capa oro.
- **Alternatives considered**: limpiar los títulos en el oro (no se reescriben capas: constitución); que el
  modelo escriba las fuentes (no verificable).

## R5. Revisión automática del formato (FR-015)

- **Decision**: nuevo `channels/quality.py` con `review_reply(messages, language) -> list[Issue]`:
  - **idioma único**: el encabezado de fuentes del idioma correcto; ninguna frase fija del otro idioma (lista
    de marcadores: «Fuentes:», «Sources:», «Por tu seguridad», «Just so you know», «respuesta abreviada»…);
    heurística de palabras funcionales por oración;
  - **bloque de fuentes**: regex de línea, numeración consecutiva, sin repetidos (URL + página), títulos de una
    línea de ≤ 80 caracteres;
  - **aviso sin motivo**: presencia del aviso cuando el mensaje de entrada no tenía datos sensibles.
- Se usa:
  - en las pruebas unitarias;
  - en `pml channels simulate --script … --check`;
  - sobre las tres respuestas reales de las pruebas, como casos de regresión: deben **fallar** con el formato
    anterior y **pasar** reprocesadas con el nuevo.
- **Rationale**: SC-002 a SC-005 medibles sin revisar a mano.

## R6. Casos de regresión

- **Decision**:
  - Las tres respuestas reales (solo texto de Valer-IA, sin datos personales) se versionan como fixture:
    `tests/fixtures/channels/regression_2026-11-27.jsonl`, con la pregunta transcrita, el idioma y la respuesta
    original. Los audios **no** se versionan.
  - Un conjunto de 20 consultas (10 es, 10 en; texto y voz) + 3 con datos sensibles ficticios:
    `tests/fixtures/channels/language_format.jsonl`, fijado antes de medir.

## Hallazgos de la implementación (2026-11-27)

- **Voz (R1)**: el plugin reconoce `[Audio]`, `Transcript:` o `<media:audio>` en cualquier posición de `content`
  o `body` y envía solo la transcripción, sin el encabezado del gateway. Pruebas con el bloque al inicio, detrás
  del encabezado con número y solo en `body`. La forma exacta en el teléfono queda por confirmar con la captura
  (T006, § «Hallazgos de la captura»).
- **Aviso (R2)**: lo disparaba el teléfono del encabezado. `phone` sale de los avisos; `password` entra
  (`privacy.detect_password`, con conector explícito: «la clave del éxito» no cuenta). El aviso va al final, una
  vez por hilo y tipo (`sensitive_notice_given`). En la simulación real el modelo añadía su propio aviso además
  del nuestro; `agent.md` 1.10 (regla 8) lo evita.
- **Idioma (R3)**: el detector de idioma fallaba con «When was Ingenio Manuelita founded?» y «Which
  certifications does Manuelita have?»; se ampliaron las palabras funcionales en inglés y las 23 consultas del
  fixture se detectan bien. El canal pasa el idioma del turno (`service.send(language=)`) y el formateador usa
  «Sources:»; los prefijos del guion de cuidado (solo en español) se omiten en turnos en inglés.
- **Fuentes (R4)**: además de «Índice…», aparecieron títulos de metadatos de PDF («Portada-acercade-cartapresidente
  VFBAJA», «01 Informe Manuelita», «Informe-…_VF_BAJA, p. 27») y un título genérico repetido para noticias
  distintas («Conoce las últimas noticias…»). Se usa el nombre del documento del enlace o, si el título se repite
  con enlaces distintos, el nombre de cada enlace.
- **Simulación real** (`pml channels simulate --script tests/fixtures/channels/language_format.jsonl --check`,
  backend aparte en el puerto 8010): 0 hallazgos en 23 mensajes; las 10 consultas por audio recibieron nota de
  voz en su idioma. En modo demo quedan oraciones del corpus en español dentro de respuestas en inglés (el modelo
  guionado no traduce); por eso el criterio es el modo real.

## Hallazgos de la captura (prueba con el teléfono, 2026-11-27 12:19)

- La nota de voz llegó al backend como texto (`kind: text`, `input_mode: text`, `voice_sent: false`) aun con la
  detección en cualquier posición: en OpenClaw 2026.11.10, `before_dispatch` recibe `content` =
  `BodyForCommands`, que con la transcripción activa es **solo el texto transcrito** (sin `[Audio]` ni
  `Transcript:`), y el evento no trae los adjuntos (`PluginHookBeforeDispatchEvent`: solo `content`, `body`, ids).
- El hook `message_received` sí trae `media` (`contentType: "audio/ogg; codecs=opus"`, `kind`, `transcribed`) con
  el mismo `messageId`, `sessionKey` y `content`, y se emite antes de elegir la ruta (fire-and-forget).
- **Decisión**: el plugin registra `message_received` y recuerda los mensajes con audio (`VoiceMemory`, por id y
  por sesión + contenido, 10 min); en `before_dispatch` espera hasta 300 ms ese registro y, si hay audio, envía
  `kind: "audio"`, `input_mode: "voice"` y el `content` como transcripción. La detección por marcas se conserva
  por si otra versión de OpenClaw entrega el bloque `[Audio]`.
- La línea de depuración `forma …` no apareció porque `VALERIA_BRIDGE_DEBUG` no estaba en el `.env` externo; ahora
  incluye `audio adjunto=sí|no`.
- **Segunda captura (12:38)**: `forma content: len=159, [Audio]@-1, Transcript:@-1, media@-1, encabezado=sí ·
  body: len=85 … · audio adjunto=no`. Tampoco `message_received` trae el adjunto: OpenClaw arma el contexto del
  hook solo con `ctx.media` (`normalizeMediaFacts(e.media)`) y WhatsApp usa los campos `MediaPath`/`MediaType`.
- **Decisión final**: la señal de voz la da el propio backend. Cada nota de voz pasa por
  `POST /api/channels/transcriptions` (CLI de `tools.media.audio`); el backend guarda en memoria una huella
  normalizada del texto (sin tildes ni signos, 10 min, se consume una vez) con el idioma detectado, y
  `ChannelBridge.handle` trata como nota de voz el mensaje cuyo texto coincide (`RecentTranscriptions`). La
  detección del plugin (marcas y `message_received`) se mantiene como respaldo para otras versiones de OpenClaw.
- **Tercera prueba (12:46)**: con `RecentTranscriptions` el backend reconoció la nota de voz (`kind: audio`,
  `input_mode: voice`, nota de voz generada), pero el envío por `openclaw message send --media` falló a los 30 s:
  en este equipo el CLI tarda ~46 s solo en arrancar (carga todos los plugins; WhatsApp 7,6 s; medido con
  `--dry-run`). **Decisión**: el plugin envía la nota de voz dentro del gateway con
  `api.runtime.gateway.request("send", …)` (el mismo método que usa el CLI; `SendParamsSchema`: `to`,
  `idempotencyKey`, `buffer` en base64, `contentType`, `asVoice: true`), sin abrir otro proceso. Si ese camino
  falla, el CLI queda como respaldo en segundo plano (180 s) sin frenar el texto, y el log dice qué camino se usó.
- **Cuarta prueba (12:55)**: `runtime.gateway.request` está reservado a plugins oficiales («Gateway requests are
  only available to bundled or trusted official plugins») y el CLI de respaldo falló a los 48 s sin decir por qué.
  **Decisión**: la nota de voz va por el adaptador de salida del canal dentro del gateway
  (`api.runtime.channel.outbound.loadAdapter("whatsapp").sendMedia`, con `audioAsVoice: true` y la carpeta del audio
  como `mediaLocalRoots`), que usa la conexión de WhatsApp ya abierta. El CLI sigue como respaldo y ahora registra
  el final de su salida (dígitos enmascarados) para diagnosticar.
- **Quinta prueba (13:17–13:19)**: dos notas de voz desde el teléfono → nota de voz de respuesta en ambas,
  enviada por el adaptador del canal (`nota de voz enviada por el adaptador del canal`, ~16 s y ~35 s después de
  la forma). Queda confirmada la cadena: transcripción del backend → `RecentTranscriptions` → respuesta con voz →
  `sendMedia` con `audioAsVoice`. Nota operativa: tras `openclaw_env.ps1 -Restart` el gateway tarda ~2 min en
  escuchar WhatsApp; un mensaje enviado en ese lapso llega como pendiente y OpenClaw no lo procesa.
