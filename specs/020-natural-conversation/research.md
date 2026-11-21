# Research: Conversación natural guiada (spec 020)

Decisiones de diseño para [spec.md](./spec.md). Cada una indica qué se decidió, por qué y qué alternativas se
descartaron. Parten del código en `main` después de la spec 019 (`d9374fb`).

## Diagnóstico de partida

Por qué la conversación se siente repetitiva hoy:

| Causa | Dónde | Efecto |
|-------|-------|--------|
| Lo ajeno se resuelve por reglas sin LLM | `router.rule_decision` → `_care_decision`; `graph.reply_node` → `care.compose_out_of_scope` | Frases preescritas para todo lo que no es Manuelita |
| Puente obligatorio en cada respuesta fuera de tema | `care.compose_out_of_scope` | Recomendación en cada turno |
| `bridge.default` con 2 variantes de la misma unidad (1864) | `prompts/care.md` | Lo que no está entre los 14 temas del catálogo siempre recibe la misma historia |
| La rotación solo evita repetir dentro del hilo | `care.pick` + `CareState.last_variant` | Entre hilos se repiten las mismas frases |
| Temperatura 0.0–0.1 | `config/agent.toml [router]`, `config/llm.toml` | Respuestas casi idénticas ante entradas parecidas |
| La evaluación exige texto literal | `tests/fixtures/care/care_cases.jsonl`, `conduct_cases.jsonl` | Cualquier variación natural cuenta como fallo |
| Sin memoria de lo ofrecido o rechazado | `CareState` solo guarda rachas y la última variante | Se repiten las ofertas |

## R1. Principio: el modelo redacta y los controles revisan

**Decision**: En el modo `guided`, toda respuesta sin búsqueda la redacta el LLM en un nodo nuevo, `converse`. Lo
guía un **plan del turno** que se calcula de forma determinista. Antes de mostrarse, la respuesta pasa por una
**revisión** (`review.py`). Las reglas de la spec 019 siguen calculando las señales (emoción, hostilidad, rechazo,
crisis, partes del mensaje), pero ya no escriben el texto, salvo en los casos de seguridad (R2).

**Rationale**: Es la única forma de que la respuesta dependa del mensaje concreto. Las garantías de la spec 019
(cero hechos externos, sin contactos inventados, sin promesas) dejan de depender de que el texto esté preescrito y
pasan a depender de que se revise antes de mostrarlo. Si la revisión falla, se usa el guion (R9), así que en el peor
caso el resultado es el de la spec 019.

**Alternatives considered**:
- *Más variantes en `care.md`*: alivia la repetición, pero sigue sin responder a lo que dijo el visitante. Habría que
  escribir cientos de frases.
- *LLM sin revisión*: natural, pero rompe SC-005 sin forma de garantizarlo.
- *Parafrasear el guion con el LLM*: suena menos rígido, pero sigue anclado a la plantilla y no maneja comentarios
  sociales ni bromas.

## R2. Qué sigue siendo fijo

**Decision**: Conservan su respuesta determinista y su prioridad, sin pasar por `converse`:
- `crisis` (Línea 106 y 123);
- `third_party`, `prompt_extraction` y `harmful` (spec 018);
- `abuse` cuando el mensaje es **solo** un insulto (los niveles `hostility.N` de la spec 019);
- los flujos de identidad de la spec 018 (`identify`, `remember`) y las acciones con aprobación (HITL);
- la respuesta de perfil («¿qué sabes de mí?»).

**Rationale**: Son casos de seguridad o de privacidad en los que la variación no aporta valor y sí aporta riesgo. La
batería de conducta (24/24) los verifica con texto exacto y así debe seguir (SC-006).

**Alternatives considered**: Redactar también la crisis con el LLM. Se descarta porque una respuesta de crisis debe
ser predecible y verificada.

## R3. Política de contenido en tres niveles

**Decision**: Cada parte del mensaje (`care.split_requests`) recibe un nivel (`tier`):

