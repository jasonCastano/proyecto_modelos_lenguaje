# Fase 0 — Investigación: DeepSeek por API en lugar de Ollama local

**Feature**: `010-deepseek-api-model`
**Fecha**: 2026-10-31
**Estado**: decisiones cerradas; sin `NEEDS CLARIFICATION`.

## 1. Cliente del proveedor

- **Decisión**: usar `langchain-openai` con `base_url` apuntando al proveedor DeepSeek y retirar
  `langchain-ollama`.
- **Racional**: DeepSeek expone una API compatible con *chat completions* de OpenAI; el cliente de LangChain
  mantiene la interfaz `BaseChatModel` que ya consumen `tasks.py` y la app, aporta manejo de errores y
  metadatos de uso, y evita mantener un cliente HTTP propio. La constitución exige LangChain para las tres
  tareas, así que un SDK suelto tampoco es opción.
- **Alternativas consideradas**:
  - Cliente HTTP con `urllib`: sin dependencia nueva, pero hay que reimplementar streaming, reintentos y
    errores; más código que mantener para el mismo resultado.
  - SDK `openai` directo: rompe la regla de LangChain y obliga a adaptar las tareas.
  - Mantener Ollama y añadir DeepSeek como segundo proveedor: la especificación pide reemplazar, no sumar.

## 2. Identificador del modelo

- **Decisión**: `model = "deepseek-flash"` por defecto en `config/llm.toml`, sobreescribible con
  `DEEPSEEK_MODEL`, y validado en `--check` contra el catálogo del proveedor.
- **Racional**: el identificador exacto depende de la cuenta y del catálogo del proveedor; dejarlo en
  configuración evita un valor inventado en el código y permite corregirlo sin tocar Python. El valor por
  defecto coincide con el identificador usado por el entorno del curso.
- **Alternativas consideradas**:
  - Fijarlo en el código: obliga a un cambio de código para corregir un nombre.
  - Usar el nombre comercial («DeepSeek V4.1 Flash 1017») como identificador: puede no coincidir con el id
    real de la API.

## 3. URL base y proveedor

- **Decisión**: `provider = "deepseek"`, `base_url = "https://api.deepseek.com/v1"`, sobreescribible con
  `DEEPSEEK_BASE_URL`.
- **Racional**: es el endpoint compatible con OpenAI que el cliente espera; mantenerlo en configuración
  permite apuntar a un proxy institucional sin cambiar código.
- **Alternativas consideradas**:
  - Endpoint específico del proveedor: no aporta nada al caso de uso.
  - Delegar en la URL por defecto del SDK: impide cambiar de puerta sin tocar código.

## 4. Manejo del secreto

- **Decisión**: la clave se lee solo de `DEEPSEEK_API_KEY` (`.env` para desarrollo local) y nunca se
  escribe en `config/llm.toml`. `--print-config` muestra `api_key_env` y un booleano `api_key_present`.
- **Racional**: `.env` ya está en `.gitignore`; el valor no entra en el historial ni en las salidas. La app
  y la descarga de sesión no incluyen credenciales.
- **Alternativas consideradas**:
  - Clave en el TOML: filtración inmediata en un repositorio público.
  - Gestor de secretos en la nube: desproporcionado para un proyecto académico local.
  - Pedir la clave por interfaz: añade superficie y no resuelve el CLI.

## 5. Errores del proveedor

- **Decisión**: mapear estados y excepciones a errores del proyecto con mensajes accionables:

  | Situación | Error del proyecto | Mensaje |
  |-----------|--------------------|---------|
  | Sin clave | `LLMConfigError` | «Define `DEEPSEEK_API_KEY` en `.env`» |
  | 401 / 403 | `LLMAuthError` | «La clave no es válida o fue revocada» |
  | 404 / modelo desconocido | `LLMModelMissingError` | «El modelo no está disponible en la cuenta» |
  | 429 | `LLMRateLimitError` | «Cuota agotada: espera o usa el modo demostración» |
  | Timeout | `LLMTimeoutError` | «El proveedor no respondió en N s» |
  | 5xx / red caída | `LLMUnavailableError` | «Proveedor no disponible: reintenta o usa demo» |
  | Respuesta vacía | `LLMResponseError` | «Respuesta vacía inutilizable, reintenta» |

