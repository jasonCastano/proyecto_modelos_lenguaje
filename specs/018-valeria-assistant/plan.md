# Implementation Plan: Valer-IA Caña, asistente virtual conversacional de Manuelita

**Branch**: `018-valeria-assistant` | **Date**: 2026-11-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-valeria-assistant/spec.md`

## Summary

El chat pasa de demostración académica a asistente para visitantes, **Valer-IA Caña**:

1. **US1 (P1), bienvenida**: `GET /api/welcome` sirve una plantilla versionada (`prompts/welcome.md`) con datos de
   Manuelita citados al oro. La interfaz la muestra como primer mensaje y la lee con la voz y el avatar.
2. **US2 (P2), visitas y reconocimiento**:
   - El cliente anónimo vive en `sessionStorage`, así que cada visita empieza limpia.
   - Un paso determinista de identidad (`agent/identity.py`) y un nodo `identify` en los dos grafos reconocen al
     cliente por la huella HMAC del correo más la confirmación del nombre, con límites de intentos.
   - Para recordar a un cliente nuevo se usa la acción `remember_client`, con aprobación conversacional.
   - El correo nunca entra al grafo ni al modelo.
3. **US3 (P3), conducta**:
   - El enrutador gana `scope_reason`, con siete motivos y respuestas deterministas de Valer-IA en
     `prompts/conduct.md`.
   - Cuando se redactan datos sensibles, la respuesta incluye un aviso.
   - Hay reglas nuevas en el prompt del agente (v1.3).
   - Una batería `agent conduct` mide el cumplimiento.
4. **US4 (P4), interfaz**: la vista normal muestra solo lo que necesita un visitante y usa respuestas rápidas para
   el consentimiento. La vista técnica (`?vista=tecnica`) conserva la demostración.

Las decisiones están en [research.md](./research.md), R1–R9.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5.9 + React 19 (frontend)

**Primary Dependencies**: las existentes (FastAPI, LangGraph/LangChain, Pydantic) y `hmac` y `hashlib` de la
librería estándar. **Sin dependencias nuevas.**

**Storage**:
- Store de LangGraph en `MANUELITA_STATE_DIR`:
  - namespace nuevo `("identities",)`: huella → `user_id`, `created_at`;
  - namespace nuevo `("identity_failures", huella)`: fallos con `expires_at`.
- `identity.key` en `MANUELITA_STATE_DIR`, si no se define `MANUELITA_IDENTITY_KEY`.
- En el navegador: `sessionStorage` para el cliente, el hilo, la bienvenida mostrada o hablada y la vista.

**Testing**:
- pytest:
  - identidad: huella, normalización, comparación de nombres, límites y que el correo nunca persista;
  - nodo `identify` en los dos grafos;
  - motivos del enrutador y respuestas de conducta;
  - aviso de datos sensibles;
  - contrato de `/api/welcome` y de los campos nuevos de `ChatResponse`;
  - batería `agent conduct` en modo demo.
- Vitest: bienvenida (texto y voz con desbloqueo), cliente en `sessionStorage`, adopción de `user_id`,
  `client_reset`, vista normal y técnica, y `QuickReplies`.
- Pruebas con red (`@network`): `agent conduct --mode real`.

**Target Platform**: servidor local o de despliegue con `make app`; navegadores modernos.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI de evaluación.

**Performance Goals**:
- Bienvenida visible en menos de 2 s (SC-001): `/api/welcome` sin LLM, en menos de 50 ms en el servidor.
- Turnos de identidad sin llamar al LLM, en menos de 300 ms.
- Reconocimiento en menos de 2 s (SC-002).

**Constraints**:
- El correo en texto plano nunca se persiste ni se envía al modelo, a las trazas ni a los registros (FR-013,
  SC-007).
- Toda escritura en la memoria sigue con aprobación humana (FR-025).
- Las pruebas corren sin red.
- No se presenta como asesoría oficial (CONSTITUTION §10).

**Scale/Scope**: 7 motivos de conducta, 24 casos de evaluación, 1 nodo nuevo por grafo, 1 acción nueva, 1 endpoint
nuevo y campos opcionales en `ChatResponse`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Autoría y uso de IA | Los commits los hace el equipo (§4.3). Valer-IA se declara como inteligencia artificial (FR-005). | ✅ |
| II. Reproducibilidad | Los prompts nuevos (`welcome.md`, `conduct.md`) y las versiones de `agent.md` y `router.md` quedan en `prompts/` y `docs/prompt_log.md`. La batería de conducta está versionada. | ✅ |
| III. Ética y legalidad | El correo es un dato personal: solo se guarda una huella HMAC, con consentimiento explícito (HITL), y se puede olvidar. Se documenta en `docs/memoria.md` §5. | ✅ |
| IV. Generación anclada | La bienvenida cita unidades del oro verificadas por prueba. Las respuestas siguen con citas y declaran la falta de evidencia. Los canales oficiales salen solo del corpus. | ✅ |
| V. Evaluación empírica | La batería de conducta (SC-004) se ejecuta en modos demo y real. Se vuelve a evaluar el Módulo 2 para descartar regresiones (SC-008). | ✅ |
| VII. Simplicidad | No hay dependencias nuevas. La identidad usa reglas, el Store existente y HITL. | ✅ |
| §3.7 App web | La interfaz cambia a la de un visitante; la vista técnica conserva la demostración de la rúbrica. | ✅ |
| §3.9 Seguridad | `MANUELITA_IDENTITY_KEY` va en `.env` y `.env.example` sin valor. La clave generada vive en el directorio de estado. Hay límites contra el sondeo. | ✅ |
| §10 No es asesoría oficial | La bienvenida incluye una nota de transparencia y Valer-IA no se declara canal autorizado (FR-003, FR-005). | ✅ |

**Resultado**: PASS. No hay violaciones que justificar.

**Re-check post-diseño (Phase 1)**: PASS. Los contratos añaden un endpoint y campos opcionales; `/api/chat` y
`/api/chat/stream` siguen siendo compatibles. La vista técnica conserva todo lo que usa la rúbrica.

## Project Structure

### Documentation (this feature)

```text
specs/018-valeria-assistant/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── api-changes.md        # GET /api/welcome; ChatResponse.client / notices; user_id adoptado
│   ├── identity-flow.md      # Máquina de estados conversacional del reconocimiento
│   ├── conduct.md            # scope_reason, respuestas y batería `agent conduct`
│   └── ui-views.md           # Vista normal vs. técnica, bienvenida, QuickReplies
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
prompts/
├── welcome.md            # NUEVO v1.0: bienvenida con citas al oro
├── conduct.md            # NUEVO v1.0: respuestas deterministas por motivo, saludo, despedida, aclaración
├── agent.md              # v1.3: personaje Valer-IA, transparencia, conducta, canales oficiales
└── router.md             # + scope_reason

