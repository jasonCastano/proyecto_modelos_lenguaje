# Research: Valer-IA con acento y expresiones caleñas (spec 036)

## R1. ¿Dónde se escribe cada respuesta y dónde entra el estilo?

**Hallazgo**: cuatro fuentes de texto llegan al visitante.

| Fuente | Prompt o texto | ¿Lleva estilo? |
|---|---|---|
| Conversación guiada (saludo, cortesía, temas ajenos, mínimos, despedida) | `prompts/converse.md` | Sí, con el bloque `<estilo>`. |
| Respuestas con búsqueda (ambas variantes, `chain` y `agent`) | `prompts/agent.md` (nodo de respuesta) | Sí, como máximo una expresión al inicio o al cierre. |
| Guion de las notas de voz | `prompts/voice_script.md` | Sí, hasta dos expresiones habladas. |
| Textos fijos (crisis, terceros, extracción, daño, abuso) y respaldos de `care.md` | `conduct.md`, `care.md` | No (FR-007). Los respaldos conservan su texto. |

`prompts/qa.md` lo usan las tareas de la Fase 1 (`/api/ask`) y la evaluación del Módulo 1. No es la voz de
Valer-IA y no cambia, para no mover métricas publicadas.

**Decisión**: un solo bloque `<estilo>`, calculado por `agent/style.py`, se inyecta en los tres prompts.

**Alternativas**: reescribir los textos de `care.md` en caleño. Se descartó porque los respaldos y los textos
fijos deben ser estables y sobrios.

## R2. Léxico caleño aprobado y vetado

**Decisión**: `config/caleno.toml`, versionado y revisable por el equipo. Lista inicial:

| Expresión | Significado | Niveles | Hablada | Ejemplo profesional |
|---|---|---|---|---|
| «ve» (interjección) | llamado de atención afectuoso | informal, neutral | sí | «¡Ve, qué buena pregunta!» |
| «qué bueno, ve» | alegría | informal, neutral | sí | «Qué bueno, ve, te cuento…» |
| «listo pues» | acuerdo, cierre | informal, neutral | sí | «Listo pues, aquí te dejo el dato.» |
| «a la orden» | disposición a servir | todos | sí | «A la orden para lo que necesites.» |
| «con mucho gusto» | cortesía | todos | sí | «Con mucho gusto te cuento.» |
| «¡uy, qué nota!» | entusiasmo | informal | sí | «¡Uy, qué nota que preguntes por eso!» |
| «bien pueda» | invitación cortés | informal, neutral, formal | sí | «Bien pueda, pregúntame lo que quieras de Manuelita.» |
| «de una» | aceptación inmediata | informal | sí | «De una, te cuento.» |
| «chévere» | agrado | informal, neutral | sí | «Qué chévere que te interese.» |
| «la ñapa» | un extra | informal, neutral | no (riesgo de pronunciación) | «Y de ñapa, te cuento que…» |
| «pues» (cierre) | énfasis amable | informal, neutral | sí | «Ahí te cuento, pues.» |
| «sucursal del cielo» | apodo de Cali | informal, neutral | sí | uso raro, solo si el visitante habla de Cali |

Vetadas, con su motivo:

- **groserías y vulgarismos** («gonorrea», «marica», «hijueputa», «chimba», «verraco» como insulto);
- **otras regiones** («parce», «parcero», «quiubo», «qué hubo», «chévere parce», «ome», «nojoda»);
- **voseo** («vos», «mirá», «sabés», «tenés», «oís»), por la decisión P2;
- **doble sentido o estereotipos** (comentarios sobre «las caleñas», la salsa usada como burla).

**Racional**: son expresiones caleñas reconocidas y aptas para la atención al cliente. Las de doble filo quedan
fuera. «Chévere» es colombiano general, pero muy usado en Cali y seguro.

**Alternativas**: dejar que el modelo improvise el caleño. Se descartó porque DeepSeek tiende a mezclar paisa,
bogotano o caricatura; con la lista, el verificador puede medir.

## R3. Nivel de estilo por turno

**Decisión**: `style.level_for(plan, memory, message)` → `off | formal | neutral | informal`.

1. **`off`** si se cumple alguna de estas condiciones:
   - idioma distinto de `es`;
   - sentimiento `frustrated`, `angry` o `distressed`;
   - acto `complaint`;
   - razón `crisis`;
   - turno con texto fijo;
   - `memory.style_opt_out`;
   - léxico deshabilitado.
2. **`formal`** si el registro es formal y el mensaje trae marcas formales («buenos días», «usted», «quisiera»,
   «cordial», «solicito», «estimado»).
3. **`informal`** si el registro es `informal` (marcas coloquiales existentes más «ve», «pues sí», «oís»).
4. **`neutral`** en los demás casos.

**Racional**: hoy el plan solo distingue `formal` e `informal`, y `formal` es el valor por defecto, que en la
práctica es neutro. Se separa lo neutro de lo formal explícito para no volver acartonado el caso común.

## R4. Sugerencias, límite y variedad

