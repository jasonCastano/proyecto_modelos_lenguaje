# Especificación técnica — Configuración del modelo y entorno (M1-04)

**Feature**: `006-llm-ollama-config`
**Versión**: 1.0
**Fecha**: 2026-10-30
**Estado**: Implementada
**Responsable**: Roberto José Guerrero (LLM y aplicación)
**Tarea**: M1-04 — Configurar modelo y entorno

---

## 1. Contexto y objetivo

El Módulo 1 exige tres tareas con LangChain: **Resumen**, **FAQ** y **Q&A**. Antes de escribirlas hay que
resolver el “enchufe” con el modelo: qué modelo se usa, con qué parámetros, cómo se autentica, cómo se
comporta ante errores y cómo se prueba sin red.

La decisión de bajo costo aprobada es **Ollama local**. Esta especificación define la configuración, el
adaptador y los criterios de aceptación para M1-04. No implementa prompts ni cadenas; eso es M1-05.

**Resultado esperado**: un modelo de LangChain construible desde `config/llm.toml`, con un adaptador falso
para pruebas offline, un chequeo de salud y errores accionables.

---

## 2. Alcance

### Dentro de alcance

- Añadir las dependencias de LangChain y Ollama.
- Crear `config/llm.toml` versionado, sin secretos.
- Crear `.env.example` y proteger `.env` en `.gitignore`.
- Crear `src/proyecto_modelos_lenguaje/llm.py` con:
  - carga y validación de configuración;
  - construcción del modelo LangChain;
  - modelo falso para pruebas;
  - chequeo de salud;
  - errores controlados.
- Pruebas unitarias y de contrato offline.
- Documentar la decisión de modelo y el procedimiento de instalación.

### Fuera de alcance

- Prompts de Resumen, FAQ y Q&A.
- Cadenas de LangChain y recuperación.
- App Streamlit.
- Evaluación de las 40 preguntas.
- Embeddings, base vectorial o memoria (Módulo 2).
- Fine-tuning o entrenamiento.
- Uso de APIs privadas de pago en esta etapa.

---

## 3. Decisiones de diseño

| Decisión | Valor propuesto | Justificación |
|----------|-----------------|---------------|
| Proveedor | **Ollama local** | Costo cero por token, sin claves, reproducible en el equipo |
| Modelo por defecto | **`llama3.1:8b`** | Buen equilibrio calidad/tamaño y español aceptable; 8B cabe en equipos de 16 GB |
| Modelo de respaldo | **`llama3.2:3b`** | Alternativa para equipos con poca RAM/VRAM |
| Integración | `langchain-ollama` (`ChatOllama`) | LangChain es obligatorio y `ChatOllama` es la integración oficial |
| Contexto por defecto | **16.384 tokens** (`num_ctx`) | Cubre el paquete de 8k con margen para prompt y respuesta |
| Paquete de contexto | **8.000 tokens** por defecto | Menor latencia y menor riesgo de truncamiento en CPU |
| Temperatura | **0,1** | Respuestas factuales, poca creatividad |
| `top_p` | **0,9** | Diversidad controlada |
| Tokens de salida | **1.024** | Suficiente para resumen/FAQ/Q&A y controla el costo |
| Timeout | **120 s** | La generación local en CPU puede ser lenta |
| Reintentos | **1** con backoff de 2 s | Tolera fallos transitorios sin bucles largos |
| Semilla | **42** (si el modelo la soporta) | Reproducibilidad aproximada |
| Idioma | **es** | Corpus y usuario principal en español |
| `keep_alive` | **5m** | Evita recargar el modelo entre llamadas |

> **Nota**: `llama3.1:8b` es el candidato inicial. Si el equipo no lo mueve con fluidez, se cambia a
> `llama3.2:3b` sin cambiar el código, solo `config/llm.toml`. La decisión final se registra tras medir
> latencia y calidad en M1-06/M1-08.

---

## 4. Arquitectura

```text
config/llm.toml ──┐
                  ├──► llm.load_llm_config() ──► LLMConfig
.env / entorno ───┘                                │
                                                   ├──► build_chat_model() ──► ChatOllama
                                                   ├──► build_fake_model() ──► FakeListChatModel
                                                   └──► health_check() ──► Ollama /api/tags

M1-05 (cadenas) ──► build_chat_model() ──► Resumen / FAQ / Q&A
M1-07 (app)     ──► build_chat_model() ──► interfaz
Tests           ──► build_fake_model() ──► sin red
```

