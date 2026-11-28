# Feature Specification: Respuestas de Valer-IA por WhatsApp en voz, en un solo idioma y bien ordenadas

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (corrige la spec 028 antes de la sustentación; mismo PR)

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "He realizado pruebas en WhatsApp con Valeria. En «pruebas valeria» hay audios y textos
con las respuestas. En «WhatsApp Audio 10.10.40» la primera frase de seguridad de datos es muy robótica y no se
siente como una conversación natural. En «WhatsApp Ptt 10.08.56» la solicitud se hizo en inglés, pero Valeria dio el
mensaje por defecto en español y combinó dos idiomas: Valeria DEBE responder en el mismo idioma que le consultan,
sea audio o texto, sin combinar idiomas. En «WhatsApp Ptt 10.00.56» la estructura de las fuentes al final está
desorganizada: los textos de respuesta deben ser ordenados y bien estructurados; NO SE ACEPTAN mensajes sin orden.
Estas pruebas fueron solicitudes por audio y el agente contestó por texto: DEBE contestar por audio cuando reciba
una solicitud por audio."

## Contexto: evidencia de las pruebas del 2026-11-27

Tres notas de voz enviadas desde un teléfono de prueba a la SIM de Valer-IA (modo cerrado). La transcripción local
de los audios y el registro técnico del canal (solo metadatos) muestran:

| Prueba | Lo que dijo la persona | Lo que pasó | Problema |
|---|---|---|---|
| Audio 10.10.40 | «Hola Valer-IA, ¿cuándo inició Ingenio Manuelita?» (español) | Respondió por texto, empezando con «Por tu seguridad, no compartas números de tarjeta…» | Aviso de seguridad robótico y sin motivo; no hubo nota de voz |
| Ptt 10.00.56 | «Perfecto, ¿puede darme datos de los productos que genera Manuelita?» (español) | Texto con el mismo aviso inicial; bloque «Fuentes:» con un título roto en 15 líneas («Índice 1. 2. 3. …») | Fuentes desordenadas; aviso sin motivo; no hubo nota de voz |
| Ptt 10.08.56 | «Valer-IA, do we know what will be the production of sugar cane for Manuelita in this month?» (inglés) | Aviso en español + respuesta en inglés + encabezado «Fuentes:» en español; [1] y [2] eran la misma fuente | Mezcla de idiomas; fuente repetida; no hubo nota de voz |

En las tres el registro del canal marca la entrada como **texto**, no como nota de voz: por eso nunca se generó
audio. Las tres respuestas abrieron con el mismo aviso de seguridad aunque nadie compartió datos sensibles.

## Clarifications

### Session 2026-11-27

- Q: ¿Cuándo debe aparecer el aviso de seguridad de datos? → A: Solo cuando la persona realmente comparte o
  intenta compartir datos sensibles (tarjetas, documentos, contraseñas); dicho con naturalidad, en su idioma, en
  una sola frase y sin repetirlo en cada mensaje. Nunca como apertura automática.
- Q: ¿Qué idioma usa Valer-IA? → A: El de la consulta (español o inglés), en **todo** el mensaje: respuesta,
  avisos, encabezado de fuentes, invitaciones, confirmaciones y nota de voz.
- Q: ¿Qué es un mensaje «ordenado»? → A: Respuesta en párrafos claros y, al final, un bloque de fuentes con una
  línea por fuente, numeración consecutiva sin huecos ni repetidos y títulos limpios de una sola línea.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Una nota de voz recibe una nota de voz (Priority: P1)

Una persona le habla a Valer-IA por WhatsApp. Recibe una nota de voz natural en su idioma y, aparte, el texto con
la respuesta y sus fuentes, tal como se especificó en la spec 028.

**Why this priority**: Es la falla más visible de las pruebas: las tres notas de voz se respondieron solo por texto.
La demo del sábado se basa en que Valer-IA hable.

