# Research: Respuesta progresiva por frases revisadas (spec 021)

Decisiones de diseño para [spec.md](./spec.md). Parten del código en `main` después de la spec 020 (`8f9d0b4`).

## Diagnóstico de partida

| Hoy (spec 020) | Dónde | Efecto |
|----------------|-------|--------|
| `converse` llama al modelo con `invoke` y revisa la respuesta completa | `agent/graph.py::_converse_node` | La primera palabra llega con la respuesta entera: 5.9–6.3 s en el p90 |
| `converse` no está en `STREAMED_NODES` | `agent/service.py` | El cliente solo ve `route` y `done` |
| `answer` (cadena) y `model` (agente) transmiten los tokens crudos del modelo | `service.stream_event` (modo `messages`) | Las respuestas con búsqueda se ven antes de la revisión de `finalize` |
| `finalize` antepone y agrega frases (límite por hostilidad, aviso de datos sensibles, `best_guess`, oferta de recordar) | `_finalize_node` | El texto final no coincide con lo transmitido; el evento `done` lo reemplaza |
| La voz agrupa los tokens en oraciones con su propio segmentador | `web/src/lib/voice.ts::SentenceSegmenter` | La última oración de un fragmento espera a que llegue texto nuevo (por las abreviaturas) |

## R1. Dónde se revisa y se entrega: dentro de los nodos del grafo

**Decision**: Cada nodo que genera texto (`converse`, `answer` y `agent`) consume el modelo en streaming, arma frases
con un **filtro de frases** (`SentenceGate`) y emite cada frase aprobada con el escritor de eventos propios de
LangGraph (`get_stream_writer`, modo `custom`). El nodo guarda en el estado la lista de frases entregadas
(`delivered`), y `finalize` construye la respuesta final a partir de ellas.

**Rationale**: La respuesta final se arma con las mismas frases que vio el visitante, así que el texto final es
igual a lo mostrado (FR-003) por construcción. La revisión tiene a mano el plan, la evidencia y la memoria del turno.

**Alternatives considered**:
- *Filtro en el servicio sobre los tokens crudos*: no conoce la evidencia del agente ni el plan, y `finalize`
  seguiría armando otra respuesta.
- *Filtro en el navegador*: el texto sin revisar ya habría salido del servidor.

## R2. Segmentación en frases

**Decision**: Un segmentador incremental en Python (`agent/sentences.py`) con la regla de `voice/text.py`
(`SENTENCE_END`, abreviaturas y «No. 3»), la misma que usa el navegador. Añade tres reglas:
- un enumerador («1.», «**2)**») al inicio de línea no cierra frase;
- una etiqueta de cita pegada al final («… azúcar [U1].») queda en la frase;
- si el búfer supera `sentence_max_chars` (220) sin cierre, se entrega el fragmento hasta el último espacio
  (FR-006). El primer fragmento usa un límite menor (`first_fragment_chars`, 160), para que llegue antes.

Al terminar el modelo, el resto del búfer es la última frase.

**Rationale**: Una sola regla en el servidor, el navegador y la voz evita que la voz corte distinto de lo que se ve.

## R3. Revisión por frase

**Decision**: Cada frase pasa por `review()` (spec 020) con las verificaciones locales:
- `external_fact`, `contact`, `promise` y `opinion`, contra la evidencia y el puente;
- `citation`: las etiquetas deben existir en la evidencia o el puente.

Las verificaciones globales se aplican así (FR-008):
- **repetición**: se evalúa sobre la primera frase. Si ya es muy parecida a una respuesta reciente (umbral 0.5 sobre
  la frase, o 0.7 si la frase tiene menos de 8 palabras), se regenera antes de mostrar. Al final se registra la
  similitud de la respuesta completa para la evaluación, sin retirar nada;
- **frases exigidas** («Valer-IA Caña», «inteligencia artificial», «profesional», «Manuelita»): si al terminar faltan,
  se agrega una frase de respaldo que las contenga (`care.md`, sección `required.<frase>`).

**Rationale**: Las verificaciones locales ya eran por fragmento (cifras, nombres, contactos). Revisar por frase
cuesta menos de 5 ms y no se nota.

## R4. Falla de la primera frase: regenerar sin mostrar