**Principio**: una sola fábrica de modelos. Ninguna tarea debe instanciar `ChatOllama` directamente.

---

## 5. Configuración versionada: `config/llm.toml`

```toml
[llm]
provider = "ollama"
model = "llama3.1:8b"
base_url = "http://localhost:11434"

temperature = 0.1
top_p = 0.9
max_output_tokens = 1024
context_window = 16384
default_context_pack = "8000"

timeout_seconds = 120
max_retries = 1
retry_backoff_seconds = 2.0
keep_alive = "5m"
seed = 42
language = "es"
```

### 5.1 Reglas de validación

| Campo | Tipo | Regla |
|-------|------|-------|
| `provider` | texto | Solo `ollama` en esta fase |
| `model` | texto | No vacío; sin espacios |
| `base_url` | texto | `http://` o `https://`; por defecto `http://localhost:11434` |
| `temperature` | número | `0.0 <= x <= 1.0` |
| `top_p` | número | `0.0 < x <= 1.0` |
| `max_output_tokens` | entero | `128 <= x <= 8192` |
| `context_window` | entero | `2048 <= x <= 131072` |
| `default_context_pack` | texto | `8000` o `32000`; no puede superar `context_window` |
| `timeout_seconds` | entero | `1 <= x <= 600` |
| `max_retries` | entero | `0 <= x <= 5` |
| `retry_backoff_seconds` | número | `0.0 <= x <= 60.0` |
| `keep_alive` | texto | Formato de duración de Ollama (`5m`, `1h`) |
| `seed` | entero o nulo | Entero no negativo si se define |
| `language` | texto | `es` por defecto |

Un valor inválido debe producir `LLMConfigError` con el campo y el rango esperado.

---

## 6. Entorno y secretos

### 6.1 `.env.example`

```bash
# Copia a .env solo si necesitas cambiar la URL local.
OLLAMA_BASE_URL=http://localhost:11434

# Opcional: override del modelo para pruebas manuales.
# OLLAMA_MODEL=llama3.2:3b
```

- Ollama no requiere API key.
- No se versiona `.env`.
- `.env.example` no contiene valores reales.
- Si en el futuro se añade un proveedor privado, la clave se leerá de una variable de entorno y nunca del
  TOML.

### 6.2 Carga del entorno

- `llm.py` puede cargar `.env` con `python-dotenv` (`load_dotenv(override=False)`) si está instalado.
- Alternativa sin dependencia: ejecutar con `uv run --env-file .env ...`.
- La configuración explícita del TOML prevalece sobre valores por defecto; las variables de entorno solo
  cubren secretos y overrides documentados.

---

## 7. API del módulo `src/proyecto_modelos_lenguaje/llm.py`

```python
@dataclass(frozen=True, slots=True)
class LLMConfig:
    provider: str
    model: str
    base_url: str
    temperature: float
    top_p: float
    max_output_tokens: int
    context_window: int
    default_context_pack: str
    timeout_seconds: int
    max_retries: int
    retry_backoff_seconds: float
    keep_alive: str
    seed: int | None
    language: str


def load_llm_config(path: str | Path = "config/llm.toml") -> LLMConfig: ...
def build_chat_model(config: LLMConfig) -> BaseChatModel: ...
def build_fake_model(responses: list[str] | None = None) -> BaseChatModel: ...
def health_check(config: LLMConfig) -> dict[str, object]: ...
def main(argv: list[str] | None = None) -> int: ...
```

### 7.1 Comportamiento esperado

- `load_llm_config` lee el TOML, valida rangos y resuelve `OLLAMA_BASE_URL` si existe.
- `build_chat_model` devuelve un `ChatOllama` configurado con modelo, `base_url`, `temperature`, `top_p`,
  `num_predict`, `num_ctx`, `keep_alive` y `seed`.
- `build_fake_model` devuelve un modelo determinista de LangChain (`FakeListChatModel` o equivalente) que
  no usa red.
- `health_check` consulta `/api/tags` y verifica que el modelo esté descargado. Devuelve:
  ```json
  {
    "ok": true,
    "provider": "ollama",
    "model": "llama3.1:8b",
    "base_url": "http://localhost:11434",
    "latency_ms": 42,
    "detail": "modelo disponible"
  }
  ```
