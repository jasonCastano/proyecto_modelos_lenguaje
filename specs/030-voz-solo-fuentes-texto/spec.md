# Feature Specification: Respuesta por voz sin texto duplicado (solo fuentes por escrito)

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (trabajo continuo de las specs 028–029; la rama la decide el equipo)

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "En la carpeta «pruebas valeria\2» se tienen nuevas pruebas que se han hecho con Valeria a través de WhatsApp. Valeria está respondiendo bien a los audios. A solicitudes de audio Valeria está enviando dos respuestas, la respuesta de audio y una misma respuesta en texto con las fuentes. Esta respuesta es redundante, cuando Valeria responda por audio, por texto únicamente deben estar detalladas las fuentes, no debe repetirse el mensaje ya enviado por audio"

## Contexto de las pruebas (2026-11-27, 13:26 y 13:31)

Dos notas de voz desde el teléfono de prueba recibieron una nota de voz de Valer-IA **y además** un mensaje escrito con
la misma respuesta completa seguida del bloque «Fuentes:». Ejemplo (13:26, «¿qué productos genera Manuelita?»): la
nota de voz cuenta los negocios de Manuelita y el texto repite párrafo por párrafo lo mismo («Claro. Manuelita produce
azúcar y, además, tiene negocios en biocombustibles…») antes de listar las tres fuentes. La persona recibe dos veces la
misma respuesta; lo único que el texto aporta y la voz no puede dar son las fuentes con sus enlaces.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nota de voz + solo las fuentes por escrito (Priority: P1)

Una persona le envía a Valer-IA una nota de voz con una pregunta sobre Manuelita. Valer-IA responde con una nota de
voz natural y, por escrito, envía **únicamente** el bloque de fuentes (encabezado y una línea por fuente con su
enlace), sin repetir el contenido que ya dijo en audio.

**Why this priority**: es el defecto observado en las dos pruebas; la respuesta duplicada hace la conversación pesada y
poco natural, y contradice el objetivo de que la voz sea la respuesta.

**Independent Test**: enviar una nota de voz que requiera buscar en los documentos; se reciben exactamente dos
mensajes: la nota de voz y un texto que solo contiene el encabezado de fuentes y sus líneas.

**Acceptance Scenarios**:

1. **Given** una pregunta por nota de voz con respuesta respaldada por documentos, **When** Valer-IA responde, **Then** la
   persona recibe la nota de voz y un mensaje escrito que contiene solo «Fuentes:» (o «Sources:» si la pregunta fue en
   inglés) y las líneas `[n] Título — enlace`, sin ninguna oración de la respuesta.
2. **Given** la misma pregunta escrita por texto, **When** Valer-IA responde, **Then** la persona recibe la respuesta
   completa escrita con sus fuentes, como hoy (sin cambios para el texto).
3. **Given** una pregunta por nota de voz cuya respuesta no tiene fuentes (saludo, conversación, «no encontré
   evidencia»), **When** Valer-IA responde, **Then** la persona recibe solo la nota de voz, sin mensaje escrito vacío ni
   encabezado de fuentes sin líneas.

---

### User Story 2 - Si la voz no llega, la respuesta escrita completa (Priority: P1)

Si la nota de voz no se pudo generar o no se pudo entregar, la persona no se queda sin respuesta: recibe la respuesta
escrita completa con sus fuentes.

**Why this priority**: al quitar el texto de la respuesta, la voz pasa a ser el único portador del contenido; una falla
de voz no puede dejar a la persona solo con una lista de enlaces.

**Independent Test**: forzar una falla de la síntesis de voz (y, por separado, del envío de la nota de voz) ante una
pregunta por voz; se recibe la respuesta escrita completa con fuentes.

**Acceptance Scenarios**:

1. **Given** una pregunta por nota de voz y una falla al generar la voz, **When** Valer-IA responde, **Then** la persona
   recibe la respuesta escrita completa con sus fuentes y el aviso breve de que no pudo enviar el audio.
2. **Given** una pregunta por nota de voz, la voz generada y una falla al entregar la nota de voz por el canal, **When**
   Valer-IA responde, **Then** la persona recibe la respuesta escrita completa con sus fuentes (no solo las fuentes).

---

### User Story 3 - La voz menciona que las fuentes van por escrito (Priority: P3)

Cuando se envían fuentes por escrito, la nota de voz cierra con una frase breve y natural que avisa que las fuentes
quedan en el mensaje escrito, para que el texto que llega no parezca suelto.

**Why this priority**: mejora la naturalidad, pero la historia 1 ya resuelve la duplicación.

**Independent Test**: escuchar la nota de voz de una respuesta con fuentes: termina con una frase del tipo «te dejo las
fuentes por escrito» en el idioma de la pregunta; una respuesta sin fuentes no la incluye.

**Acceptance Scenarios**:

1. **Given** una respuesta por voz con fuentes en español, **When** se genera la nota de voz, **Then** termina con una
   frase breve que indica que las fuentes van por escrito.
2. **Given** una respuesta por voz con fuentes en inglés, **When** se genera la nota de voz, **Then** la frase está en
   inglés; **And** una respuesta sin fuentes no la incluye.

### Edge Cases