**Decisión**:

- `style.suggest(level, last_expressions, seed, k=3)` elige 3 expresiones permitidas en el nivel que no estén en
  `last_expressions`. Para la voz filtra `spoken = true`.
- El bloque `<estilo>` dice:
  - el nivel;
  - las sugeridas;
  - «como máximo una»;
  - «al inicio o al cierre, nunca dentro de una cifra o una cita»;
  - «tuteo, sin voseo»;
  - y «no la uses si no encaja» (no es obligatorio usarla).
- Tras el turno, `care.update_conversation` guarda las expresiones encontradas en la respuesta
  (`last_expressions`, máximo 3).

**Racional**: obligar a usar una en cada turno vuelve la expresión muletilla. SC-001 pide el 60 %, no el 100 %.

## R5. Verificador

**Decisión**: en `agent/review.py` se agregan cuatro checks:

| Check | Regla | Dónde |
|---|---|---|
| `style_banned` | expresión vetada o voseo | conversación (reintento) y búsqueda (`RETRIEVAL_CHECKS`: se quita la frase) |
| `style_excess` | más de una expresión aprobada en texto escrito | conversación |
| `style_repeat` | una expresión también presente en la respuesta anterior del hilo | conversación |
| `style_off` | alguna expresión con nivel `off` | conversación y búsqueda (se quita la expresión o la frase) |

Cada check lleva su nota en `NOTES`. Por frase (streaming) se aplican `style_banned` y `style_off`. La coincidencia
es por palabra completa y sin tildes. «Ve» solo cuenta como interjección: al inicio de la frase seguido de coma o
signo, o tras una coma al final de la frase («qué bueno, ve»), para no confundirla con «ve a la página».

**Alternativas**: un clasificador LLM del estilo. Se descartó por costo y latencia; queda solo para el juez de la
evaluación.

## R6. Voz: la más cercana del catálogo

**Hallazgo**: el catálogo de Phonon en español tiene voces castellanas (Noa, Lucía-Sol, Candela, Alba, Marcos,
Iker…), mexicanas (Regina, Ximena; Rebeca es la actual) y voces sin acento declarado (Celia, Alicia, Danae,
Azucena, Jimena, Yael…). No hay colombianas.

**Decisión**:

- `uv run python -m proyecto_modelos_lenguaje.voice --audition` sintetiza la misma frase caleña con las voces
  femeninas de español no castellanas: Rebeca, Regina, Ximena, Celia, Alicia, Danae, Azucena, Jimena y Yael (la
  que el catálogo no declare como femenina se descarta al escuchar);
- además sintetiza cada expresión con `spoken = true`;
- los WAV quedan en `MANUELITA_STATE_DIR/voice_audition/`, fuera del repositorio, con un índice en texto;
- el usuario escucha, elige la voz y marca las expresiones mal pronunciadas;
- se actualizan `config/voice.toml` (`voice`) y `config/caleno.toml` (`spoken = false`), y se registra en
  `docs/prompt_log.md`.

**Racional**: es la decisión P1 (sin motor nuevo). El oído del equipo es el criterio; una persona de Cali valida en
SC-007.

## R7. «Habla normal» y pregunta por una expresión

**Decisión**:

- `style.opt_out(message)` detecta frases como «habla normal», «sin acento», «sin modismos», «no hables así»,
  «speak normally». Marca `style_opt_out = true` en la memoria y el resto del hilo queda en `off`. El turno responde
  con una confirmación breve guiada por el plan («Listo, te hablo sin modismos»), sin expresiones.
- La pregunta por una expresión («¿qué significa "ve"?») va por la conversación guiada como `about_assistant` o
  `smalltalk`. El bloque `<estilo>` trae el glosario de las expresiones usadas en el hilo (significado de
  `caleno.toml`), y la respuesta explica en una frase y vuelve a Manuelita (spec 035).

## R8. Evaluación

**Decisión**: el conjunto `tests/fixtures/converse/caleno.jsonl` tiene 14 conversaciones:

- informal, neutro y formal;
- queja, angustia y crisis;
- inglés;
- «¿qué significa "ve"?»;
- «habla normal»;
- respuesta con búsqueda y cita;
- conversación larga (8 turnos);
- jerga y groserías del visitante;
- nota de voz (guion);
- despedida.

`check_turn` agrega estas claves:

| Clave | Qué verifica | Criterio |
|---|---|---|
| `style_used` | presencia | SC-001 |
| `no_banned` | sin expresiones vetadas | SC-002 |
| `max_expressions` | límite por respuesta | SC-003 |
| `style_off` | sin estilo donde no toca | SC-004 |
| `no_style_repeat` | variedad | SC-005 |
| `citations_kept` | citas conservadas | SC-008 |

`agent converse --style` escribe `docs/evaluacion_caleno.{md,json}`. En el modo real, `prompts/style_judge.md`
califica la claridad y el profesionalismo de 1 a 5 (SC-006). La prueba humana (SC-007) se registra a mano en el
mismo informe.