- `main --check` imprime ese JSON y devuelve `0` si está disponible, `2` si falta el modelo o el servidor.
- `main --print-config` imprime la configuración efectiva sin secretos.

### 7.2 Errores

| Error | Cuándo | Mensaje esperado |
|-------|--------|------------------|
| `LLMConfigError` | TOML inválido, campo fuera de rango | Campo, valor y rango esperado |
| `LLMUnavailableError` | Ollama no responde | “Ejecuta `ollama serve` y verifica `OLLAMA_BASE_URL`” |
| `LLMModelMissingError` | El modelo no está descargado | “Ejecuta `ollama pull llama3.1:8b`” |
| `LLMResponseError` | Respuesta vacía o inválida | “El modelo no devolvió contenido utilizable” |

Los errores no deben incluir claves, tokens ni rutas absolutas.

---

## 8. Modelos candidatos y hardware

| Modelo | Parámetros | Contexto típico | Español | Uso previsto |
|--------|-----------:|----------------:|---------|--------------|
| `llama3.1:8b` | 8B | 128k (configurar `num_ctx`) | Bueno | **Candidato principal** |
| `llama3.2:3b` | 3B | 128k | Aceptable | Respaldo para poca RAM/VRAM |
| `qwen2.5:7b` | 7B | 32k | Muy bueno | Alternativa multilingüe |
| `mistral:7b` | 7B | 32k | Bueno | Alternativa rápida |
| `gemma2:9b` | 9B | 8k | Bueno | Solo si se usa el paquete de 8k |

### 8.1 Requisitos de hardware

- **Mínimo**: 16 GB de RAM; CPU; `llama3.2:3b` en cuantización Q4.
- **Recomendado**: GPU con 8 GB de VRAM; `llama3.1:8b` Q4.
- **Contexto 32k**: requiere más memoria; si el equipo no lo soporta, usar el paquete de 8k.
- La elección final se registra con la salida de `ollama list`, la latencia medida y la memoria disponible.

### 8.2 Instalación

```bash
# Instalar Ollama (fuera de uv; es un runtime del sistema)
# Windows/macOS/Linux: seguir el instalador oficial

ollama serve
ollama pull llama3.1:8b
ollama list

# Verificación del proyecto
uv run python -m proyecto_modelos_lenguaje.llm --check
```

---

## 9. Dependencias

Añadir a `pyproject.toml` y fijar en `uv.lock`:

| Dependencia | Uso |
|-------------|-----|
| `langchain` | Framework obligatorio para las tareas del Módulo 1 |
| `langchain-core` | `BaseChatModel`, mensajes y utilidades |
| `langchain-ollama` | Integración `ChatOllama` |
| `python-dotenv` | Carga opcional de `.env` |

No añadir en esta tarea: embeddings, base vectorial, Streamlit ni LangChain experimental.

---

## 10. Pruebas

### 10.1 Unitarias (sin red)

- `test_load_llm_config_defaults`
- `test_load_llm_config_rejects_out_of_range`
- `test_load_llm_config_env_override_base_url`
- `test_build_chat_model_uses_ollama`
- `test_build_fake_model_is_deterministic`
- `test_health_check_reports_missing_model` (con HTTP simulado)
- `test_errors_do_not_leak_secrets`
- `test_print_config_redacts_nothing_sensitive`

### 10.2 Contrato

- `config/llm.toml` cumple el esquema de campos y rangos.
- `.env.example` no contiene valores reales.
- `--check` devuelve un JSON con `ok`, `provider`, `model`, `base_url`, `latency_ms` y `detail`.

### 10.3 Integración opcional

- Marcador `@pytest.mark.ollama`, omitido por defecto.
- Se ejecuta solo con `OLLAMA_RUN_INTEGRATION=1` y un servidor local disponible.
- No forma parte de CI.

**Regla**: `uv run pytest` debe pasar sin Ollama instalado y sin red.

---

## 11. Reproducibilidad y observabilidad

- Registrar en `docs/prompt_log.md` (M1-06): modelo, versión, temperatura, `top_p`, tokens, contexto,
  semilla, latencia y resultado.