| Nivel | Regla de clasificación | Qué puede hacer la respuesta |
|-------|------------------------|------------------------------|
| `social` | Afirmación, exclamación, saludo, risa o emoji sin pedido de datos. Ejemplos: «qué calor», «estoy haciendo una tarea», «jaja» | Acompañar, empatizar o comentar en términos generales, sin cifras, fechas, nombres ni resultados |
| `external` | Pedido (pregunta o imperativo) de un tema del catálogo o de cualquier tema sin `COMPANY` | Declinar con palabras propias, sin inventar nada. Puede ofrecer un puente (R5) |
| `manuelita` | Mención de la empresa o de los temas del oro, como hasta ahora | Responder con evidencia y citas |

`care.analyze` asigna el nivel con las mismas reglas léxicas (`QUESTION`, el imperativo y `match_topic`), más un
léxico nuevo de comentario social. Si el enrutador LLM interviene, puede proponer `tier` y `act` (R4).

**Rationale**: Hoy «qué calor hace» y «¿qué temperatura hará mañana?» reciben el mismo trato. La distinción entre
afirmar y pedir es la frontera más simple que permite acompañar lo social sin abrir la puerta a los datos externos.
Lo que la respuesta no puede afirmar lo controla la revisión (R8), no la clasificación.

**Alternatives considered**: Un clasificador LLM aparte para el nivel. Se descarta porque añade una llamada por turno
(latencia); el enrutador LLM ya existe para los casos ambiguos.

## R4. Plan del turno y acto de diálogo

**Decision**: Un `TurnPlan` determinista, calculado en el nodo `route` a partir de las señales de `care`, la decisión
del enrutador y la memoria del hilo (R6). Contiene:
- `act`: el acto de diálogo dominante. Puede ser `greeting`, `smalltalk`, `off_topic`, `manuelita`, `complaint`,
  `correction`, `minimal`, `about_assistant`, `closing`, `thanks` o `clarify`.
- `tiers`: el nivel de cada parte.
- `sentiment`.
- `strategy`: una o varias de `accompany`, `empathize`, `decline`, `answer`, `clarify`, `limit` y `farewell`.
- `bridge`: si se permite un puente y cuál (R5).
- `length`: `short` (hasta 2 frases), `medium` o `long`.
- `language` y `register`.

Las reglas detectan los actos nuevos con léxicos:
- `minimal`: «ok», «jaja», emojis, «mmm»;
- `closing`: «listo, gracias, eso era todo», «chao»;
- `correction`: «no, me refería a…», «quise decir»;
- `about_assistant`: «¿eres humana?», «¿qué puedes hacer?».

`prompts/router.md` 1.5 añade `act` como campo opcional para los casos que decide el LLM.

**Rationale**: El plan separa *qué hacer* de *cómo decirlo*. Lo primero es verificable con reglas y pruebas sin red;
lo segundo lo aporta el modelo. El plan no contiene texto del visitante, así que puede entrar al registro del contacto.

**Alternatives considered**: Dejar que el modelo decida todo con un prompt largo. Sería menos predecible, sin forma
de probar la cuota de puentes ni los silencios tras un rechazo.

## R5. Puentes dinámicos con cuota y memoria

**Decision**: Un módulo nuevo, `bridges.py`, aplica tres pasos:
1. **Elegibilidad**, con reglas sobre el plan y la memoria. No hay puente si:
   - `sentiment ∈ {frustrated, angry, distressed}`;
   - `act ∈ {closing, minimal, complaint}`;
   - hubo un rechazo explícito sin señal posterior de interés;
   - hubo un puente en el turno fuera de tema anterior (`bridge_every = 2`).

   En los demás casos el puente es opcional: el plan lo permite y el modelo decide si lo usa.
2. **Candidatos**, buscando en el oro con el retriever híbrido existente. La consulta es el tema del visitante (la
   parte `external` o `social`) ampliado con las palabras de un **mapa de ángulos**. El mapa vive en `prompts/care.md`
   1.1, en la sección nueva `angles.<tema>`; por ejemplo, `clima → agua, cuencas, río Cauca, sostenibilidad`.
3. **Selección**: se descartan las unidades y los ángulos ya ofrecidos en el hilo (`bridges_offered`) y se toma el
   mejor candidato por encima de un puntaje mínimo. Si no hay candidato, se usa una unidad del conjunto curado de
   `care.md` que no se haya ofrecido. Si todas se ofrecieron, no hay puente.

