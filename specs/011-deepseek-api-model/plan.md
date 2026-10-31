# Implementation Plan: Modelo DeepSeek vía API en lugar de Ollama local

**Branch**: `feat/010-deepseek-api-model` | **Date**: 2026-10-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-deepseek-api-model/spec.md`

## Summary

Sustituir el modelo local de Ollama (`llama3.1:8b`) por **DeepSeek V4.1 Flash 1017** consumido por API,
manteniendo intactos el contrato de las tres tareas (Resumen, FAQ y Q&A), la app, el CLI y las pruebas. El
cambio se concentra en `src/proyecto_modelos_lenguaje/llm.py` y `config/llm.toml`: proveedor
OpenAI-compatible, clave solo por variable de entorno, mapeo de errores del proveedor a errores
controlados, medición de tokens y costo estimado, y modo demostración como única vía sin red.

## Technical Context

**Language/Version**: Python 3.14 (gestión con `uv`).

**Primary Dependencies**: `langchain` y `langchain-core` (ya presentes); se añade `langchain-openai` y se
retira `langchain-ollama`. El proveedor es compatible con la API de chat completions de OpenAI.

**Storage**: sin cambios. La configuración versionada vive en `config/llm.toml`; la clave en `.env`
(ignorado por Git) mediante `DEEPSEEK_API_KEY`.

**Testing**: `pytest` con el modelo falso existente (`build_scripted_model`) para la suite por defecto; las
pruebas del cliente remoto usan un transporte HTTP simulado, sin red ni cuota.

**Target Platform**: biblioteca + CLI + app local; el servicio remoto es externo.

**Project Type**: proyecto único: biblioteca + CLI + app Streamlit.

**Performance Goals**: primera respuesta < 30 s con el proveedor disponible; timeout configurable (60 s por
defecto); reintento único solo ante errores transitorios.

**Constraints**: sin claves en el repositorio; solo se envían fragmentos de evidencia públicos; la suite
no usa red; el modo demostración funciona sin conexión; ninguna escritura en `data/`.

**Scale/Scope**: tres tareas, una app de cuatro vistas, un CLI con dos comandos de diagnóstico y ~365 líneas
actuales en `llm.py`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | Modelo, versión, parámetros y tarifa versionados en `config/llm.toml`; resultados registran modelo y tokens. |
| II. Evaluación con métricas y línea base | PASS | Tokens de entrada/salida, latencia y costo estimado por llamada; comparación posible con la línea base anterior. |
| III. Procedencia y ética de datos | PASS | Solo se envían fragmentos públicos de oro ya citados; sin datos personales; se documenta el tercero. |
| IV. Experimentos como código versionado | PASS | Configuración y prompts versionados; el secreto queda fuera. |
| V. Simplicidad y alcance académico | PASS | Se intercambia un cliente LangChain por otro; sin SDK propio ni orquestación nueva. |
| §3.5 Modelo vía API | PASS | La constitución admite modelo privado vía API con justificación por costo, latencia, calidad, idioma y disponibilidad (ver §Justificación). |
| §3.5 Configuración y claves | PASS | `config/llm.toml` + `.env` documentado; `--print-config` nunca muestra el valor. |
| §3.8 Pruebas offline | PASS | Modelo falso en la suite; transporte simulado para el cliente remoto. |
| §4.3 Seguridad y secretos | PASS | Clave solo por entorno, redacción en logs y en la descarga de sesión. |
| Arquitectura medallion | PASS | Sin escrituras en `data/`; el corpus no cambia. |

### Justificación del proveedor (§3.5)

| Criterio | Evaluación |
|----------|------------|
| Costo | Tarifa por token configurable; el modo demostración permite trabajar sin costo. |
| Latencia | Servicio remoto con timeout y reintento acotado; la latencia se registra por llamada. |
| Calidad | Modelo de generación más reciente que el local anterior; la evaluación de 40 preguntas (M1-08) medirá el efecto. |
| Idioma | Español soportado; los prompts ya exigen español. |
| Disponibilidad | Depende de red y cuota; se compensa con el modo demostración y mensajes accionables. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-deepseek-api-model/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades y validaciones
├── quickstart.md        # Fase 1: validación end-to-end
├── contracts/
│   ├── provider-config.schema.json
│   └── provider-errors.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
config/
└── llm.toml                 # provider=deepseek, modelo, base_url, límites, tarifas

.env.example                 # DEEPSEEK_API_KEY= (sin valor real)

src/proyecto_modelos_lenguaje/
├── llm.py                   # config, cliente, errores, salud, redacción
├── tasks.py                 # sin cambios de contrato; consume `model`
└── app_metrics.py           # sin cambios

app.py                       # panel: proveedor activo y costo estimado de la sesión
tests/
├── unit/test_llm.py         # validación de config, enmascarado, mapeo de errores
├── contract/test_llm_contract.py
└── integration/test_llm_api.py  # transporte simulado, sin red
```