**Decision**: Mientras no se haya entregado nada, una frase rechazada corta el stream y se regenera con la nota de
corrección (`max_regenerations` = 1). Si vuelve a fallar, o el modelo falla o vence el tiempo antes de la primera
frase, se entrega el respaldo de la spec 019, también por frases.

## R5. Falla de una frase posterior

**Decision**:
- **Conversación** (`converse`): se descarta la frase, se corta el stream y la respuesta termina con las frases ya
  aprobadas. Si la última frase entregada no cierra con un signo de cierre, se agrega una frase breve de cierre
  (`close.short` en `care.md`).
- **Con búsqueda** (`answer` y `agent`): se descarta la frase y se sigue con las siguientes (FR-005), como hacía
  `review_trimmed`, pero sin que el visitante la vea.

En ambos casos el turno registra el número de frases descartadas (`discarded`) y el aviso `sentence_discarded`.

**Rationale**: En la charla, saltar una frase rompe el hilo del texto; en una respuesta con citas, las frases son
afirmaciones independientes.

## R6. Respuestas con búsqueda: frases sin cita retenidas

**Decision**: En `answer` y `agent`, una frase sin etiqueta de cita (por ejemplo «Según los documentos públicos de
Manuelita:») se retiene hasta que llega una frase citada y aprobada; entonces se entregan juntas. Si la respuesta
termina sin ninguna frase citada, no se entrega nada de lo retenido y se emite el mensaje de evidencia insuficiente
(FR-010). El reintento con `STRICT_REMINDER` de la cadena solo ocurre si todavía no se entregó nada.

**Rationale**: Hoy una respuesta sin citas pasa a `FALLBACK_ANSWER`. Si el texto previo se mostrara antes de saberlo,
habría que retirarlo y se rompería FR-003.

## R7. Variante agente: frases por llamada al modelo

**Decision**: El agente (`create_agent`) se invoca con un callback (`on_llm_new_token`) que alimenta un
`SentenceGate` **por cada llamada al modelo**:
- si en la llamada aparece un fragmento de llamada a herramienta, se descarta el búfer de esa llamada (todavía no
  entregado: la primera frase se retiene hasta que la llamada produzca una segunda frase o termine sin herramientas);
- la evidencia para revisar es el texto de las herramientas ejecutadas hasta ese momento (`ToolTrace` más
  `retriever.units_by_id`).

**Rationale**: DeepSeek emite las llamadas a herramientas sin texto previo, así que el caso de texto con
herramientas es raro. La evaluación mide el texto retirado (SC-003) para detectarlo si ocurre.

**Alternatives considered**: Generar la respuesta final con una llamada aparte, fuera del agente. Es más
predecible, pero cambia la arquitectura de la variante agente (spec 014) y añade una llamada por turno.

## R8. Frases antes y después de la respuesta

**Decision**: Las frases que hoy agrega `finalize` se reparten así:
- **antes** (`lead`), calculadas en `route` y entregadas primero por el nodo que genera:
  - el límite por hostilidad;
  - el aviso de datos sensibles;
  - en el modo `scripted`, la apertura empática de la spec 019;
- **después** (`tail`), entregadas por `finalize` con el mismo escritor:
  - el sufijo `best_guess`;
  - el aviso de solicitudes truncadas;
  - la oferta de recordar en el cierre;
  - las frases exigidas que falten (R3).

Las respuestas que no genera el modelo (seguridad, identidad, perfil, acciones) no entregan nada antes:
`finalize` entrega la respuesta completa como frases. El texto final es `lead + delivered + tail`.

## R9. Contrato del flujo de eventos

**Decision**: Un evento nuevo, `sentence`, con `{text, index}`. En la entrega por frases, el servidor no emite
eventos `token`. El evento `done` lleva la respuesta final, igual a la unión de las frases. En la entrega completa
(línea base), todo funciona como en la spec 020.

**Rationale**: La voz recibe oraciones ya cerradas y no tiene que esperar el texto siguiente para decidir si un
punto es una abreviatura. Un cliente viejo que ignore `sentence` sigue viendo la respuesta en `done`.

## R10. Web y voz