- El chequeo de salud debe reportar la versión del modelo si Ollama la expone.
- No registrar claves ni contenido sensible.
- La configuración es versionada; los cambios se hacen en `config/llm.toml` y se registran en el prompt log.
- El modelo local no se versiona; se descarga con `ollama pull`.

---

## 12. Criterios de aceptación

1. `config/llm.toml` existe, está versionado y no contiene secretos.
2. `.env.example` existe; `.env` está en `.gitignore`.
3. `llm.py` carga, valida y construye `ChatOllama` desde la configuración.
4. `uv run python -m proyecto_modelos_lenguaje.llm --check` devuelve `0` con Ollama y el modelo disponibles,
   o un error accionable con código `2`.
5. `build_fake_model()` permite ejecutar pruebas sin red.
6. `uv run pytest` pasa sin Ollama y sin red.
7. `uv run ruff check .` pasa.
8. La elección de modelo y hardware está documentada.
9. Se declara el paquete de contexto por defecto (8k) y el límite `num_ctx` (16k).
10. No se implementan aún prompts, cadenas, app ni evaluación.

---

## 13. Pasos de implementación

1. Añadir dependencias y ejecutar `uv sync`.
2. Crear `config/llm.toml` con los valores de §5.
3. Crear `.env.example` y actualizar `.gitignore`.
4. Crear `src/proyecto_modelos_lenguaje/llm.py` con la API de §7.
5. Implementar `--check` y `--print-config`.
6. Escribir pruebas unitarias y de contrato.
7. Instalar Ollama y descargar `llama3.1:8b` en el equipo de desarrollo.
8. Ejecutar `--check`, medir latencia y ajustar modelo/contexto si hace falta.
9. Registrar la decisión en `docs/decisions/0006-ollama-llm.md` o en el prompt log.
10. Actualizar README con el procedimiento de instalación y verificación.

---

## 14. Decisiones abiertas para refinar

1. **Modelo final**: `llama3.1:8b` vs `llama3.2:3b` según hardware y latencia medida.
2. **Contexto**: 8k por defecto; evaluar 32k solo si el equipo lo soporta y la calidad lo justifica.
3. **Carga de `.env`**: `python-dotenv` vs `uv run --env-file`.
4. **Semilla**: confirmar si el modelo y la versión de Ollama la respetan de forma estable.
5. **Formato estructurado**: si M1-05 necesita JSON, evaluar `format="json"` de Ollama.
6. **Métricas**: latencia y tokens por llamada se medirán en M1-06; aquí solo se deja el gancho.

---

## 15. Referencias

- `CONSTITUTION.md` §3.5 (modelo, framework y tareas), §3.6 (prompt engineering), §3.7 (app), §4.3
  (seguridad y secretos).
- `docs/alcance.md` (40 preguntas y fronteras del alcance).
- `docs/data_card.md` (corpus y limitaciones).
- `specs/005-scrape-empresa-entrypoint/spec.md` (patrón de entrada canónica).
- Ollama: `https://ollama.com/`.
- LangChain Ollama: `https://python.langchain.com/docs/integrations/chat/ollama/`.

---

## 16. Resultados de implementación (2026-10-30)

| Elemento | Resultado |
|----------|-----------|
| `config/llm.toml` | Creado con proveedor `ollama`, modelo `llama3.1:8b`, contexto 16k y paquete 8k |
| `.env.example` | Creado con `OLLAMA_BASE_URL`; sin claves |
| `src/proyecto_modelos_lenguaje/llm.py` | Creado con configuración, `ChatOllama`, modelo falso, reintentos y `health_check` |
| `--print-config` | Devuelve la configuración efectiva, sin secretos |
| `--check` | Devuelve `0` con Ollama y `llama3.1:8b` disponibles; `2` con mensaje accionable si falta el servidor o el modelo |
| Invocación real | LangChain respondió `OK` en 7,75 s |
| Pruebas | 185 recolectadas; 184 pasan y 1 se omite por defecto (la integración real pasa con `OLLAMA_RUN_INTEGRATION=1`) |
| Ruff | Limpio |
| CI | Verde |
| Decisión | `docs/decisions/0006-ollama-llm.md` |

**Validación real**: Ollama `0.40.5` está instalado, el servidor responde en `127.0.0.1:11434`, el modelo
`llama3.1:8b` está descargado (4,9 GB), `--check` devuelve `0` y la prueba de integración real pasa.
