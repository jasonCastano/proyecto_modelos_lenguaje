# Research: Valer-IA Caña con habilidades de agente de call center (spec 019)

Decisiones de diseño R1–R16. Cada una indica qué se eligió, por qué y qué alternativas se descartaron.

## R1. Respuestas fuera de alcance compuestas desde guiones, sin LLM

**Decision**: las respuestas a temas ajenos, consejos profesionales y pedidos no atendibles se **componen** en un
módulo determinista (`agent/care.py`) a partir de guiones versionados (`prompts/care.md`). Cada respuesta une cinco
piezas:

1. apertura según la emoción, si aplica;
2. reconocimiento del tema concreto («Entiendo que quieres saber del clima en Cali»);
3. límite breve y cordial;
4. puente a un tema de Manuelita, con su cita al oro;
5. pregunta de cierre.

Cada pieza tiene de 2 a 4 variantes y se rotan por hilo.

**Rationale**:
- SC-001 exige que el 100 % de las respuestas no tenga hechos externos. Con texto compuesto solo de guiones, eso se
  garantiza por construcción.
- No suma latencia (SC-010) y funciona igual en modo demo y real (FR-027).
- La variedad sale del tema mencionado, de las variantes y de la rotación (FR-002, SC-002).
- Continúa el enfoque de la spec 018: la seguridad no depende del modelo.

**Alternatives considered**:
- *LLM que redacta la declinación con un validador de salida*: suena más natural, pero detectar "hechos externos" en
  texto libre no es verificable al 100 %. Además suma una llamada al modelo por turno y en demo no habría paridad.
  Queda como mejora futura.
- *Mantener `conduct.md` con una sola frase por motivo*: es justo lo que el usuario rechaza.

## R2. Catálogo de temas ajenos y tema libre del enrutador

**Decision**:
- `care.py` define un catálogo `TOPICS`. Cada tema tiene clave, etiqueta en español, patrón normalizado y puente
  preferido. Los temas son: clima, deportes, política, finanzas externas, programación, cocina/recetas, tareas
  escolares, entretenimiento, viajes, tecnología, otras empresas y salud. Salud se trata como consejo.
- Los patrones de `OUT_OF_SCOPE_PATTERNS` del enrutador migran a este catálogo.
- Si el enrutador LLM clasifica `off_topic` sin coincidencia en el catálogo, el JSON trae un campo opcional
  `topic`. Se sanea: minúsculas, solo letras y espacios, como máximo 4 palabras y 40 caracteres, y pasa por
  `redact_pii`. Si no supera el saneamiento, se usa la etiqueta genérica «ese tema».

**Rationale**: con reglas se cubren los temas frecuentes sin llamar al modelo. El campo `topic` permite nombrar
cualquier tema en modo real sin abrir una vía de inyección, porque la etiqueta saneada no puede llevar instrucciones
ni datos personales.

**Alternatives considered**:
- *Insertar la frase original del visitante*: riesgo de repetir insultos, datos personales o inyecciones.
- *Solo reglas*: los temas no previstos terminarían en «ese tema» también en modo real.

## R3. Detección de emoción por reglas, con apoyo opcional del enrutador

**Decision**:
- `care.detect_sentiment(message)` clasifica el mensaje en uno de seis estados (`neutral`, `satisfied`, `confused`,
  `frustrated`, `angry`, `distressed`) con léxicos normalizados en español colombiano.
- También devuelve tres banderas: `hostile` (insultos), `rejection` («eso no me sirve», «no me ayudaste») y
  `sarcasm` (ironía, por ejemplo «gracias por nada» o «excelente servicio… no»).
- El sarcasmo convierte un elogio aparente en `frustrated`.
- Cuando el enrutador usa el LLM, su JSON puede traer `sentiment`. Solo se acepta si las reglas dieron `neutral`.

**Rationale**: es determinista, rápido, probado sin red y funciona igual en demo (FR-006). El LLM solo refina los casos
que las reglas no ven.

**Alternatives considered**:
- *Clasificador de sentimiento entrenado*: añade una dependencia y peso al servidor sin una ganancia clara para
  6 clases en un chat corto (Principio VII).