**Structure Decision**: se mantiene el proyecto único y la frontera actual: `llm.py` es el único módulo que
conoce al proveedor; `tasks.py` sigue recibiendo un `BaseChatModel`. Así el cambio de proveedor no toca las
tareas, la app ni los prompts.

## Complexity Tracking

Sin violaciones de la constitución. No se requiere justificación adicional.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. `langchain-openai` con `base_url` propio en lugar de un cliente HTTP artesanal.
2. Identificador de modelo `deepseek-flash` por defecto, configurable y validado en `--check`.
3. Base URL `https://api.deepseek.com/v1`, sobreescribible por entorno.
4. Clave solo en `DEEPSEEK_API_KEY`; `--print-config` muestra el nombre de la variable y si está presente.
5. Mapeo explícito de estados HTTP a errores del proyecto.
6. Reintento solo ante 429, 5xx y timeout.
7. Tokens del proveedor cuando existan; si no, estimación local; costo con tarifa configurable.
8. Salud mediante `GET /models` (no consume tokens) con alternativa de ping mínimo.
9. Modo demostración como única vía offline.
10. Minimización de datos: solo unidades seleccionadas + enunciado.

## Phase 1 — Design & Contracts

### Data model

Ver [data-model.md](./data-model.md). Entidades: `ProviderConfig`, `RemoteCall`, `UsageSummary`,
`ProviderError`, `HealthStatus`.

### Contracts

- [contracts/provider-config.schema.json](./contracts/provider-config.schema.json): forma y validación de
  `config/llm.toml`.
- [contracts/provider-errors.md](./contracts/provider-errors.md): tabla de errores, mensajes accionables y
  contrato de `--check` / `--print-config`.

### Quickstart

Ver [quickstart.md](./quickstart.md). Escenarios: configuración del secreto, verificación, tres tareas,
modo demostración, errores simulados, costo y ausencia de red.

### Re-evaluación post-diseño

| Principio / restricción | Resultado | Evidencia |
|--------------------------|-----------|-----------|
| Reproducibilidad | PASS | Config versionada + resultados con modelo, tokens y latencia. |
| Métricas y línea base | PASS | Costo y tokens por llamada; comparación con la línea base local. |
| Procedencia y ética | PASS | Solo evidencia pública; tercero documentado en la decisión. |
| Experimentos como código | PASS | Contratos y pruebas versionados. |
| Simplicidad | PASS | Un cliente LangChain intercambiado; sin orquestación nueva. |
| Medallion y seguridad | PASS | Sin escrituras; secreto fuera del repositorio y de las salidas. |

## Implementation Phases

### Fase A — Configuración y secreto

1. Reescribir `config/llm.toml` con `provider = "deepseek"`, `model = "deepseek-flash"`,
   `api_key_env = "DEEPSEEK_API_KEY"`, `base_url`, límites y tarifas.
2. Actualizar `.env.example` sin valor real y documentar la variable.
3. Validar en `load_llm_config` que la variable exista cuando se pide el cliente real, y fallar con un
   mensaje accionable si no.

### Fase B — Cliente y errores

