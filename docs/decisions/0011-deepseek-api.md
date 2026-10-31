# ADR 0011 — Modelo DeepSeek por API en lugar de Ollama local

- **Fecha**: 2026-10-31
- **Estado**: Aceptada
- **Contexto**: spec `010-deepseek-api-model`. El Módulo 1 usaba `llama3.1:8b` servido por Ollama en el
  equipo; el equipo pasa a consumir **DeepSeek V4.1 Flash 1017** como servicio remoto.

## Contexto

La constitución (§3.5) admite modelo open source vía Ollama **o** privado vía API, siempre que la elección
se justifique por costo, latencia, calidad, idioma y disponibilidad, y que las claves se lean de `.env`. El
modelo local exigía instalar y mantener un runtime por equipo, descargar ~5 GB y repetir la descarga en cada
máquina; además ataba la demo al hardware disponible.

## Decisión

1. **Proveedor**: DeepSeek V4.1 Flash 1017 vía API compatible con *chat completions* de OpenAI, consumido con
   `langchain-openai` (`base_url` configurable). Se retira `langchain-ollama`.
2. **Modelo**: `deepseek-flash` por defecto en `config/llm.toml`, sobreescribible con `DEEPSEEK_MODEL` y
   validado por `--check` contra el catálogo del proveedor.
3. **Secreto**: solo `DEEPSEEK_API_KEY`, leída de `.env` (ignorado por Git). La configuración rechaza campos
   como `api_key`, `token`, `secret` o `password`; `--print-config` expone `api_key_env` y
   `api_key_present`, nunca el valor.
4. **Errores**: jerarquía propia (`LLMAuthError`, `LLMRateLimitError`, `LLMTimeoutError`,
   `LLMModelMissingError`, `LLMUnavailableError`, `LLMResponseError`, `LLMConfigError`) con código y mensaje
   accionable; se mapean a `model_timeout`, `model_error` o `invalid_config` en `TaskResult`.
5. **Reintentos**: los gestiona el cliente (solo 429/5xx/timeout, nunca 401/403), con `max_retries`
   configurable.
6. **Uso y costo**: se usan los tokens que reporta el proveedor (con respaldo en `estimate_tokens`) y se
   calcula un costo estimado con tarifas configurables; el panel lo muestra o indica «costo no configurado».
7. **Offline**: el modelo de demostración (`build_scripted_model`) es la única vía sin red y sin costo, y la
   app lo rotula de forma persistente.
8. **Datos enviados**: solo el enunciado de la tarea y las unidades de evidencia públicas seleccionadas.

### Justificación §3.5

| Criterio | Evaluación |
|----------|------------|
| Costo | Tarifa por token configurable y modo demo sin costo; desaparece la descarga de 5 GB por equipo. |
| Latencia | Servicio remoto con timeout de 60 s y reintento acotado; la latencia se registra por llamada. |
| Calidad | Modelo de generación reciente; la evaluación de 40 preguntas (M1-08) medirá el efecto real. |
| Idioma | Español soportado; los prompts ya exigen español. |
| Disponibilidad | Depende de red y cuota; se compensa con el modo demo y mensajes accionables. |

## Consecuencias

- **Positivas**: sin runtime local, sin descarga de modelos, misma interfaz `BaseChatModel`, errores
  clasificados y costo visible. La suite sigue siendo offline con el modelo falso y un transporte simulado.
- **Negativas**: dependencia de red y de cuota, y envío de fragmentos públicos a un tercero (documentado).
  La línea base de calidad anterior (Ollama) deja de ser comparable directamente.
- **Riesgo aceptado**: el identificador `deepseek-flash` y las tarifas deben confirmarse con la cuenta; ambos
  son configurables y `--check` detecta un modelo inexistente.

## Alternativas consideradas

| Alternativa | Por qué no |
|-------------|------------|
| Mantener Ollama y añadir DeepSeek | Duplica mantenimiento y contradice el reemplazo pedido. |
| Cliente HTTP propio con la biblioteca estándar | Más código para streaming, reintentos y errores; LangChain ya aporta el cliente. |
| Clave en `config/llm.toml` | Filtración inmediata en un repositorio público. |
| Reintentar todos los errores | Gastaría cuota ante una clave inválida y retrasaría el mensaje correcto. |

## Evidencia

- `src/proyecto_modelos_lenguaje/llm.py`, `config/llm.toml`, `.env.example`.
- `tests/unit/test_llm.py`, `tests/contract/test_llm_contract.py` y `tests/integration/test_llm_api.py`
  (transporte simulado: éxito, 401, 404, 429, 500, timeout y respuesta vacía).
- `specs/010-deepseek-api-model/quickstart.md` para la verificación con la clave real.