- **Racional**: la app ya distingue errores y propone acciones; conservar esa forma evita cambios en la
  interfaz y mantiene los códigos `model_error` / `model_timeout` del contrato de tareas.
- **Alternativas consideradas**:
  - Un único error genérico: el usuario no sabe si el problema es su clave, su cuota o la red.
  - Exponer el mensaje crudo del proveedor: puede incluir detalles internos o repetir la clave en un eco.

## 6. Reintentos

- **Decisión**: reintentar una sola vez (configurable) solo ante 429, 5xx y timeout; nunca ante 401/403 ni
  ante un modelo inexistente.
- **Racional**: reintentar un error de autenticación solo gasta cuota y retrasa el mensaje correcto.
- **Alternativas consideradas**:
  - Reintentar todo: enmascara fallos de configuración.
  - Sin reintentos: los cortes transitorios de red se vuelven errores visibles.

## 7. Tokens y costo

- **Decisión**: usar los tokens reportados por el proveedor; si no llegan, estimar con
  `silver.cleaning.estimate_tokens`. El costo se calcula con tarifas configurables por millar de tokens de
  entrada y salida.
- **Racional**: el costo es una métrica más del experimento; no requiere facturación exacta, pero sí
  trazabilidad y una base para comparar con el modelo local.
- **Alternativas consideradas**:
  - Estimar siempre: ignora los tokens reales que el proveedor ya devuelve.
  - No registrar costo: pierde el argumento de la justificación §3.5.

## 8. Verificación de salud

- **Decisión**: `--check` consulta el catálogo de modelos (`GET /models`) para validar clave y
  disponibilidad del modelo; no consume tokens. Si el catálogo no existe, se hace una petición mínima.
- **Racional**: verificar antes de generar evita gastar cuota en un diagnóstico y detecta el id de modelo
  equivocado, que es el fallo más probable.
- **Alternativas consideradas**:
  - Enviar un prompt de prueba: consume tokens y añade latencia.
  - Solo comprobar que la clave tiene formato: no detecta una clave revocada.

## 9. Modo sin red y sin costo

- **Decisión**: el modelo falso (`build_scripted_model`) sigue siendo la única vía offline; la app lo rotula
  y la configuración permite activarlo por entorno (`PML_DEMO`).
- **Racional**: al retirar Ollama no queda modelo local; sin un modo offline la demo y las pruebas dejan de
  ser reproducibles sin red.
- **Alternativas consideradas**:
  - Mantener Ollama solo para offline: contradice «cambiar» y duplica mantenimiento.
  - Caché de respuestas: no cubre preguntas nuevas.

## 10. Minimización de datos enviados

- **Decisión**: solo se envían el enunciado de la tarea y las unidades de evidencia seleccionadas del corpus
  público; nada de la sesión, del panel ni del catálogo.
- **Racional**: el corpus es información pública ya citada; limitar el payload reduce exposición y costo.
- **Alternativas consideradas**:
  - Enviar el paquete completo: más tokens, más costo, misma utilidad.
  - Enviar metadatos del catálogo: no aportan a la respuesta.

## 11. Retirada de Ollama

- **Decisión**: eliminar `langchain-ollama`, las claves `keep_alive`/`seed` específicas y las referencias en
  README, `.env.example` y scripts; conservar `build_fake_model` y el modo demostración.
- **Racional**: dejar dependencias y variables muertas confunde a quien clone el repositorio y rompe la
  reproducibilidad de la configuración.
- **Alternativas consideradas**:
  - Dejar Ollama como opción oculta: mantiene dependencias y pruebas que ya no se ejecutan.
  - Eliminar el modo demostración: rompe offline y las pruebas.

## 12. Trazabilidad del cambio

- **Decisión**: registrar la decisión en `docs/decisions/0011-deepseek-api.md` con la justificación §3.5
  (costo, latencia, calidad, idioma y disponibilidad) y actualizar `docs/prompt_log.md` con la nueva línea
  base.
- **Racional**: la constitución exige justificar la elección del modelo y mantener el registro de
  experimentos; el cambio de proveedor invalida la línea base anterior.
- **Alternativas consideradas**:
  - Solo documentarlo en el README: no cumple el registro de decisiones.
  - Reutilizar la ADR 0006 (Ollama): mezcla dos decisiones distintas.
