# ADR 0006 — Modelo local Ollama para el Módulo 1

- **Estado**: aceptada
- **Fecha**: 2026-10-30
- **Autores**: Jason Alejandro Castaño, Roberto José Guerrero
- **Contexto**: Módulo 1, tarea M1-04

## Contexto

El Módulo 1 exige tres tareas con LangChain: Resumen, FAQ y Q&A. La constitución permite un modelo open
source vía Ollama o un modelo privado vía API, y exige justificar la elección por costo, latencia, calidad,
idioma y disponibilidad.

El equipo aprobó una solución de **bajo costo** para esta etapa. La prioridad es avanzar sin cuotas de API,
sin claves y con un entorno reproducible.

## Decisión

Usar **Ollama local** con `llama3.1:8b` como modelo principal y `llama3.2:3b` como respaldo para equipos
con poca RAM/VRAM.

| Parámetro | Valor |
|-----------|-------|
| Proveedor | `ollama` |
| Modelo | `llama3.1:8b` |
| Respaldo | `llama3.2:3b` |
| Base URL | `http://localhost:11434` |
| Integración | `langchain-ollama` (`ChatOllama`) |
| Temperatura | 0,1 |
| `top_p` | 0,9 |
| Tokens de salida | 1.024 |
| Contexto (`num_ctx`) | 16.384 |
| Paquete por defecto | 8.000 |
| Timeout | 120 s |
| Reintentos | 1 con backoff de 2 s |
| Semilla | 42 |
| Idioma | Español |

La configuración vive en `config/llm.toml`. Los secretos, si se añaden en el futuro, se leen de variables de
entorno; `.env` no se versiona.

## Implementación

- `src/proyecto_modelos_lenguaje/llm.py`:
  - `LLMConfig` y `load_llm_config`;
  - `build_chat_model` para `ChatOllama`;
  - `build_fake_model` para pruebas offline;
  - `invoke_with_retries`;
  - `health_check` y CLI `--check` / `--print-config`;
  - errores `LLMConfigError`, `LLMUnavailableError`, `LLMModelMissingError`, `LLMResponseError`.
- `config/llm.toml` versionado.
- `.env.example` con `OLLAMA_BASE_URL`; `.env` ignorado.
- Pruebas unitarias y de contrato sin red; prueba de integración opcional con
  `OLLAMA_RUN_INTEGRATION=1`.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| OpenAI/Anthropic/Google desde el inicio | Costo por token y dependencia de cuota/red |
| `llama3.2:3b` como principal | Menor calidad; se prefiere solo como respaldo |
| `gemma2:9b` como principal | Contexto de 8k limita el paquete de 32k |
| Implementación directa contra la API de Ollama | LangChain es obligatorio; `langchain-ollama` reduce código |
| Modelo fine-tuned | Fuera de alcance y sin datos de entrenamiento |

## Consecuencias

- Costo variable cercano a cero; el costo real es hardware y electricidad.
- Funcionamiento offline y sin claves.
- La calidad depende del hardware y del modelo local; se medirá en M1-06/M1-08.
- El paquete de 8k se usa por defecto; 32k solo si el equipo lo soporta.
- La integración con Ollama es reemplazable: cambiar de proveedor implica cambiar `llm.py` y la configuración,
  no las tareas.

## Validación observada

- Ollama instalado: `0.40.5`, servidor activo en `127.0.0.1:11434`.
- Modelo `llama3.1:8b` descargado (4,9 GB).
- `uv run python -m proyecto_modelos_lenguaje.llm --print-config`: configuración efectiva, sin secretos.
- `uv run python -m proyecto_modelos_lenguaje.llm --check`: devuelve `0` con `"ok": true` y latencia de
  ~2,1 s en frío.
- Invocación real con LangChain: respuesta `OK` en 7,75 s con el prompt “Responde solo con la palabra OK”.
- Prueba de integración real: `OLLAMA_RUN_INTEGRATION=1 uv run pytest tests/integration/test_llm_ollama.py`
  pasa.
- Pruebas: 185 recolectadas; 184 pasan y 1 se omite por defecto (la integración real, que pasa cuando se
  habilita).
- Ruff limpio y CI verde.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| El equipo no tiene RAM/VRAM suficiente para 8B | Cambiar a `llama3.2:3b` en `config/llm.toml` |
| Generación lenta en CPU | Usar el paquete de 8k, bajar `max_output_tokens` o usar 3B |
| Modelo no descargado | `--check` indica `ollama pull <modelo>` |
| Servidor apagado | `--check` indica `ollama serve` |
| Calidad insuficiente en español | Evaluar `qwen2.5:7b` o `mistral:7b` y registrar la decisión |

## Licencias

- Ollama es software local; su licencia se rige por el proyecto oficial.
- `langchain`, `langchain-core`, `langchain-ollama` y `python-dotenv` son dependencias MIT/BSD compatibles
  con el proyecto.
- Los modelos descargados conservan su licencia original; no se versionan en el repositorio.
