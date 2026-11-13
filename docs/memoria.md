# Memoria del asistente conversacional

**Autor**: Roberto José Guerrero · **Spec**: `specs/014-rag-agent-memory-router` (US1, US4, US5) · **Fecha**:
2026-11-11

Este documento declara qué recuerda el asistente, dónde lo guarda, cuánto tiempo y cómo se borra (FR-009).

## 1. Qué se persiste

| Memoria | Contenido | Alcance | Archivo |
|---------|-----------|---------|---------|
| **Hilo** (memoria corta) | Turnos visibles (pregunta, ruta, fragmentos, respuesta, citas, métricas), resumen del historial y registro de decisiones humanas (`actions[]`) | Un `thread_id` | `checkpoints.sqlite3` |
| **Preferencias** (memoria larga) | Solo preferencias declaradas de una lista cerrada: `response_format` (formato de respuesta), `topics_of_interest` (temas de interés) y `language` (idioma), cada una con un valor de hasta 200 caracteres | Un `user_id` anónimo, entre hilos | `memory.sqlite3` |
| **Perfil** (memoria larga, ADR 0018) | Datos que el usuario cuenta de sí mismo y aprueba guardar: `name`, `workplace`, `role` y `city`, cada uno de hasta 80 caracteres y con datos personales redactados | Un `user_id` anónimo, entre hilos; namespace `("users", user_id, "profile")` | `memory.sqlite3` |
| **Log de turnos** | Una línea JSON por turno: ruta, quién decidió, herramientas, latencia, tokens y fallo de evidencia. Sin la pregunta, la respuesta ni el `user_id` | Todos los hilos | `logs/turns.jsonl` |

No se guardan resúmenes de conversación en la memoria larga, ni texto libre fuera de esas claves. El perfil se
guarda solo cuando la persona aprueba la acción `save_profile`. «¿Dónde trabajo?» o «¿Cómo me llamo?» se
responden sin buscar en el corpus y la respuesta dice si el dato viene del perfil (largo plazo) o del hilo
(corto plazo). `forget_memory` borra preferencias **y** perfil.

## 2. Dónde

Ambos archivos viven en el directorio de estado, **siempre fuera del repositorio** (regla dura: la app no escribe
en `data/` ni en el repositorio):

- Variable `MANUELITA_STATE_DIR` si está definida.
- Si no, `%LOCALAPPDATA%\manuelita-rag` en Windows o `$XDG_STATE_HOME/manuelita-rag`
  (`~/.local/state/manuelita-rag`) en Linux y macOS.

Si la ruta configurada cae dentro del repositorio, el servidor se niega a arrancar el chat
(`resolve_state_dir`).

## 3. Retención

- **Preferencias**: 30 días desde que se guardan (`memory.preference_ttl_days` en `config/agent.toml`). Cada
  preferencia lleva `created_at` y `expires_at`; las vencidas se borran la próxima vez que se leen.
- **Hilos**: se conservan mientras exista el archivo de estado. Cuando el historial supera
  `memory.summarize_after_tokens` (6.000 tokens estimados), los turnos antiguos se condensan en un resumen que
  conserva entidades, cifras y las URL de las fuentes; los últimos `memory.keep_last_messages` mensajes quedan
  completos.

## 4. Cómo se guarda y cómo se borra

Toda escritura pasa por **aprobación humana** (regla de oro: lectura automática, escritura con aprobación):

1. La persona pide algo como «Prefiero respuestas en viñetas», «Olvida mis preferencias» o «Exporta la
   conversación», o pulsa «Olvidar» en la web (`DELETE /api/memory/{user_id}?thread_id=…`).
2. El asistente **propone** la acción (`save_preference`, `forget_memory` o `export_conversation`) y el hilo
   queda en `pending_approval`.
3. La persona **aprueba**, **edita** los argumentos o **rechaza**
   (`POST /api/threads/{thread_id}/resume`). Solo con aprobación o edición se ejecuta.
4. La decisión queda registrada en `actions[]` del hilo, con argumentos finales y fecha. La espera sobrevive a
   un reinicio del servidor.

Consulta: `GET /api/memory/{user_id}` lista las preferencias vigentes con sus fechas. En la web aparecen sobre
la conversación («Tus preferencias»).

Las preferencias vigentes se agregan al system prompt de ambas variantes como bloque
«Preferencias declaradas por el usuario»: cambian la forma de responder, nunca la evidencia ni las reglas de
cita.

## 5. Privacidad (FR-010)

- El `user_id` es un identificador anónimo generado en el navegador (`anon-…`); no hay cuentas ni nombres.
- Los datos personales se **redactan antes de persistir**, con el mismo formato que `PIIMiddleware`
  (`[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `[REDACTED_DOCUMENT]`, `[REDACTED_CREDIT_CARD]`):
  - en el mensaje del usuario, antes de guardarlo en el hilo;
  - en el valor de una preferencia, antes de escribirlo en el Store;
  - en la entrada del modelo de la variante agente (`PIIMiddleware` en modo `redact`).
- Detectores: correo y tarjeta (LangChain); teléfono celular o fijo colombiano y documento de identidad
  (cédula, NIT, pasaporte, tarjeta de identidad) con patrones propios en `agent/privacy.py`. Las cifras de
  negocio («1.864 toneladas») no se tocan.
- Las herramientas de escritura no reciben `user_id` ni `thread_id` del modelo: el servidor los toma del hilo,
  así el modelo no puede escribir en la memoria de otra persona.

## 6. Trazas opcionales (LangSmith)

La trazabilidad con LangSmith está desactivada por defecto. Para activarla en un entorno local, define en `.env`
`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` y, si quieres, `LANGSMITH_PROJECT` (por defecto
`manuelita-modulo2`). Cada turno se etiqueta con la variante y el modo y lleva el `thread_id` como metadato;
`GET /api/observability` confirma si las trazas están activas. Las trazas incluyen los mensajes del hilo ya redactados;
no la actives con datos reales de usuarios sin revisar la política del proyecto.