**Independent Test**: Enviar desde un teléfono las tres notas de voz de las pruebas (dos en español y una en
inglés) y verificar que cada una recibe nota de voz y texto.

**Acceptance Scenarios**:

1. **Given** una nota de voz en español, **When** Valer-IA responde, **Then** llega una nota de voz en español y un
   mensaje de texto con citas y fuentes.
2. **Given** una nota de voz en inglés, **When** Valer-IA responde, **Then** la nota de voz y el texto están en
   inglés.
3. **Given** una nota de voz, **When** se revisa el registro técnico del canal, **Then** la entrada figura como
   nota de voz y la respuesta como enviada con voz.
4. **Given** una persona que escribe por texto, **When** Valer-IA responde, **Then** responde solo por texto (sin
   cambios frente a la spec 028).

---

### User Story 2 - Un solo idioma de principio a fin (Priority: P1)

Valer-IA responde en el idioma en que le preguntaron, por voz o por texto, sin mezclar idiomas en ninguna parte
del mensaje.

**Why this priority**: El bonus de la sustentación en inglés exige que un invitado que habla inglés reciba todo en
inglés; mezclar idiomas se ve como un error del producto.

**Independent Test**: Enviar el mismo conjunto de preguntas en español y en inglés (texto y voz) y verificar que
cada mensaje de respuesta, incluidos el encabezado de fuentes y cualquier aviso, está en un solo idioma.

**Acceptance Scenarios**:

1. **Given** una pregunta en inglés, **When** Valer-IA responde, **Then** el cuerpo, el encabezado de fuentes
   («Sources:»), las invitaciones a seguir y cualquier aviso están en inglés.
2. **Given** una pregunta en español, **When** Valer-IA responde, **Then** todo está en español («Fuentes:»).
3. **Given** una conversación que cambia de español a inglés, **When** llega la primera pregunta en inglés,
   **Then** esa respuesta ya está completamente en inglés.
4. **Given** una nota de voz en inglés, **When** Valer-IA responde, **Then** la voz y el texto están en inglés.

---

### User Story 3 - El aviso de seguridad solo cuando hace falta y dicho con naturalidad (Priority: P1)

Valer-IA solo recuerda no compartir datos sensibles cuando la persona efectivamente comparte o intenta compartir
uno (número de tarjeta, documento de identidad, contraseña), y lo dice como lo diría una persona, en una frase y
en el idioma de la conversación.

**Why this priority**: Abrir cada respuesta con un aviso que nadie pidió suena robótico y rompe la conversación
natural que es el objetivo de la spec 028.

**Independent Test**: Hacer las tres preguntas de las pruebas y diez preguntas más sin datos sensibles: ninguna
respuesta lleva el aviso. Enviar tres mensajes con datos sensibles ficticios: los tres reciben un aviso breve y
natural, sin repetir el dato.

**Acceptance Scenarios**:

1. **Given** una pregunta sin datos sensibles (texto o voz), **When** Valer-IA responde, **Then** no aparece ningún
   aviso de seguridad.
2. **Given** un mensaje con un número de tarjeta ficticio, **When** Valer-IA responde, **Then** incluye una sola
   frase cordial que pide no compartir ese tipo de datos, sin repetir el dato y sin listas de categorías.
3. **Given** el aviso ya se dio en la conversación, **When** la persona sigue preguntando sin datos sensibles,
   **Then** no se vuelve a dar.
4. **Given** una pregunta en inglés con un dato sensible, **When** Valer-IA responde, **Then** el aviso está en
   inglés.

---

### User Story 4 - Respuestas ordenadas y fuentes limpias (Priority: P1)

Cada respuesta escrita se lee ordenada: párrafos claros y, al final, un bloque de fuentes con una línea por fuente,
numeración consecutiva, sin fuentes repetidas y con títulos legibles de una sola línea.

**Why this priority**: Un bloque de fuentes con títulos rotos («Índice 1. 2. 3. …») o repetidos resta credibilidad
justo en lo que diferencia a Valer-IA: citar sus fuentes. El equipo no acepta mensajes sin orden.