- **Formato de respuesta elegido por la persona**: si pidió «respóndeme por escrito», todo sigue por texto completo; si
  pidió «mándame audio» y escribe, recibe nota de voz + solo fuentes (misma regla que una nota de voz).
- **Avisos que no son la respuesta** (aviso de datos sensibles, «cambiaste de tema», acción por confirmar): lo que
  forma parte de lo dicho en la voz no se repite por escrito; una confirmación pendiente («¿lo guardo?») se dice en la
  voz y no exige texto.
- **Fuentes sintéticas de demostración** (planificación): se listan por escrito igual que las públicas, con su
  encabezado propio, y nada más.
- **Respuestas largas**: el bloque de fuentes nunca se parte entre mensajes; si no cabe en uno, se envían líneas
  completas en mensajes consecutivos sin repetir el encabezado a mitad de línea.
- **Idioma**: el encabezado y la frase de la voz van en el idioma de la pregunta (regla de la spec 029).
- **Pruebas de regresión de formato**: la revisión automática del canal (spec 029) acepta un mensaje que es solo el
  bloque de fuentes y marca como error que un turno con voz repita oraciones de la respuesta por escrito.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cuando la respuesta de un turno se entrega como nota de voz, el mensaje escrito MUST contener únicamente
  el bloque de fuentes (encabezado en el idioma del turno y una línea por fuente), sin oraciones de la respuesta.
- **FR-002**: Si la respuesta entregada por voz no tiene fuentes, el sistema MUST NOT enviar mensaje escrito alguno
  (ni vacío ni con un encabezado sin fuentes).
- **FR-003**: Cuando la respuesta se entrega solo por texto (pregunta escrita sin preferencia de audio, o preferencia
  «por escrito»), el comportamiento MUST seguir igual: respuesta completa con fuentes.
- **FR-004**: Si la nota de voz no se puede generar, el sistema MUST enviar la respuesta escrita completa con fuentes
  y el aviso breve de que no se pudo enviar el audio.
- **FR-005**: Si la nota de voz se generó pero no se pudo entregar por el canal, el sistema MUST enviar la respuesta
  escrita completa con fuentes en lugar de solo las fuentes.
- **FR-006**: El bloque de fuentes enviado tras una nota de voz MUST cumplir el formato de la spec 029 (títulos limpios,
  sin duplicados por enlace y página, numeración 1..N, idioma del turno) y nunca partirse a mitad de línea.
- **FR-007**: Cuando se envían fuentes por escrito tras la voz, la nota de voz SHOULD cerrar con una frase breve y
  natural, en el idioma del turno, que indique que las fuentes van por escrito; sin fuentes, no la incluye.
- **FR-008**: La revisión automática del formato del canal MUST tratar como conforme un turno con voz cuyo texto es solo
  el bloque de fuentes, y como hallazgo («texto duplicado de la voz») un turno con voz cuyo texto repite la respuesta.
- **FR-009**: El registro de cada turno del canal MUST indicar qué se entregó por escrito (respuesta completa, solo
  fuentes o nada) para poder verificar las pruebas sin leer contenido.

### Key Entities

- **Entrega del turno**: lo que recibe la persona por una respuesta: nota de voz (sí/no) y contenido escrito
  (respuesta completa, solo fuentes o nada), con el idioma del turno.
- **Bloque de fuentes**: encabezado en el idioma del turno y líneas `[n] Título[, p. X] — enlace`, públicas y
  sintéticas por separado (definido en la spec 029).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En 10 de 10 preguntas por nota de voz con fuentes, el mensaje escrito contiene solo el bloque de fuentes
  (0 oraciones de la respuesta repetidas).
- **SC-002**: En 3 de 3 preguntas por nota de voz sin fuentes (saludo, conversación, sin evidencia), la persona recibe
  solo la nota de voz.
- **SC-003**: En 10 de 10 preguntas escritas, la respuesta escrita completa con fuentes no cambia respecto de hoy.
- **SC-004**: Ante una falla simulada de voz (generación o entrega), la persona recibe la respuesta escrita completa en
  el 100 % de los casos; nunca solo una lista de fuentes.
- **SC-005**: Las dos pruebas del 2026-11-27 (13:26 y 13:31) repetidas por voz dan una nota de voz y un texto de 4 y 2
  líneas respectivamente (encabezado + fuentes), sin la respuesta repetida.

## Assumptions

- El texto «solo fuentes» lleva únicamente el encabezado y las líneas de fuentes; no se agrega una frase introductoria
  escrita (la referencia a las fuentes, si se incluye, va en la voz — historia 3).
- La nota de voz se envía antes que el texto de fuentes, como hoy.
- Las respuestas que no son de búsqueda (saludos, confirmaciones, avisos) siguen las mismas reglas: si van por voz, el
  texto solo lleva fuentes (normalmente ninguna, así que no hay texto).
- Las specs 028 y 029 (reconocimiento de la nota de voz, entrega de la voz por WhatsApp, idioma del turno, formato de
  fuentes y aviso de datos sensibles) están implementadas y se reutilizan.
- Los audios y textos de `C:\Users\JCastano\Downloads\pruebas valeria\2` son solo referencia; no se versionan ni se
  copian datos personales al repositorio.