- *Solo LLM*: en demo no habría detección y los turnos decididos por reglas no la tendrían.

## R4. Apertura empática determinista antepuesta en `finalize`

**Decision**:
- Si la emoción es `frustrated`, `angry` o `confused`, o el mensaje es una crítica a la empresa (`concern`), el nodo
  `finalize` antepone una frase de apertura tomada de `care.md`. Es el mismo mecanismo del aviso de datos sensibles
  de la spec 018.
- Aplica en todas las rutas.
- Los prompts del agente y de la cadena le indican al modelo que **no** abra con su propia frase empática, para que
  no se duplique.

**Rationale**: garantiza SC-003 en los dos modos y en las dos variantes. La apertura queda como primera frase, que es
lo primero que se escucha con la voz (spec 016).

**Alternatives considered**:
- *Pedirle al LLM que reconozca la emoción*: no es verificable en demo y el cumplimiento varía.

## R5. Crisis: motivo nuevo `crisis`, con prioridad sobre todo lo demás

**Decision**:
- Patrones de angustia grave o autolesión, como «quiero morirme», «no quiero vivir», «hacerme daño» o «suicid*».
  Se evalúan **antes** que los de conducta.
- La ruta es `out_of_scope` con `scope_reason="crisis"`. La respuesta determinista empática no lleva puente ni
  contenido comercial e incluye:
  - **Línea 106**: línea nacional de salud mental del Ministerio de Salud y Protección Social, gratuita, confidencial
    y 24/7;
  - **123**: emergencias.
- Si el mensaje mezcla crisis y una pregunta sobre Manuelita, prima la crisis. La pregunta no se responde en ese turno.

**Rationale**: FR-010 y SC-005. La Línea 106 figura en la página oficial del Ministerio
(minsalud.gov.co/salud/publica/salud-mental/Paginas/linea-106.aspx), consultada el 2026-11-17. La línea 192 opción 4
fue un canal de la pandemia (2020) y no se usa porque no hay certeza de que siga activa.

**Alternatives considered**:
- *Recomendar solo "servicios de emergencia"*: es el respaldo previsto en la spec si la verificación fallara. Como la
  106 está verificada, se usa la 106.
- *Responder la pregunta de Manuelita además del apoyo*: trivializa la crisis.

## R6. Insultos: límite cordial sin abandonar la atención

**Decision**:
- El motivo `abuse` determinista se conserva solo cuando el mensaje es **únicamente** hostil, es decir, cuando al
  quitar los insultos no queda una consulta.
- Si hay insulto y además consulta, el turno sigue su ruta normal con `hostile=True`, y `finalize` antepone un límite
  breve tomado de `care.md`, sin repetir el insulto.
- Las respuestas escalan por número de turnos hostiles en el hilo:
  - nivel 1: límite y ofrecimiento;
  - nivel 2: límite con alternativa;
  - nivel 3 o más: cierre cordial que deja la puerta abierta.
- La conversación nunca se bloquea.

**Rationale**: cumple FR-008 y el caso límite de insulto con pregunta válida, y mantiene la seguridad de la spec 018
(FR-005).

## R7. Varias solicitudes en un mensaje (multitarea)

**Decision**:
- `care.split_requests(message)` separa hasta 5 solicitudes. Corta por signos de interrogación, «;», saltos de línea,
  enumeraciones y conectores como «y también», «además» o «otra pregunta». Si hay más de 5, se atienden las primeras
  5 y se invita a seguir.
- Cada parte se clasifica en `manuelita`, `off_topic`, `advice` o `unattainable` con las mismas reglas.
- **Cadena**: `retrieve` busca por cada parte de Manuelita, reparte el `top_k` y fusiona la evidencia sin duplicados.
  El mensaje al modelo lista las solicitudes numeradas, y el prompt pide responderlas en orden, cada una con su
  evidencia.
- **Agente**: el system prompt lleva la misma lista. El agente puede llamar varias veces a las herramientas.
- Las partes ajenas reciben una declinación compuesta (R1), corta, que se añade al final de la respuesta.
- La métrica SC-006 se evalúa por solicitud.

**Rationale**: FR-003, FR-013 y SC-006. Sigue siendo una sola llamada al modelo de respuesta: la búsqueda léxica extra
es barata (SC-010).

