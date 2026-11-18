# Contrato: habilidades de atención de Valer-IA (spec 019)

## Prioridad de decisión en el nodo `route`

1. Acción de escritura o pregunta de perfil (sin cambios, spec 014).
2. `care.analyze()` → **crisis** → `out_of_scope` con `scope_reason="crisis"`.
3. Conducta de la spec 018, en este orden: `prompt_extraction`, `third_party`, `harmful`, `abuse`. `abuse` solo
   aplica si `hostile_only`; si el insulto viene con consulta, sigue a los pasos siguientes con `hostile=True`.
4. Pregunta por la naturaleza de la IA, saludo o despedida (sin cambios).
5. Clasificación de las partes (`requests`):
   - todas ajenas, de consejo o no atendibles → `out_of_scope` con `off_topic`, `advice` o `unattainable`; la
     respuesta se compone con R1 y R8;
   - al menos una de Manuelita → enrutador habitual (reglas, luego LLM) con la parte o partes de Manuelita; las demás
     partes se declinan en `finalize`.
6. Ambigüedad: con `clarify_streak >= 1`, se usa la ruta alternativa o `documental` y se marca `best_guess`.

## Composición determinista (`care.compose`)

```text
[opener.<emoción>]? + ack.<tipo>({topic}) + boundary.<tipo> + bridge.<topic_key|default> + close
```

- Cada pieza elige una variante que no sea igual a la última usada en el hilo (`CareState.last_variant`).
- Los `bridge.*` y `channel.*` llevan cita. La respuesta devuelve `citations` con esas unidades, que se validan como
  cualquier cita.
- `advice`: el límite sugiere acudir a un profesional y nunca da el consejo.
- `unattainable`:
  - `pricing` y `commitment`: el límite dice qué no puede ofrecer, luego qué sí puede, y el canal citado o el sitio
    web;
  - `human`: «Soy una asistente virtual…» y el canal citado o el sitio web.
- Con `rejection`, se toma la siguiente alternativa no ofrecida de
  `rejection.rephrase → rejection.related_topics → rejection.official_channel`.
- Con `complaint_streak >= 3`, se usa `complaint.escalation`.

## Antepuesto y sufijo en `finalize`

Orden de los bloques de la respuesta final:

1. aviso de datos sensibles (spec 018), si aplica;
2. límite por hostilidad (`hostility.<nivel>`) si `hostile` y la ruta no fue `abuse`;
3. apertura empática si la emoción es `frustrated`, `angry` o `confused`, o hay `concern` (y no la puso ya la
   composición);
4. respuesta (del modelo o compuesta);
5. una declinación breve por cada parte ajena, en el formato «Sobre {topic}, no tengo información; …»;
6. `best_guess.suffix` si aplica.

Los casos de crisis no reciben los bloques 2, 3, 5 ni 6.

## Respuesta de crisis (`care.md` § crisis)

Contenido mínimo, verificado por prueba:
- reconocimiento empático sin minimizar;
- **Línea 106**: línea nacional de salud mental, gratuita, confidencial y 24 horas;
- **123** en emergencia;
- invitación a hablar con alguien de confianza.

No lleva puente, canal comercial ni pregunta sobre Manuelita.

## Brief de atención para el modelo (rutas con búsqueda)

Se añade al mensaje del usuario en la cadena y al system prompt en el agente. Es breve y no incluye texto del
visitante redactado:

```text
Atención:
- Solicitudes a responder en orden: 1) … 2) …
- Partes ajenas (no las respondas, el sistema las declina): clima
- Estado del visitante: frustrado (el sistema ya abre con una frase empática; no la repitas)
- Retoma en una frase lo que entendiste antes de responder: sí|no
- Es una crítica: responde con equilibrio, solo con lo que documenta la evidencia
```

## Prompts versionados

| Archivo | Versión | Cambio |
|---------|---------|--------|
| `prompts/care.md` | nuevo, 1.0 | guiones de atención (ver data-model) |
| `prompts/agent.md` | 1.4 → 1.5 | reglas de claridad verbal, solicitudes múltiples, críticas, no abrir con empatía, sin tablas |
| `prompts/router.md` | 1.3 → 1.4 | `crisis`, `unattainable` + `kind`, `topic` y `sentiment` opcionales |
| `prompts/conduct.md` | 1.0 → 1.1 | `off_topic`, `advice` y `clarify` pasan a `care.md` y quedan como respaldo; `abuse` sin cambios |

## Batería `agent care`

```bash
uv run python -m proyecto_modelos_lenguaje.agent care --mode demo|real \
    [--variants chain agent] [--cases PATH] [--baseline] [--json-out PATH]
```

- Salida en `docs/evaluacion_atencion.md` y `.json`: verificaciones por caso y por habilidad, SC-001 a SC-007 y
  SC-009, agregados del CRM (FR-024) y latencia frente a la línea base si se pasa `--baseline` (SC-010).
- Termina con código 1 si falla un criterio del 100 % (SC-001 en la parte de hechos externos, SC-004, SC-005, SC-007,
  SC-009).