El puente entra al prompt de `converse` como `<puente>` con su etiqueta `[U#]`. La cita se valida como cualquier otra
(`validate_answer`).

**Rationale**:
- Cada visitante recibe una sugerencia relacionada con lo que dijo, y no una de 14 fijas.
- El oro tiene cientos de unidades citables.
- La cuota y la memoria cumplen FR-012 a FR-015 de forma verificable.
- El retriever ya está cargado y la búsqueda local tarda menos de 50 ms.

**Alternatives considered**:
- *Que el modelo elija el puente libremente*: inventaría temas sin cita.
- *Ampliar `care.md` a 50 puentes*: sigue siendo finito y no guarda relación con temas fuera del catálogo.

## R6. Memoria conversacional estructurada

**Decision**: Una clave nueva del estado del hilo, `conversation` (`ConversationMemory`), con:
- `topics`: etiquetas de temas, hasta 20;
- `bridges_offered`: unidad, ángulo y turno;
- `bridge_rejected_at`: turno del último rechazo;
- `interest_after_rejection`;
- `corrections`;
- `register` (`formal` o `informal`);
- `language` (`es`, `en` u `other`);
- `thread_name`: el nombre dado en el hilo, solo en el estado y nunca en `contact` ni en el Store.

El resumen del hilo que ya existe (`compact_history`, `prompts/memory_summary.md`) se mantiene para el contenido. La
memoria estructurada garantiza que lo ofrecido y lo rechazado sobrevivan a la condensación (FR-019).

**Rationale**:
- La memoria estructurada se puede probar y no depende de que el resumen del LLM conserve los detalles.
- El nombre en el hilo ya circula en los mensajes previos que recibe el modelo, así que guardarlo en el estado no
  añade exposición.
- Excluirlo del registro y del Store respeta las specs 018 y 019.

**Alternatives considered**: Confiar solo en el resumen del LLM. No se puede verificar y en demo no existe.

## R7. Parámetros de generación por tipo de turno

**Decision**: Una sección nueva `[conversation]` en `config/agent.toml`:
- `temperature_social = 0.8`: para `converse`;
- `temperature_facts = 0.3`: respuestas con evidencia de Manuelita; hoy es 0.1, y se sube un poco para variar la
  redacción sin tocar los hechos;
- `presence_penalty = 0.3` y `frequency_penalty = 0.3`.

Se aplican con `model.bind(...)` en cada nodo, sin cambiar `config/llm.toml`. Los valores se validan en `[0, 1]`,
como ya hace `llm.py`, aunque la API de DeepSeek acepte hasta 2. El enrutador y el juez siguen en 0.

**Rationale**: La documentación de DeepSeek recomienda temperaturas más altas para conversación general. Un valor de
0.8 da variación sin que el modelo pierda la consigna, y las penalizaciones reducen la repetición de frases. La
verificación de que `deepseek-flash` acepta `presence_penalty` y `frequency_penalty` es una tarea de la
implementación: si no los acepta, se omiten y la antirrepetición queda en R8.

**Verificado (2026-11-20)**: una llamada real a `deepseek-flash` con `model.bind(temperature=0.8,
presence_penalty=0.3, frequency_penalty=0.3, max_tokens=60)` respondió sin error (1.8 s). Aun así, el nodo
`converse` reintenta sin penalizaciones si el proveedor las rechaza en el futuro.

**Alternatives considered**: Subir la temperatura global. Afectaría al enrutador y al juez, que deben ser
deterministas.

## R8. Revisión antes de mostrar (`review.py`)

**Decision**: Una función pura, `review(text, plan, evidence, memory, recent_answers) → ReviewVerdict`, que aplica
estas verificaciones:

| Verificación | Regla |
|--------------|-------|
| `external_fact` | Cifras, porcentajes, fechas, horas, temperaturas o marcadores (`\d`, «grados», «a 2») que no aparecen en la evidencia, en el puente ni en la lista blanca (año de fundación citado). Nombres propios de dos o más palabras con mayúscula fuera de una lista blanca (Manuelita, Valer-IA, Palmira, Cali, Valle del Cauca, Colombia, Fundación Manuelita…) y fuera de la evidencia |
| `contact` | `care.invented_contacts` (spec 019) |
| `promise` | Léxicos `PRICING` y `COMMITMENT` en primera persona afirmativa: «te doy», «te garantizo», «te hago un descuento» |
| `citation` | Las etiquetas `[U#]` deben existir en la evidencia o en el puente (`validate_answer`) |
| `repetition` | Similitud mayor que 0.5 (`difflib.SequenceMatcher` sobre tokens normalizados) con alguna de las 3 últimas respuestas del hilo |
| `opinion` | Léxico de opiniones sobre temas polémicos en primera persona: «yo creo que el gobierno», «mi candidato» |

Si hay un problema, se hace **una** regeneración con una nota breve («evita cifras y nombres que no estén en la
evidencia» o «no repitas la estructura de tu respuesta anterior»). Si persiste, se usa el respaldo (R9). Los avisos
`review_retry` y `review_fallback` quedan en `notices`.

Un juez LLM opcional (`review_llm = false` por defecto) puede añadirse para el nivel `external`. No se activa por
defecto, por la latencia.

**Rationale**:
- Las reglas tienen sesgo conservador: prefieren un falso positivo, que solo cuesta una regeneración, a dejar pasar
  un dato externo.
- Corren en menos de 5 ms y funcionan sin red, así que se pueden probar exhaustivamente.

**Alternatives considered**:
- *Juez LLM siempre*: entre 0.5 y 1 s más por turno, y otra fuente de no determinismo.
- *Lista negra de temas*: no sirve para el texto libre.

## R9. Respaldo

**Decision**: El respaldo se usa cuando la revisión falla dos veces, cuando el LLM lanza un error o cuando vence el
tiempo de espera (`converse_timeout_seconds = 8`). Consiste en la composición de la spec 019
(`care.compose_out_of_scope`, `compose_complaint`, `compose_clarify` o `conduct(...)`) con el puente elegido por R5
en lugar de `bridge.default`. El visitante no ve el error (FR-027).

**Rationale**: Reutiliza código probado. El peor caso equivale a la spec 019, pero sin la repetición del puente por
defecto.

## R10. Streaming

**Decision**: `converse` **no** se transmite token a token: no entra en `STREAMED_NODES`. Sus respuestas son cortas
(`max_tokens = 220`) y se revisan antes de mostrarse. Las respuestas con búsqueda (`answer`, `model`) se siguen
transmitiendo como hoy. `finalize` ya reemplaza el texto en vivo por el definitivo en el evento `done`.

**Rationale**: Transmitir antes de revisar permitiría que el visitante viera por un instante un dato externo. Con
respuestas de 1 a 3 frases, la generación completa tarda alrededor de 1.5 s, dentro de la meta de 3 s (SC-011).

**Alternatives considered**: Transmitir y luego reemplazar. Es visible y confuso para el visitante, y la voz (spec
016) ya habría empezado a leer el texto.

## R11. Mensajes mixtos (Manuelita más charla o datos externos)

**Decision**: Si hay al menos una parte `manuelita`, la ruta sigue siendo de búsqueda (cadena o agente) y el brief
`<atencion>` de la spec 019 se amplía con el plan:
- las partes `social`, que se acompañan en una frase;
- las partes `external`, que se declinan con naturalidad;
- el idioma y el registro.

`prompts/agent.md` 1.6 indica que la respuesta sea una sola pieza fluida. La revisión R8 se aplica también a estas
respuestas, pero solo con las verificaciones `contact`, `promise` y `opinion`, porque la evidencia ya valida las
cifras. Las cifras ajenas a la evidencia se detectan con la misma regla de `external_fact`.

**Rationale**: Una sola respuesta natural, sin ensamblar piezas con declinaciones fijas (`decline.part`).

## R12. Idioma y registro

**Decision**:
- **Idioma**: `care.analyze` detecta el inglés con el léxico `ENGLISH`, que ya existe. Otros idiomas se detectan
  con una heurística simple: proporción de palabras funcionales.
