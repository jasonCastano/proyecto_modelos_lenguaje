# Research: Respuesta por voz sin texto duplicado (spec 030)

Sin `NEEDS CLARIFICATION` en el contexto técnico. Las decisiones salen del flujo actual del canal (specs 024, 028 y
029) y de lo observado en las pruebas del 2026-11-27 (13:26 y 13:31).

## R1. Quién decide qué texto se entrega

- **Hallazgo**:
  - El backend (`ChannelBridge.handle` → `_attach_voice`) genera la nota de voz y devuelve `messages` (respuesta
    completa con fuentes) más `voice`.
  - El plugin `valeria-bridge` envía primero la voz y después entrega `messages` como texto.
  - Solo el plugin sabe si la voz **se entregó** (adaptador del canal o CLI de respaldo).
- **Decision**:
  - El backend devuelve dos versiones del texto:
    - `messages`: la respuesta completa con fuentes, sin cambios; es el respaldo de FR-004 y FR-005.
    - `sources_messages`: solo el bloque de fuentes en el idioma del turno; lista vacía si no hay fuentes.
  - El plugin entrega `sources_messages` si la voz se envió; si no, entrega `messages`.
  - Sin voz en la respuesta (`voice: null`), entrega `messages` como hoy.
- **Rationale**:
  - La decisión queda donde está el dato (resultado del envío).
  - El contrato sigue siendo compatible: el campo nuevo es opcional y un plugin anterior seguiría enviando
    `messages`.
- **Alternatives considered**:
  - El backend envía solo las fuentes. Descartado: si la entrega de la voz falla, la persona se queda sin respuesta
    (viola FR-005).
  - El plugin recorta el texto buscando «Fuentes:». Descartado: es frágil con dos idiomas, con fuentes sintéticas y
    con bloques partidos en varios mensajes.

## R2. Envío de la voz: síncrono y con resultado

- **Hallazgo**: con la spec 029 la voz se envía por el adaptador del canal (≈1–3 s). Si ese camino falla, el CLI
  corre en segundo plano (~46 s de arranque) y su resultado se conoce tarde.
- **Decision**:
  - `sendVoice` devuelve si la nota quedó **entregada**.
  - Con el adaptador del canal, la confirmación es su resolución sin error.
  - Si el adaptador falla, el plugin entrega `messages` (respuesta completa) de inmediato y deja el CLI como intento
    adicional en segundo plano.
- **Rationale**:
  - Nunca se deja a la persona solo con enlaces.
  - En el peor caso recibe el texto completo y, quizá después, también la voz: redundante, pero nunca incompleto.
- **Alternatives considered**: esperar al CLI antes de responder. Descartado: más de 45 s de espera adicional.

## R3. Frase de cierre de la voz (historia 3, FR-007)

- **Decision**: frase determinista añadida al final del guion hablado solo cuando la respuesta tiene fuentes:
  - es: «Te dejo las fuentes por escrito.»
  - en: «I've left the sources for you in writing.»
- **Rationale**:
  - El guion del modelo no siempre la incluiría.
  - Una frase fija es verificable en pruebas y no introduce hechos nuevos.
  - `valid_script` sigue validando las cifras del guion contra la respuesta, y la frase no tiene cifras.
- **Alternatives considered**: pedirla en `prompts/voice_script.md`. Descartado como único mecanismo, porque el
  respaldo determinista (`fallback_script`) no pasa por el prompt.

## R4. Bloque de fuentes solo, numeración y división

- **Decision**:
  - Nueva función `sources_only(answer, citations, language, max_chars)` en `channels/format.py`.
  - Reutiliza `number_citations` (mismo orden y deduplicación de la spec 029) y `sources_block`.
  - Parte por líneas completas: si el bloque supera `max_chars`, los mensajes siguientes continúan con líneas enteras
    y sin repetir el encabezado.
- **Rationale**: un solo formato de fuentes para texto y voz, y los números coinciden con los del texto completo de
  respaldo.

## R5. Registro (FR-009) y revisión de formato (FR-008)

- **Decision**:
  - **Registro**:
    - El registro del canal (`channels.jsonl`) añade `written`: `full` | `sources` | `none`, con lo que el backend
      dejó listo para el caso de voz entregada.
    - El plugin registra en el log del gateway cuando cae a la respuesta completa
      (`voz no entregada: texto completo`).
  - **Revisión**: `quality.review_reply(..., voice=True)` marca `voice_text_duplicate` si algún mensaje tiene
    oraciones fuera de bloques de fuentes; un turno con voz cuyo texto es solo fuentes (o vacío) es conforme.
  - **Simulador**: `pml channels simulate --check` usa `sources_messages` cuando la respuesta trae voz.
- **Rationale**: verificable sin leer contenido; el log del gateway no lleva texto.

## R6. Casos de regresión

- **Decision**: las dos respuestas reales (13:26 y 13:31), con solo el texto de Valer-IA, se versionan en
  `tests/fixtures/channels/regression_2026-11-27b.jsonl`. Con `voice=True` deben **fallar** la revisión
  (`voice_text_duplicate`); su bloque de fuentes aislado debe **pasar**. Los audios no se versionan.