src/proyecto_modelos_lenguaje/agent/
├── identity.py           # NUEVO: normalización, huella HMAC, clave, IdentityRegistry (Store), fallos, nombres
├── router.py             # + patrones por motivo; RouteDecision.scope_reason
├── models.py             # + scope_reason en el esquema de la decisión
├── graph.py              # + nodo identify al inicio; respuestas desde conduct.md; aviso pii; oferta de recordar
├── actions.py            # + RememberClientArgs; ejecución: guardar nombre + vincular huella
├── service.py            # _prepare: identidad antes de redactar; adopción de user_id; client_reset; notices
├── conduct.py            # NUEVO: casos, ejecución y reporte de la batería de conducta
├── welcome.py            # NUEVO: carga y valida prompts/welcome.md
└── __main__.py           # + subcomando `conduct`
src/proyecto_modelos_lenguaje/api.py, api_models.py   # GET /api/welcome; ChatResponse.client/notices

web/src/
├── lib/session.ts        # NUEVO: cliente/hilo/vista/bienvenida en sessionStorage
├── components/WelcomeMessage.tsx  # NUEVO
├── components/QuickReplies.tsx    # NUEVO
├── components/ChatView.tsx        # vista normal/técnica; adopción de user_id; client_reset; nombre Valer-IA
└── test/…                          # pruebas nuevas

tests/
├── unit/agent/test_identity.py, test_conduct_router.py, test_welcome.py
├── integration/agent/test_identify_node.py (cadena y agente), test_conduct_eval.py
├── api/test_valeria_api.py
├── fixtures/conduct/conduct_cases.jsonl
└── integration/agent/test_conduct_real.py   # @network

docs/
├── decisions/0022-valeria-asistente.md
├── evaluacion_conducta.md / .json            # generado por `agent conduct --mode real`
├── memoria.md (§5 correo), prompt_log.md, demo.md, README.md
CONSTITUTION.md (v1.10.0), .env.example (MANUELITA_IDENTITY_KEY)
```

**Structure Decision**: la identidad y la conducta se resuelven con reglas, en módulos propios y en un nodo
determinista al inicio de los grafos, para que la seguridad no dependa del modelo de lenguaje. El personaje vive en
prompts versionados. La interfaz separa la vista de visitante de la técnica sin duplicar componentes.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
