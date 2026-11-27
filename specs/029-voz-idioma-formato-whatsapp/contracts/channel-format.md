# Contrato: formato de las respuestas del canal (spec 029)

Complementa `specs/024-…/contracts/channel-api.md` §5 y `specs/028-…/contracts/channel-api-v2.md`.

## 1. Entrada de una nota de voz (plugin `valeria-bridge`)

- Es nota de voz si `content` o `body` del hook `before_dispatch` contienen, en cualquier posición, `[Audio]`,
  `Transcript:` o `<media:audio>`.
- Se envía `kind: "audio"`, `input_mode: "voice"` y `text` = la transcripción (texto que sigue al último
  `Transcript:`; si no hay etiqueta, el texto tras `[Audio]` sin líneas `User text:` ni marcas `<media:…>`).
- Nada del encabezado del gateway (remitente, número, fecha) viaja al backend.
- Depuración (`VALERIA_BRIDGE_DEBUG=1`): una línea por mensaje con la forma, nunca el contenido:
  `forma content: len=…, [Audio]@pos, Transcript:@pos, media@pos · body: …` (dígitos → `#`).

## 2. Respuesta escrita

```text
<cuerpo en párrafos, con citas [1] [2] …>

Fuentes:                                   ← «Sources:» si la respuesta es en inglés
[1] Informe de Sostenibilidad Manuelita 2021-2022, p. 31 — https://…
[2] Manuelita: más que azúcar — https://…
```

Reglas:

1. Todo el mensaje en el idioma del turno (cuerpo, aviso, encabezados, marcas, invitaciones).
2. Una línea por fuente: `[n] Título[, p. X] — URL`. Numeración 1..N sin huecos. Sin fuentes repetidas por
   (URL, página). Títulos de una línea, ≤ 80 caracteres, sin `Índice`, listas ni números sueltos.
3. Sin líneas vacías ni numeradas sueltas dentro del bloque de fuentes.
4. Si la respuesta no tiene citas, no hay bloque de fuentes.
5. Al dividir en varios mensajes (≤ 1.500 caracteres, ≤ 4 mensajes), el bloque de fuentes va completo en el último.

## 3. Aviso de seguridad

- Solo si el mensaje de la persona contiene tarjeta, documento de identidad o contraseña.
- Una frase al final de la respuesta, en el idioma del turno; una vez por conversación (salvo dato nuevo).
- es: «Ojo: por aquí no hace falta que compartas datos como tarjetas o documentos; para lo que necesites me basta
  con tu pregunta.»
- en: «Just so you know, there's no need to share card or ID details here; your question is all I need.»

## 4. Revisión automática

`channels.quality.review_reply(messages, language, *, sensitive_input=False) -> list[Issue]` devuelve los hallazgos
del data model. Lista vacía = respuesta conforme. Se usa en pruebas, en `pml channels simulate --check` y sobre los
fixtures de regresión.