**Decision**:
- `ChatView.liveStage`: ante `sentence`, agrega el texto (con un espacio) y muestra la etapa «Escribiendo…».
- `useVoice.pushSentence(text)`: encola la oración directamente, sin pasar por el segmentador.
- La vista técnica muestra en la línea «Actos» las frases descartadas del turno (`✂N`).

## R11. Configuración

**Decision**: En `[conversation]`:
- `delivery = "sentences" | "complete"`, con `sentences` por defecto. `complete` restablece la spec 020 (FR-014);
- `sentence_max_chars = 220` y `first_fragment_chars = 160`;
- `stream_first_timeout_seconds = 8`: tiempo máximo hasta la primera frase antes del respaldo;
- `stream_idle_timeout_seconds = 6`: tiempo máximo sin texto nuevo a mitad de la respuesta.

## R12. Modo demo

**Decision**: `DemoChatModel` ya transmite palabra por palabra en `answer`. `converse` en demo divide el texto de
`demo_converse` en frases con el mismo segmentador y las entrega por el mismo camino (FR-017).

## R13. Evaluación

**Decision**: `agent converse` y `agent care` miden, por turno:
- tiempo hasta el primer `sentence` (o el primer `token` en `complete`);
- tiempo hasta `done`;
- texto mostrado comparado con la respuesta final (`retracted` si no coincide, sin contar espacios);
- frases descartadas.

Las métricas se separan por clase de turno: conversación (rutas `direct`, `out_of_scope` y `clarify`) y búsqueda. La
opción `--baseline-delivery` repite la evaluación en `complete`, para comparar SC-001, SC-002 y SC-006.

## R14. Voz: medición de SC-007

**Decision**: Se mide en dos partes:
- en el navegador (Vitest): `pushSentence` encola la primera oración en el mismo ciclo y pide el audio de inmediato;
- en el servidor (prueba con red, `voice`): el tiempo de síntesis de la primera oración de Phonon, que ya mide la
  spec 016.

SC-007 se reporta como la suma de los dos.

## R15. Constitución y ADR

**Decision**: CONSTITUTION v1.13.0, §3.7: la conversación guiada se entrega por frases revisadas y nunca se retira
texto mostrado. ADR 0025 con las decisiones R1, R5, R6 y R7.

## R16. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Texto retirado en el agente si una llamada mezcla texto y herramientas | Retención de la primera frase de cada llamada (R7) y métrica `retracted` (SC-003) |
| Frases cortas que rompen la coherencia al descartar una del medio (conversación) | En la conversación se corta el stream en la primera frase rechazada (R5) |
| Más eventos por turno en el SSE | Unos 2 a 8 eventos `sentence` por turno, frente a cientos de `token` hoy |
| La repetición se detecta tarde | Revisión de la primera frase (R3) y métrica de similitud final en la evaluación |

## R17. Hallazgo de la implementación: el tiempo no estaba en generar

**Medición** (2026-11-20, DeepSeek con `deepseek-flash`):
- DeepSeek tarda entre 1.1 y 1.7 s en entregar el primer fragmento y genera una respuesta corta de 2 a 3 frases
  en unos 0.3 s más. Para la charla, entregar por frases ahorra poco: la primera frase llega casi con la última.
- En los turnos con posible puente, `route` tardaba unos 1.66 s buscando el puente en el oro con el buscador
  híbrido (embeddings de la consulta).

**Decision**: La búsqueda del puente usa solo las palabras del ángulo (`angles.<tema>`) y queda en caché por buscador
y tema (`bridges._retrieved`). Al crear las dependencias del modo real, un hilo en segundo plano precalienta los 17
temas (`bridges.warm_up`, unos 26 s una sola vez por buscador). Con la caché caliente, `route` tarda menos de 0.1 s
y el turno de charla completo, entre 1.2 y 2.8 s.

**Rationale**: El texto del visitante solo servía para adivinar el tema. La relación del puente con lo que dijo la
definen las palabras del ángulo, que ya se exigían en el candidato (`_mentions_angle`).

**Alternatives considered**:
- *Lanzar la búsqueda en paralelo con el modelo*: el puente debe entrar en el prompt antes de generar.
- *Solo búsqueda léxica*: menos relevante y obligaba a separar el buscador híbrido.
