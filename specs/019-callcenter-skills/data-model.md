# Data Model: habilidades de atención de Valer-IA (spec 019)

Todas las entidades son del dominio del agente. Ninguna guarda texto libre del visitante ni datos personales.

## CareSignals (análisis del mensaje, efímero por turno)

Lo produce `care.analyze(message, care_state)` en el nodo `route`, antes de decidir la ruta.

| Campo | Tipo | Regla |
|-------|------|-------|
| `sentiment` | `Sentiment` | `neutral \| satisfied \| confused \| frustrated \| angry \| distressed` |
| `hostile` | bool | contiene insultos del léxico `abuse` |
| `hostile_only` | bool | al quitar los insultos no queda una consulta → motivo `abuse` determinista |
| `rejection` | bool | «eso no me sirve», «no me ayudaste», «no entiendes» |
| `sarcasm` | bool | ironía detectada; fuerza `frustrated` |
| `concern` | bool | crítica a la empresa (contaminación, daño, explotación…) |
| `crisis` | bool | angustia grave o autolesión; tiene prioridad sobre todo |
| `requests` | list[`RequestPart`] | de 1 a `max_requests` (5); `truncated` si había más |

`RequestPart`: `index` (int), `text` (str, **solo en memoria del turno**, nunca persistido), `kind`
(`manuelita | off_topic | advice | unattainable`), `topic_key` (clave del catálogo o `None`), `unattainable_kind`
(`pricing | commitment | human | None`).

## RouteDecision (cambios)

Campos nuevos, opcionales y validados:

| Campo | Tipo | Regla |
|-------|------|-------|
| `scope_reason` | `ScopeReason` | se añaden `crisis` y `unattainable` |
| `topic` | str \| None | saneado: `[a-záéíóúñ ]`, como máximo 4 palabras y 40 caracteres; solo con `off_topic` |
| `sentiment` | `Sentiment` \| None | lo propone el LLM; solo se usa si las reglas dieron `neutral` |
| `kind` | `pricing \| commitment \| human` \| None | solo con `unattainable` |

## CareState (`ChatState["care"]`, persistido por hilo en el checkpointer)

| Campo | Tipo | Uso |
|-------|------|-----|
| `used` | dict[str, int] | veces que se usó cada clave de guion, para rotar variantes |
| `last_variant` | dict[str, int] | última variante por clave; no se repite de forma consecutiva |
| `complaint_streak` | int | quejas o rechazos seguidos; se reinicia con un turno satisfecho o resuelto |
| `clarify_streak` | int | aclaraciones seguidas; con 1 o más, la siguiente ambigüedad usa la mejor interpretación |
| `hostile_turns` | int | turnos hostiles del hilo; determina el nivel 1, 2 o 3 o más |
| `alternatives_offered` | list[str] | alternativas ya ofrecidas (`rephrase`, `related_topics`, `official_channel`) |

## ContactRecord (`ChatState["contact"]`, persistido por hilo; el "CRM")

| Campo | Tipo | Regla |
|-------|------|-------|
| `version` | `"1.0"` | |
| `opened_at` / `updated_at` | datetime ISO | |
| `turns` | int | turnos atendidos |
| `requests` | list[`ContactRequest`] | una por cada `RequestPart` atendida |
| `sentiments` | list[`Sentiment`] | una por turno, en orden; muestra la evolución |
| `motive` | list[str] | etiquetas de tema únicas, en orden de aparición (máximo 5) |
| `resolved` | bool | true si todas las solicitudes del último turno quedaron `resolved`, `out_of_scope` o `referred` |
| `hostile_turns` | int | copia de `CareState.hostile_turns` |
| `crisis` | bool | hubo al menos un turno de crisis |

`ContactRequest`: `turn` (int), `category`
(`manuelita | off_topic | advice | complaint | unattainable | crisis | conduct | other`), `topic` (etiqueta
controlada: `topic_id` del oro, clave del catálogo u `otro`), `status`
(`resolved | out_of_scope | not_attainable | needs_clarification | referred | no_evidence`).

**Reglas de estado de una solicitud**:

| Situación | `status` |
|-----------|----------|
| Respuesta con citas válidas | `resolved` |
| Ruta documental o estructurada sin evidencia (`fallback`) | `no_evidence` |
| Tema ajeno o consejo profesional | `out_of_scope` |
| Pedido no atendible con canal oficial citado | `referred` |
| Pedido no atendible sin canal | `not_attainable` |
| Ruta `clarify` | `needs_clarification` |
| Crisis | `referred` (líneas de ayuda) |
| Conducta de la spec 018 (terceros, extracción, daño, abuso) | `out_of_scope` con categoría `conduct` |

**Invariantes**:
- El registro no contiene `user_id`, huella, nombre, correo ni texto del visitante. Una prueba lo verifica con todos
  los casos de la batería (SC-009).
- Un hilo nuevo, por ejemplo tras «empecemos de nuevo», empieza con un registro vacío (FR-025).

## Playbook (`prompts/care.md`, versionado)

Secciones, cada una con una lista de 2 a 4 variantes (`- …`). Los placeholders permitidos son `{topic}`, `{bridge}`,
`{channel}` y `{options}`.

| Sección | Contenido |
|---------|-----------|
| `opener.frustrated`, `opener.angry`, `opener.confused`, `opener.concern` | frases de apertura empática |
| `ack.off_topic`, `ack.advice` | reconocimiento del tema, con `{topic}` |
| `boundary.off_topic`, `boundary.advice`, `boundary.pricing`, `boundary.commitment`, `boundary.human` | límite cordial |
| `bridge.<topic_key>` | puente a Manuelita, con línea de cita `unit \| url \| title` |
| `bridge.default` | puente general (historia, negocios, sostenibilidad) |
| `channel.website`, `channel.ethics_line`, `channel.data_protection` | canales oficiales con cita |
| `close` | pregunta de cierre |
| `hostility.1`, `hostility.2`, `hostility.3` | límite según el nivel |
| `rejection.rephrase`, `rejection.related_topics`, `rejection.official_channel` | alternativas de resiliencia |
| `complaint.escalation` | tercera queja: reconoce lo pendiente y ofrece canal |
| `clarify.intro`, `clarify.options.<topic_key>`, `clarify.options.default` | aclaración con opciones |
| `best_guess.suffix` | «Si te referías a otra cosa, dime y lo ajusto.» |
| `crisis` | respuesta de apoyo con la Línea 106 y el 123 (sin puente) |
| `satisfied` | cierre cálido breve |
| `language.other` | aviso cortés de que responde en español |

## Topic catalog (`care.TOPICS`, código)

`TopicSpec`: `key`, `label` (la que se dice al visitante, por ejemplo «el clima»), `pattern` (regex normalizada),
`bridge` (clave `bridge.*`) y `kind` (`off_topic` o `advice`).

Claves iniciales: `clima`, `deportes`, `politica`, `finanzas_externas`, `programacion`, `cocina`, `tareas`,
`entretenimiento`, `viajes`, `tecnologia`, `otras_empresas`, `salud` (`advice`), `legal` (`advice`) e `inversion`
(`advice`).

## CareCase (`tests/fixtures/care/care_cases.jsonl`)

`id`, `skill` (`off_topic | empathy | hostility | crisis | clarify | multitask | assertiveness | criticism |
resilience | satisfied`), `turns` (list[str]) y `expect`:
- `scope_reason?`, `category?`, `sentiment?`;
- `mentions[]`, `forbidden[]`;
- `opener: bool`, `crisis_lines: bool`, `no_echo[]`;
- `parts: int?`, `no_invented_contacts: bool`.

## Transiciones

```text
mensaje → analyze() ─ crisis ───────────────→ reply(crisis) ─────────────────────────┐
                    ├ hostile_only ────────→ reply(abuse nivel n) ───────────────────┤
                    ├ conducta 018 ────────→ reply(conduct.md) ──────────────────────┤
                    ├ todo ajeno/no atend. → reply(compuesto R1/R8) ─────────────────┤
                    └ Manuelita (+ partes) → retrieve/agent ─→ answer ───────────────┤
                                                                                     ▼
                finalize: apertura (emoción/hostil) + respuesta + declinaciones de partes ajenas
                          + sufijo de mejor interpretación → actualiza CareState y ContactRecord
```