- **Registro**: `informal` si hay marcas como «parce», «jaja», «uy», «qué más» o tuteo con muletillas; si no,
  `formal`.

Ambos se guardan en la memoria y se pasan al plan. `converse` y el agente responden en el idioma del visitante. Las
citas y los nombres de los documentos se mantienen como están. El guion `language.other` de la spec 019 queda solo
como respaldo.

## R13. Modo conmutable y línea base

**Decision**: `[conversation] mode = "guided" | "scripted"`, con `guided` por defecto. En `scripted`, el
comportamiento es exactamente el de la spec 019 (las pruebas de la spec 019 corren en ese modo sin cambios). Si
`[care] enabled = false`, se vuelve a la spec 018, como hasta ahora.

## R14. Modo de demostración

**Decision**: El modelo guionado (`agent/demo.py`) gana una función `demo_converse(plan, memory, seed)`. Compone
respuestas variadas a partir de `care.md` y del plan, con una semilla derivada del hilo y del turno. Así, las pruebas
sin red verifican el flujo completo:
- plan;
- puente con cuota;
- revisión;
- respaldo;
- memoria.

La diversidad real se mide solo en modo real.

## R15. Evaluación de naturalidad (`agent converse`)

**Decision**: Un comando nuevo, `converse_eval.py`, con cuatro bloques:
1. **Repetición entre hilos**: 8 mensajes fuera de tema o sociales, cada uno enviado en 10 hilos nuevos. Mide las
   respuestas distintas por mensaje. Dos respuestas son distintas si su similitud es menor o igual a 0.8 (SC-002).
2. **Conversaciones guionadas**: unas 12 conversaciones de 6 a 10 turnos en
   `tests/fixtures/converse/conversations.jsonl`. Cubren cuota y repetición de puentes, rechazo, visitante molesto,
   corrección, referencia previa, nombre, cierre, mensajes mínimos, inglés, registro informal, broma y datos externos
   camuflados. Las comprobaciones son por turno y de intención, no de texto literal.
3. **Conversaciones simuladas** (solo en modo real): 5 perfiles (curioso, molesto, bromista, estudiante, disperso) ×
   8 turnos, con DeepSeek en el papel de visitante (`prompts/visitor_sim.md`).
4. **Juez de naturalidad** (solo en modo real): `prompts/converse_judge.md` califica de 1 a 5 la naturalidad, la
   empatía y la pertinencia de cada respuesta, a temperatura 0, en JSON.

En todos los bloques se aplica R8 como verificador duro (SC-005). `--baseline` repite todo con `mode = "scripted"`
(SC-007). El informe va a `docs/evaluacion_conversacion.{md,json}`, con una sección de calificación humana sobre una
muestra.

**Rationale**: La batería de la spec 019 mide texto. Esta mide comportamiento, variedad y calidad percibida, que es
lo que se quiere mejorar.

## R16. Ajuste de las baterías existentes (FR-033)

**Decision**:
- `agent conduct` no cambia: sus casos de seguridad conservan el texto exacto, y los de consejo ya piden
  «profesional».
- `agent care` corre en el modo configurado. En el modo `guided`, sus comprobaciones literales de guion pasan a ser de
  intención:
  - `mentions_topic`: se acepta el tema o un sinónimo;
  - `has_alternative`: puente, oferta de ayuda o canal oficial;
  - la emoción reconocida se acepta en las dos primeras frases.

  Los criterios estrictos (SC-005 y SC-007 de la spec 019) se mantienen sin cambios. Se documenta en
  `docs/prompt_log.md`.

## R17. Coste y latencia esperados

| Turno | Llamadas al LLM hoy (spec 019) | Llamadas en el modo `guided` |
|-------|--------------------------------|------------------------------|
| Social o fuera de tema por reglas | 0 | 1 (`converse`), o 2 si se regenera |
| Ambiguo (enrutador LLM) | 1 | 2 |
| Manuelita | 1–5 | Sin cambios |

Con respuestas cortas, DeepSeek tarda entre 1 y 2 s. La meta de SC-011 (menos de 3 s en el 90 % de los turnos) se
mide en la evaluación. El coste extra por turno ronda unos cientos de tokens.