**Independent Test**: Repetir la pregunta de la prueba 10.00.56 y otras nueve con varias fuentes y verificar con
una revisión automática que cada bloque de fuentes cumple el formato.

**Acceptance Scenarios**:

1. **Given** una fuente cuyo título original trae saltos de línea, listas o fragmentos de índice, **When** se arma
   el bloque, **Then** se muestra un título limpio de una sola línea (o el nombre del documento si el título no
   sirve), con página si existe, y el enlace.
2. **Given** dos citas a la misma fuente (mismo documento y página), **When** se arma el bloque, **Then** aparece
   una sola vez y las citas del texto usan el mismo número.
3. **Given** cualquier respuesta con fuentes, **When** se revisa, **Then** los números van de 1 en adelante sin
   huecos, cada línea sigue el mismo formato y no hay líneas vacías ni numeradas sueltas.
4. **Given** una respuesta larga, **When** se divide en varios mensajes, **Then** ningún mensaje corta una fuente a
   la mitad y el bloque de fuentes queda completo y al final.

### Edge Cases

- La nota de voz llega sin transcripción (audio vacío o inaudible): Valer-IA pide repetir, en el idioma de la
  conversación si se conoce, por texto y por voz breve si es posible (spec 028).
- La pregunta mezcla idiomas («What is el ingenio Manuelita?»): se responde en el idioma predominante, uno solo.
- Mensajes muy cortos sin idioma claro («ok», «hola»): se usa el idioma de la conversación; si no hay, español.
- Una fuente no tiene título utilizable ni nombre de documento: se muestra el dominio o el nombre del archivo del
  enlace, nunca una línea vacía.
- Dos fuentes del mismo documento en páginas distintas: se mantienen separadas, cada una con su página.
- Una respuesta sin fuentes (saludo, conversación): no se muestra el encabezado de fuentes.
- La persona comparte un dato sensible por nota de voz: el aviso se da en la respuesta (texto y voz) sin
  pronunciar ni repetir el dato.

## Requirements *(mandatory)*

### Functional Requirements

**Voz (Historia 1)**

- **FR-001**: Una nota de voz de WhatsApp MUST llegar al agente identificada como nota de voz (no como texto), con
  su transcripción y el idioma detectado.
- **FR-002**: Toda respuesta a una nota de voz MUST incluir una nota de voz y el texto con fuentes, según la spec
  028; si la voz falla, el texto llega igual y la falla queda registrada.
- **FR-003**: El registro técnico del canal MUST permitir verificar, sin texto ni números, que la entrada fue voz y
  que la respuesta llevó voz.

**Idioma (Historia 2)**

- **FR-004**: Valer-IA MUST responder en el idioma de la consulta (español o inglés), por texto o por voz.
- **FR-005**: Todo el contenido de una respuesta MUST estar en un solo idioma: cuerpo, avisos, encabezado de
  fuentes («Fuentes:»/«Sources:»), invitaciones, confirmaciones, mensajes del canal y nota de voz.
- **FR-006**: El idioma de cada turno MUST decidirse sobre la consulta de ese turno (con la conversación como
  respaldo para mensajes muy cortos), de modo que un cambio de idioma se respete desde el primer mensaje.

**Aviso de seguridad (Historia 3)**

- **FR-007**: El aviso de no compartir datos sensibles MUST aparecer solo cuando el mensaje de la persona contiene
  o intenta compartir datos sensibles reales (tarjetas, documentos de identidad, contraseñas).
- **FR-008**: El aviso MUST ser una sola frase cordial, en el idioma de la conversación, integrada a la respuesta,
  sin enumerar categorías, sin repetir el dato y sin afirmar acciones que no ocurrieron.
- **FR-009**: El aviso MUST darse como máximo una vez por conversación, salvo que la persona vuelva a compartir
  datos sensibles.
