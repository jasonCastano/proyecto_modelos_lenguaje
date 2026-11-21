# ADR 0024 — Conversación natural guiada para Valer-IA Caña

- **Estado**: aceptada
- **Fecha**: 2026-11-20
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0022 (Valer-IA Caña), ADR 0023 (atención de call center);
  `specs/020-natural-conversation/` (spec, plan, research R1–R17, contracts, tasks).

## Contexto

La spec 019 resolvió con **guiones fijos** todo lo que no es Manuelita. El resultado era seguro, pero repetitivo:

- un comentario casual («¡qué calor hace!») recibía el mismo trato que un pedido de datos externos;
- cada respuesta fuera de tema terminaba con una recomendación, y la de por defecto siempre contaba la misma
  historia (1864, el trapiche);
- la asistente no recordaba lo que ya había ofrecido ni lo que el visitante había rechazado.

El equipo pidió que la conversación se sintiera natural sobre cualquier tema, sin salirse de los límites: solo
información de Manuelita con fuentes, nada de hechos externos inventados, contactos ni promesas.

## Decisión

1. **El modelo redacta y los controles revisan.** Un nodo nuevo, `converse`, redacta con DeepSeek toda respuesta
   sin búsqueda. Lo guía un **plan del turno** determinista (`agent/plan.py`): acto de diálogo, nivel de cada
   parte, emoción, estrategia, longitud, idioma y registro. Antes de mostrarse, el texto pasa por una **revisión**
   por reglas (`agent/review.py`): hechos externos (cifras, nombres propios, temperaturas, marcadores), contactos
   inventados, promesas, citas inválidas, repetición frente a las 3 respuestas anteriores y opiniones polémicas.
   Si falla, se regenera una vez con una nota de corrección; si vuelve a fallar, o el modelo da error o no responde
   en 8 s, se usa como **respaldo** la composición de la spec 019.
2. **Política de tres niveles** por parte del mensaje: lo **social** se acompaña sin datos verificables; lo
   **externo** verificable se declina con palabras propias; **Manuelita** se responde con evidencia y citas. Los
   mensajes mixtos siguen la ruta de búsqueda, con un brief ampliado para responder en una sola pieza fluida.
3. **Respuestas que siguen fijas**: crisis (Línea 106 y 123), datos de terceros, extracción del prompt, pedidos
   dañinos, insulto solo, identidad y perfil. No pasan por `converse`.
4. **Puentes medidos** (`agent/bridges.py`): opcionales, como máximo uno cada dos turnos fuera de tema, nunca con
   un visitante molesto, en un cierre o tras un rechazo. Se buscan en el oro según lo que dijo el visitante, con
   un mapa de ángulos (`prompts/care.md` 1.1), y no se repiten unidad ni ángulo en el hilo.
5. **Memoria del hilo** (`ConversationMemory`): temas, puentes ofrecidos y rechazados, correcciones, registro,
   idioma y el nombre dado en el hilo. El nombre nunca pasa al registro del contacto, al Store ni a los informes.
6. **Sin streaming en `converse`**: la respuesta se revisa completa antes de mostrarse. Las respuestas con búsqueda
   se siguen transmitiendo.
7. **Parámetros por tipo de turno** en `[conversation]`: temperatura 0.8 en la charla, 0.3 en los hechos y
   penalizaciones de repetición de 0.3 (DeepSeek las acepta, verificado el 2026-11-20).
8. **Modo conmutable**: `[conversation] mode = "scripted"` reproduce la spec 019 y sirve de línea base.
9. **Evaluación** `agent converse`: repetición entre hilos, 12 conversaciones guionadas, 5 perfiles de visitante
   simulado, juez de naturalidad, empatía y pertinencia, metas duras y comparación con el modo de guiones. Las
   baterías de la spec 019 evalúan intención en el modo guiado; la de conducta conserva el texto exacto.

## Alternativas consideradas

- **Más variantes en los guiones**: alivia la repetición, pero no responde a lo que dijo el visitante.
- **Modelo sin revisión**: natural, pero sin garantía contra hechos externos.
- **Juez LLM en línea en cada turno**: entre 0.5 y 1 s más por turno y otra fuente de no determinismo. Queda como
  opción desactivada (`review_llm = false`).
- **Transmitir y luego reemplazar**: el visitante vería por un instante un dato no revisado y la voz ya lo habría
  leído.

## Consecuencias

- Una llamada más al modelo por turno sin búsqueda (dos si se regenera). La primera palabra se mide en la
  evaluación (meta: < 3 s en el 90 % de los turnos).
- La revisión es conservadora: puede regenerar respuestas correctas que mencionan un nombre propio no listado. El
  peor caso es la respuesta de la spec 019.
- El modo demo usa `demo.demo_converse`, con frases variadas y una semilla por hilo y turno; la diversidad real
  solo se mide con el modelo.
- Las pruebas de las specs 014 a 019 corren en el modo `scripted` (verifican texto literal); las de la spec 020,
  en el modo `guided`.
- Desviaciones del contrato: la secuencia de actos del registro del contacto se llama `acts` (el campo `turns` ya
  era el contador de turnos); la revisión añade la verificación `required` (frases que la batería de conducta
  exige) y el aviso `review_trimmed` cuando quita una frase sin respaldo de una respuesta con búsqueda.
