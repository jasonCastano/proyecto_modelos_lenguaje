# Contrato: conversación guiada (spec 020)

Contrato de comportamiento del nodo `converse`, del plan del turno, de los puentes y de la revisión. Es la referencia
de las pruebas sin red, las de `tests/integration/agent/test_converse_flow.py`.

## 1. Orden de decisión en `route`

1. Identidad, recordar y acciones con aprobación (specs 018 y 014): sin cambios.
2. `care.analyze`: señales, partes, `tier` por parte y `act`.
3. Crisis → `reply` fijo (spec 019).
4. `third_party`, `prompt_extraction`, `harmful` y `abuse` solo hostil → `reply` fijo (specs 018 y 019).
5. Pregunta de perfil → `reply` (spec 014).
6. Hay alguna parte `manuelita` → ruta de búsqueda (`retrieve`/`answer` o `agent`), con el brief ampliado (§5).
7. Cualquier otro caso → `converse` si `[conversation] mode = "guided"`; si no, `reply` (spec 019).

En el modo `scripted`, los pasos 6 y 7 funcionan exactamente como en la spec 019.

## 2. Plan del turno

`plan.build_plan` es determinista: para las mismas señales, decisión y memoria, devuelve el mismo plan.

| Situación | `act` | `strategy` | `bridge_allowed` | `length` |
|-----------|-------|------------|------------------|----------|
| «hola, buen día» | `greeting` | `accompany` | no | short |
| «¡qué calor hace hoy!» | `smalltalk` | `accompany` | sí, si se cumple la cuota | short/medium |
| «¿cómo estará el clima mañana?» | `off_topic` | `decline` (+`accompany`) | sí, si se cumple la cuota | medium |
| «esta página no sirve» | `complaint` | `empathize`, `limit` | no | medium |
| «no, me refería a la energía» | `correction` | `answer` | no | según la evidencia |
| «jaja» / «ok» / «👍» | `minimal` | `accompany` | no | short |
| «¿eres humana?» | `about_assistant` | `answer` | no | short |
| «listo, gracias, eso era todo» | `closing` | `farewell` | no | medium |
| «gracias» (sin cierre) | `thanks` | `accompany` | no | short |
| «hazme un descuento» | `off_topic` (`unattainable`) | `limit`, `decline` | no; se ofrece el canal oficial | medium |

## 3. Prompt de `converse` (`prompts/converse.md` v1.0)

Las secciones son `system`, `style` y `examples`, que se parsean como los demás prompts. Contenido normativo:

- **Identidad**: Valer-IA Caña, asistente de IA del sitio sobre Manuelita. No es un canal oficial (spec 018).
- **Tres niveles**:
  - lo social se acompaña, sin cifras, fechas, nombres ni resultados;
  - lo externo se declina con palabras propias, sin inventar;
  - Manuelita solo se trata con evidencia. En `converse` no hay evidencia, salvo el `<puente>`.
- **Estilo**:
  - variar aperturas y estructura, sin fórmulas fijas;
  - longitud según `length`;
  - idioma y registro del plan;
  - una pregunta de vuelta solo si ayuda;
  - no repetir lo que el visitante ya rechazó;
  - sin opiniones sobre temas polémicos.
- **Puente**: si llega `<puente>`, puede mencionarlo en una frase con su `[U#]`, o no usarlo si no encaja. Nunca
  menciona otro tema de Manuelita sin cita.
- **Memoria**: recibe `<memoria>` con los temas tratados, lo ofrecido y el nombre en el hilo. Puede retomar lo
  anterior.
- **Ejemplos**: 8 a 10 pares de estilo derivados de `care.md`, marcados como «estilo, no copiar».

Entrada del modelo:
- sistema, más `<plan>`, `<memoria>` y `<puente>` opcional;
- los últimos `keep_last_messages` turnos;
- el mensaje actual.

Salida: texto plano.

## 4. Revisión y respaldo

```text
texto = modelo(prompt)                      # temperature_social, penalizaciones
veredicto = review(texto, plan, evidencia, memoria, últimas_respuestas)
si no ok y regeneraciones < max_regenerations:
    texto = modelo(prompt + nota_de_corrección(veredicto.issues)); notices += review_retry
    veredicto = review(...)
si no ok o error o timeout:
    texto = respaldo_spec019(plan, puente_elegido); notices += review_fallback
```

Garantías:
- **Nada sin revisar**: ninguna respuesta de `converse` llega al visitante sin pasar por `review` o sin ser respaldo.
- **El respaldo pasa la revisión**: sus textos se verifican en las pruebas.
- **Sin streaming**: `converse` no transmite tokens (R10).

## 5. Brief de las respuestas con búsqueda

`care_brief` (spec 019) añade, cuando corresponde:
- `Social: acompaña en una frase «…tema…»`;
- `Externo: declina con naturalidad «…tema…»`;
- `Idioma: en`;
- `Registro: informal`;
- `Sentimiento: frustrated → abre reconociéndolo`.

`prompts/agent.md` 1.6 pide una sola respuesta fluida. Las declinaciones fijas `decline.part` y la apertura
determinista de `finalize` solo se usan en el modo `scripted`. En el modo `guided` las redacta el modelo.

## 6. `finalize` en el modo `guided`

- **Se mantiene**:
  - el aviso de datos sensibles (spec 018);
  - el reemplazo de contactos inventados;
  - `hostility.N` como antepuesto cuando hay insulto con pregunta;
  - el sufijo `best_guess`.
- **Se omite**: la apertura empática determinista (`empathy_opener`), porque ya la redacta el modelo.
- **Se añade**:
  - la oferta de recordar de la spec 018, una vez por visita y solo a visitantes anónimos, en los turnos
    `closing`;
  - la actualización de `ConversationMemory`;
  - `ContactRecord.turns`.

## 7. Batería `agent converse`

```text
uv run python -m proyecto_modelos_lenguaje.agent converse \
    --mode demo|real --variants chain agent [--baseline] [--simulate] [--repeats 10] [--json-out PATH]
```

| Métrica | Fuente | Meta |
|---------|--------|------|
| `within_thread_max_similarity` | guionadas y simuladas | ≤ 0.5 en el 100 % de los pares (SC-001) |
| `cross_thread_distinct` | bloque de repetición | ≥ 8/10 por mensaje (SC-002) |
| `bridge_repeats` | guionadas y simuladas | 0 (SC-003) |
| `bridge_rate_offtopic` | guionadas y simuladas | ≤ 0.5 (SC-003) |
| `bridges_when_blocked` | guionadas | 0 (SC-004) |
| `hard.external_facts`, `contacts`, `promises` | todas, con `review` como verificador | 0 (SC-005) |
| `crisis`, `conduct` | `agent care` y `agent conduct` | 100 %, 24/24 (SC-006) |
| `judge.*` | simuladas y guionadas | ≥ 4 y mayor que la línea base (SC-007) |
| `social_accompanied` | casos `smalltalk` | ≥ 90 % (SC-008) |
| `minimal_short` | casos `minimal` | ≥ 90 % con 2 frases o menos (SC-009) |
| `corrections_no_clarify`, `refers_back` | guionadas | 100 % y ≥ 80 % (SC-010) |
| `first_word_ms.p90` | todas | < 3000 (SC-011) |
| `fallback_on_error` | prueba con el modelo caído | 100 % (SC-012) |

El comando sale con código 1 si falla alguna meta dura (SC-001 a SC-006 y SC-012). Las metas de calidad (SC-007 a
SC-011) se informan y se registran en `docs/prompt_log.md`.