**Alternatives considered**:
- *Una sub-respuesta del LLM por parte*: multiplica la latencia y el costo.
- *Dejar que el LLM descubra las partes*: no se cumple en demo y no se puede medir por solicitud.

## R8. Pedidos no atendibles: motivo `unattainable` con tipo

**Decision**:
- Motivo nuevo `unattainable` con `kind`:
  - `pricing`: precios, descuentos, cotizaciones, comprar;
  - `commitment`: «garantízame», «prométeme», reembolsos, empleo garantizado;
  - `human`: «quiero hablar con una persona», «pásame con un asesor».
- Las respuestas se componen desde `care.md`:
  1. lo que no puede ofrecer;
  2. lo que sí puede ofrecer;
  3. los canales oficiales **que existan en el corpus**, con cita;
  4. una pregunta.
- Si el corpus no tiene un canal para el tema (ventas, empleo), se dice con honestidad y se sugiere el sitio web
  oficial, que tiene cita.
- Las preguntas informativas siguen en la ruta documental: «¿Manuelita tiene programas de empleo?» o «¿a quién le
  vende?».

**Canales verificados en el oro (2026-11-17)**:
- **Sitio web oficial www.manuelita.com**: unidades del sitio, por ejemplo `/alimenticio`.
- **Línea Ética**: «servicio de información, anónimo e independiente, para comunicar todo hecho irregular»
  (`unit_041ccaa4fc001330`, `unit_0790df213985da99`). Se usa para denuncias de irregularidades.
- **protecciondedatos@manuelita.com**: consultas y reclamos de Habeas Data (`unit_04332ad427df77f2`). Se usa para
  temas de datos personales.

No hay en el oro un canal de ventas, servicio al cliente ni empleo con datos de contacto. No se inventan.

**Rationale**: FR-016 y FR-018, SC-007 y la Constitución IV (generación anclada).

## R9. Resiliencia: memoria de atención por hilo

**Decision**:
- El estado del hilo gana `care`. Guarda:
  - cuántas veces se usó cada clave de guion y la última variante;
  - cuántas quejas o rechazos seguidos hubo;
  - cuántas aclaraciones seguidas hubo;
  - cuántos turnos hostiles hubo.
- La rotación nunca repite la última variante.
- Con `rejection` o una queja repetida, se elige una alternativa **distinta** de la anterior. El orden es: otra forma
  de preguntar, temas relacionados y canal oficial.
- En la tercera queja seguida se reconoce que el problema sigue sin resolverse y se ofrece el canal oficial.

**Rationale**: FR-009, US2 escenario 3 y US4 escenario 2. Vive en el checkpointer, igual que el resto del hilo, y no
contiene texto del visitante.

## R10. Aclaración única y luego la mejor interpretación

**Decision**:
- La respuesta `clarify` se compone con 2 o 3 opciones concretas de `care.md`. Las elige el tema detectado; si no
  hay tema, usa unas genéricas: historia, productos y sostenibilidad.
- Si el turno anterior fue `clarify` y el actual vuelve a ser ambiguo, el nodo `route` usa la ruta alternativa del
  enrutador, o `documental` si no hay alternativa.
- En ese caso, `finalize` añade «Si te referías a otra cosa, dime y lo ajusto».

**Rationale**: FR-012 y el caso límite de ambigüedad repetida.

## R11. Parafraseo cuando hubo confusión

**Decision**:
- Cuando el turno anterior fue `clarify` o `fallback`, o hay una queja repetida, el brief de atención pide al modelo
  que empiece retomando en una frase lo que entendió.
- En demo, el modelo guionizado antepone «Entiendo que buscas información sobre {tema}». El tema es el `topic_id`
  del oro de la evidencia principal.

**Rationale**: FR-015. El parafraseo es lenguaje natural y le corresponde al modelo. En demo se mantiene la paridad
con una versión determinista.

## R12. Claridad verbal en los prompts y verificación de forma

**Decision**: `prompts/agent.md` (v1.5) y la sección de respuesta de la cadena reciben reglas de forma:
- idea principal en la primera frase;
- frases cortas;
- pasos numerados solo para procesos;
- sin tablas ni encabezados;
- como máximo unas 120 palabras por solicitud;
- tuteo cordial;
- sin abrir con empatía, porque la apertura la pone el sistema.

