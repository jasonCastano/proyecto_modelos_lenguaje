# ADR 0026 — Gatekeeper System One (Jev) en el enrutador

- **Estado**: aceptada (gatekeeper desactivado por defecto)
- **Fecha**: 2026-11-21
- **Autor**: Roberto José Guerrero
- **Relacionadas**: ADR 0016 (agente LangGraph y enrutador), ADR 0015 (alcance del Módulo 2, Jev opcional);
  `specs/022-jev-router-gate/` (spec, plan, research R1–R14, contrato, tasks).

## Contexto

La rúbrica de sustentación del Módulo 2 pide en el ítem 2.3 (Router Agent, 10 %) decidir la ruta «por reglas, LLM o
gatekeeper System One (Jev: Choice, Noul, Score, Box) si está disponible». La evaluación docente lo marcaba como no
implementado. Además:

- El enrutador hacía una llamada completa a DeepSeek por cada mensaje que las reglas no resolvían, y el tiempo de
  respuesta del Módulo 2 incumplía por poco SC-007 (95 % y 91 % de respuestas en menos de 10 s el 2026-11-14).
- Las señales de atención de las specs 019 y 020 (crisis, enojo, motivo) dependen solo de listas de palabras.

Jev (TypeSafe) no redacta texto: responde preguntas tipadas con probabilidades en fracciones de segundo.

## Decisión

1. **Etapa intermedia del enrutador**: reglas → **Jev** → clasificador LLM. Las reglas siempre ganan. Jev decide si la
   probabilidad de la ruta elegida alcanza `route_threshold` (0,75, inclusivo); si no, decide el LLM como antes.
2. **Una sola solicitud por turno** (`POST https://api.typesafe.ai/v1/systemone`) con cuatro preguntas de
   `prompts/jev.md`: `route` (Choice), `scope` (Choice), `annoyance` (Score de 4 niveles) y `crisis` (Noul). No se
   consulta en saludos ni en acciones de escritura o preguntas de perfil.
3. **TypeSafe directo con cliente propio** (`httpx`, `agent/jev.py`), versión **fija** `jev-1.14.0`, timeout de 2 s y
   sin reintentos. Todo fallo (red, timeout, 4xx/5xx, respuesta inválida, rechazo) se convierte en
   `GateOutcome(status="failed")` y el turno sigue con el LLM: Jev nunca tumba una respuesta.
4. **Crisis como unión**: es crisis si el léxico **o** Jev (`P ≥ 0,5`) lo indican; Jev nunca anula una crisis. La
   molestia solo intensifica la emoción detectada.
5. **Privacidad**: al servicio solo llegan el mensaje y hasta tres preguntas previas, con correos, teléfonos y
   documentos enmascarados (`privacy.redact_pii`). La clave `TYPESAFE_API_KEY` vive solo en `.env`.
6. **Desactivado por defecto** (`[jev].enabled = false`; `MANUELITA_JEV_ENABLED=1` lo activa). Sin clave, todo
   funciona como antes; las pruebas usan un gatekeeper simulado sin red.

## Alternativas

| Alternativa | Motivo para descartarla |
|---|---|
| SDK `typesafe-sdk` | Dependencia nueva en etapa temprana y forma de llamada no verificada; el contrato HTTP es de tres campos. |
| OpenRouter (`/api/alpha/decisions`) | Endpoint *alpha*; el registro fue bloqueado por la verificación antibots. |
| Vercel AI Gateway / Cloudflare Workers AI | Pensados para JavaScript y Workers; ruta desde Python no documentada. |
| Reemplazar el clasificador LLM por Jev | Sin respaldo ante fallos o baja confianza; peor en las preguntas ambiguas. |
| Box (recuadros sobre imágenes) | El corpus no tiene imágenes y el proveedor lo marca como experimental. |

## Resultados (`docs/evaluacion_jev.md`)

- **Validación en español** (24 consultas nuevas, distintas de las de evaluación): 24/24 rutas correctas, ~215 ms
  por consulta. Fijó el umbral; no se ajustó nada con las 44 consultas de evaluación (principio II).
- **Enrutador, 44 consultas del Módulo 2, dos ejecuciones**: exactitud 97,7 % sin Jev y **93,2 % con Jev** (los
  mismos tres errores en ambas: preguntas `documental` de «¿dónde?», «¿desde cuándo?» y «¿cuánto … al año?» que Jev
  envía a `structured`; la última también la falla el LLM). Jev decide el 57–59 % de las consultas y evita el
  73–77 % de las llamadas al LLM del enrutador; la latencia media de enrutamiento baja de ~1,3 s a ~0,5 s.
- **Atención** (36 casos): 100 % de las crisis y del límite cordial con y sin Jev; los casos que cumplen varían ±3
  entre ejecuciones aun sin Jev (la conversación guiada redacta con el LLM).
- **Costo**: ~0,005 USD por comparación completa.

## Consecuencias

- El ítem 2.3 queda cubierto con el gatekeeper System One y con evidencia comparativa.
- **SC-001 de la spec no se cumple** (−4,5 puntos frente a una tolerancia de −2): por eso Jev queda desactivado por
  defecto. Mejorarlo exige un conjunto de validación más difícil (preguntas de «¿dónde?»/«¿cuándo?» narrativas) y
  ajustar `prompts/jev.md` con él, nunca con las 44 consultas de evaluación.
- Se añade un segundo proveedor externo en EE. UU. cuando se activa; queda en la data card (limitación 13).
- `turns.jsonl` registra el bloque `jev` (estado, ruta, confianza, latencia, costo) y `TurnMetrics.gate_calls`.