- **FR-010**: Los metadatos técnicos de una nota de voz (marcas, identificadores, rutas) MUST NOT activar el aviso.

**Orden y fuentes (Historia 4)**

- **FR-011**: El bloque de fuentes MUST tener una línea por fuente con el formato «[n] Título, p. X — enlace» (la
  página solo si existe), numeración consecutiva desde 1 y el encabezado en el idioma de la respuesta.
- **FR-012**: Los títulos de fuente MUST mostrarse limpios: una sola línea, sin saltos, listas, numeraciones de
  índice ni fragmentos de texto, de 80 caracteres como máximo; si el título no es utilizable se usa el nombre del
  documento o del archivo del enlace.
- **FR-013**: Las citas a la misma fuente (mismo enlace y página) MUST unificarse en un solo número, también en el
  texto de la respuesta.
- **FR-014**: El cuerpo de la respuesta MUST presentarse en párrafos separados y sin líneas vacías o numeradas
  sueltas; al dividir en varios mensajes, ningún corte parte una fuente y el bloque de fuentes queda al final.
- **FR-015**: El proyecto MUST incluir una revisión automática del formato de las respuestas del canal (idioma
  único, bloque de fuentes, ausencia de aviso sin motivo) que se ejecute en las pruebas y sobre las respuestas
  reales de una corrida de verificación.

### Key Entities

- **Mensaje entrante**: texto o nota de voz; para la voz, transcripción e idioma detectado.
- **Idioma del turno**: español o inglés, decidido sobre la consulta del turno.
- **Aviso de seguridad**: frase opcional ligada a la detección real de datos sensibles en el mensaje de la persona.
- **Fuente presentada**: número, título limpio, página opcional y enlace; única por enlace y página.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Las tres notas de voz de las pruebas del 2026-11-27, repetidas desde un teléfono, y siete más
  (≥ 3 en inglés) reciben nota de voz y texto: 10/10.
- **SC-002**: En un conjunto de 20 consultas (10 en español y 10 en inglés, texto y voz), 0 respuestas mezclan
  idiomas en ninguna parte del mensaje.
- **SC-003**: En ese mismo conjunto, sin datos sensibles, 0 respuestas incluyen el aviso de seguridad; en 3
  mensajes con datos sensibles ficticios, 3/3 lo incluyen una sola vez, en una frase y sin repetir el dato.
- **SC-004**: El 100 % de los bloques de fuentes del conjunto pasa la revisión de formato: una línea por fuente,
  numeración consecutiva, sin repetidos y títulos limpios de ≤ 80 caracteres.
- **SC-005**: La pregunta de la prueba 10.00.56 («datos de los productos que genera Manuelita») produce un bloque de
  fuentes sin títulos rotos, y la de la prueba 10.08.56 no repite la misma fuente con dos números.
- **SC-006**: Las mediciones vigentes no bajan: exactitud de herramientas ≥ 90,7 % y escudo del canal 20/20.

## Assumptions

- La transcripción de las notas de voz funciona (las tres pruebas fueron entendidas correctamente); la falla está en
  cómo la nota de voz llega identificada al agente y en la presentación de la respuesta.
- El aviso de seguridad se conserva como protección cuando la persona comparte datos sensibles; lo que cambia es
  cuándo aparece y cómo se dice.
- Solo español e inglés; cualquier otro idioma se atiende en español (spec 028).
- Las correcciones entran en la misma entrega que la spec 028, antes de la sustentación del sábado 28 de noviembre de
  2026, y se verifican con el teléfono de prueba en modo cerrado.
- Las respuestas reales de las pruebas (`C:\Users\JCastano\Downloads\pruebas valeria`) sirven de casos de regresión;
  los audios no se versionan.

## Dependencies

- Spec 028 (canal natural con voz) y spec 024 (canal y formato de WhatsApp).
- Gateway, backend y SIM vinculada en el portátil servidor (ya en verde).