La batería verifica la forma con reglas: sin tablas, sin encabezados y con la primera frase de 30 palabras o menos.

**Rationale**: FR-014 y la "sonrisa telefónica" aplicada a la voz de la spec 016, que ya limpia el texto para TTS.

## R13. Registro del contacto (CRM) en el estado del hilo

**Decision**:
- `ContactRecord` vive en `ChatState["contact"]` (checkpointer, por hilo) y lo actualiza `finalize` de forma
  determinista.
- Cada solicitud registra la categoría, el estado, el tema y el turno.
- El tema es **siempre una etiqueta controlada**:
  - para solicitudes de Manuelita, el `topic_id` del oro de la evidencia principal;
  - para temas ajenos, la clave del catálogo, o `otro` si el tema vino libre del LLM.
- Nunca se guarda texto del visitante. Esto garantiza FR-022 y SC-009 por construcción.
- El registro se expone en `ChatResponse.contact`, que es opcional, y en la vista del hilo. La interfaz solo lo
  muestra en la vista técnica.
- Al reiniciar se crea un hilo nuevo, y por tanto un registro nuevo (FR-025). El registro no guarda `user_id` ni
  huella.

**Alternatives considered**:
- *Tabla aparte en el Store por usuario*: liga el registro al visitante, que FR-025 pide evitar, y duplica el
  checkpointer.
- *Resumen libre generado por el LLM*: puede filtrar datos personales.

## R14. Batería `agent care` y reporte agregado

**Decision**: nuevo subcomando `agent care --mode demo|real [--variants chain agent] [--json-out]`, análogo a
`agent conduct`. Usa `tests/fixtures/care/care_cases.jsonl` con unos 36 casos, de un turno y de varios turnos. Cada
caso declara verificaciones automáticas:
- `mentions`: el tema;
- `forbidden`: hechos externos o frases prohibidas;
- `opener`: emoción reconocida en la primera frase;
- `no_echo`: no repetir el insulto;
- `crisis_lines`;
- `no_invented_contacts`: todo teléfono o correo debe estar en la lista blanca de canales citados;
- `parts_answered`: varias solicitudes;
- `distinct`: textos distintos entre casos.

Además, agrega los `ContactRecord` en totales por categoría y sentimiento, proporción de resueltas, crisis y hostilidad
(FR-024).

La batería escribe `docs/evaluacion_atencion.{md,json}`, con una sección para la calificación humana (SC-011) y la
comparación de latencia (SC-010): `--baseline` corre el mismo conjunto con `[care] enabled = false`.

## R15. Guiones versionados (`prompts/care.md`) y verificación contra el oro

**Decision**:
- `care.md` usa el formato de secciones de `conduct.md`, leído con `load_sections`, con listas de variantes.
- Los puentes y canales declaran la cita como `unit | url | title`, igual que `welcome.md`.
- Hay dos pruebas:
  - una valida que cada unidad citada exista en el oro y que todo teléfono, correo o URL del guion aparezca en el
    texto o la URL de su unidad; se omite si el oro es un puntero LFS, como en CI;
  - otra valida la estructura: secciones obligatorias, de 2 a 4 variantes y placeholders conocidos.
- Cada cambio se registra en `docs/prompt_log.md` (FR-019, FR-020).

## R16. Configuración y compatibilidad

**Decision**:
- `config/agent.toml` gana `[care]` con:
  - `enabled = true`;
  - `max_requests = 5`;
  - `hostility_levels = 3`;
  - `complaint_escalation = 3`.
- `RouteDecision` gana `topic`, `sentiment` y `kind`, todos opcionales y saneados.
- El enrutador gana el motivo `crisis` y `unattainable`.
- `ChatResponse` gana `contact`, opcional. Los clientes de la spec 018 siguen siendo compatibles.
- Los casos de la batería de conducta para `off_topic` y `advice` se actualizan: en vez de comparar el texto exacto,
  verifican el motivo y la ausencia de fugas. Los motivos de seguridad conservan la comparación exacta (SC-008).