1. Sustituir `ChatOllama` por el cliente OpenAI-compatible con `base_url`, timeout y reintentos.
2. Implementar la jerarquía de errores y el mapeo desde estados HTTP y excepciones de red.
3. Reintentar solo errores transitorios; no reintentar autenticación.
4. Enmascarar la clave en cualquier salida, log o serialización.

### Fase C — Salud, tokens y costo

1. Reescribir `health_check` contra el proveedor (validar clave y modelo disponible).
2. Registrar tokens del proveedor cuando existan y estimar si no.
3. Calcular costo estimado con la tarifa configurada y exponerlo en el panel.

### Fase D — App, CLI y modo demostración

1. Mantener el modo demostración como única vía offline y rotularlo.
2. Ajustar el panel para mostrar proveedor, modelo y costo de la sesión.
3. Actualizar los mensajes accionables de la app y del CLI.

### Fase E — Pruebas y retirada de Ollama

1. Pruebas de configuración, enmascarado y mapeo de errores con transporte simulado.
2. Pruebas de que la suite no usa red.
3. Retirar `langchain-ollama` y las referencias a Ollama en documentación y scripts.

## Testing Strategy

| Nivel | Qué cubre | Fixtures |
|-------|-----------|----------|
| Unitario | Validación de config, enmascarado, mapeo de estados, cálculo de costo | `tests/unit/test_llm.py` |
| Contrato | Forma de `config/llm.toml` y salidas de `--check` / `--print-config` | `tests/contract/test_llm_contract.py`, `jsonschema` |
| Integración | Cliente con transporte simulado: éxito, 401, 429, timeout, 5xx, respuesta vacía | `tests/integration/test_llm_api.py` |
| Manual | Verificación real con la clave del equipo | quickstart |

**Regla**: la suite por defecto no usa red ni consume cuota.

## Risks & Mitigations

| Riesgo | Mitigación |
|--------|------------|
| Filtración de la clave | Solo por entorno; redacción en logs y salidas; prueba que busca la clave en artefactos. |
| Identificador de modelo inexistente | `--check` valida contra el catálogo del proveedor; el id es configurable. |
| Cambio de precio del proveedor | Tarifa configurable; el costo es estimado, nunca facturación. |
| Latencia o caída del servicio | Timeout, reintento acotado y modo demostración. |
| Costo descontrolado en pruebas | Modelo falso por defecto; nunca se ejecutan pruebas contra el servicio real. |
| Dependencia de red en la demo | Modo demostración rotulado y documentado. |
| Datos enviados a un tercero | Solo fragmentos públicos ya citados; se documenta en la decisión. |
| Ruptura del contrato de tareas | Las tareas no cambian: reciben un `BaseChatModel`. |

## Acceptance Mapping

| Requisito | Prueba / evidencia |
|-----------|--------------------|
| FR-001, FR-010 | Config nueva + tareas ejecutadas con el cliente remoto |
| FR-002, FR-015, FR-019 | Pruebas de enmascarado y búsqueda de la clave en artefactos |
| FR-003, FR-018 | Esquema de configuración y validación de modelo |
| FR-004 | `--check` con casos disponible / clave inválida / modelo inexistente |
| FR-005 | Suite de tareas existente en verde |
| FR-006, FR-017 | Tokens, latencia y costo en resultados y panel |
| FR-007, FR-016 | Modo demostración sin red |
| FR-008, FR-009 | Mapeo de errores y reintentos en pruebas de integración |
| FR-011 | Inspección del payload enviado en la prueba simulada |
| FR-012 | Timeout cancelado en prueba simulada |
| FR-013 | Prompts en español sin cambios |
| FR-014, SC-010 | Sin escrituras en `data/`; corpus intacto |
| FR-020, SC-005 | Suite offline < 2 min |
| SC-001…SC-009 | quickstart + pruebas |

## Next Steps

1. Ejecutar `/speckit.tasks` para generar el backlog.
2. Implementar la Fase A (configuración y secreto) y validar `--print-config`.
3. Implementar la Fase B y C, y solo entonces retirar `langchain-ollama`.
