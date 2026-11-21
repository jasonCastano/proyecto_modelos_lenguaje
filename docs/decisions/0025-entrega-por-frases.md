# ADR 0025 — Entrega de las respuestas por frases revisadas

- **Estado**: aceptada
- **Fecha**: 2026-11-20
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0024 (conversación guiada), ADR 0020 (voz); `specs/021-sentence-streaming/` (spec, plan,
  research R1–R16, contracts, tasks).

## Contexto

La spec 020 hizo que Valer-IA redacte con el modelo lo que no es Manuelita y que revise la respuesta antes de
mostrarla. Para que el visitante nunca viera un dato externo, esas respuestas se mostraban completas al final, y la
primera palabra tardaba entre 5.9 y 6.3 s en el 90 % de los turnos de conversación (meta incumplida SC-011 de la spec
020).

En las respuestas con búsqueda pasaba lo contrario: el texto se transmitía palabra por palabra antes de la revisión
final, así que una frase sin respaldo podía verse y luego desaparecer.

## Decisión

1. **Entrega por frases revisadas** (`agent/sentences.py`). Los nodos que redactan (`converse`, `answer` y `agent`)
   leen el modelo en streaming. Un segmentador con la misma regla de oraciones que la voz arma frases, y cada frase
   pasa la revisión de la spec 020 antes de entregarse como evento SSE `sentence`.
2. **Nunca se retira texto mostrado.** La respuesta final se arma con las mismas frases entregadas, en este orden:
   - `lead`: aviso de datos sensibles y límite por hostilidad, calculados en `route`;
   - `delivered`: las frases del modelo;
   - `tail`: sufijo de mejor interpretación, oferta de recordar, frases exigidas y cierre breve, entregados por
     `finalize`.
3. **Conversación**:
   - si falla la primera frase, se regenera o se usa el respaldo sin haber mostrado nada;
   - si falla una frase posterior, se corta ahí y se cierra con lo aprobado;
   - si el modelo falla a mitad, se conserva lo mostrado y se agrega un cierre breve.
4. **Respuestas con búsqueda**:
   - una frase sin respaldo se descarta y la respuesta sigue;
   - las frases sin cita se retienen hasta que llega una frase citada;
   - si no llega ninguna, el visitante ve el mensaje de evidencia insuficiente, sin texto parcial.
5. **Variante agente**: un callback por cada llamada al modelo. El texto de una llamada que termina pidiendo
   herramientas se descarta, y la primera frase de cada llamada se retiene hasta la segunda o hasta el final.
6. **Voz**: la web entrega cada oración al lector en cuanto llega (`pushSentence`), sin esperar el texto siguiente.
7. **Modo conmutable**: `[conversation] delivery = "complete"` restablece la spec 020. La entrega por frases solo
   aplica en la conversación guiada; con `mode = "scripted"` vale la spec 019.

## Alternativas consideradas

- **Filtro en el servicio sobre los tokens crudos**: no conoce la evidencia del agente ni el plan, y `finalize`
  seguiría armando una respuesta distinta de la mostrada.
- **Transmitir y luego reemplazar**: el visitante vería texto sin revisar y la voz ya lo habría leído.
- **Generar la respuesta final del agente con una llamada aparte**: más predecible, pero cambia la arquitectura de
  la variante agente y añade una llamada por turno.
- **Modelo más rápido o de otro proveedor (por ejemplo Jev de TypeSafe)**: no genera texto, así que no resuelve la
  causa principal; queda como posible verificador semántico en un experimento aparte.

## Consecuencias

- La primera frase llega mientras el modelo sigue escribiendo. El tiempo total no cambia: la revisión por frase
  tarda menos de 5 ms.
- La repetición frente al hilo se revisa sobre la primera frase. Una repetición que solo aparece al final no se
  retira, pero la evaluación la mide.
- El evento `token` solo existe en la entrega completa. Los clientes que ignoren `sentence` siguen recibiendo la
  respuesta en `done`.
- La evaluación `agent converse` mide la primera frase, el tiempo total, el texto retirado y las frases descartadas, y
  los compara con la entrega completa (`--baseline-delivery`).
