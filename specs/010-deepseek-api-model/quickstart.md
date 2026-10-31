# Quickstart — modelo DeepSeek por API

**Feature**: `010-deepseek-api-model`
**Fecha**: 2026-10-31

Guía de validación del cambio de proveedor. Ningún paso escribe en `data/` ni en el repositorio.

## 1. Requisitos

```bash
uv sync
uv run ruff check .
uv run pytest -q
```

- Cuenta con acceso al proveedor y su clave.
- `data/gold/` materializado (`git lfs pull`).

## 2. Configurar el secreto

```bash
# .env (ignorado por Git)
DEEPSEEK_API_KEY=tu_clave_real
```

- No copies la clave a `config/llm.toml` ni a ningún archivo versionado.
- `.env.example` solo documenta el nombre de la variable.

Resultado esperado: `git status` no muestra `.env`.

## 3. Verificar el proveedor

```bash
uv run python -m proyecto_modelos_lenguaje.llm --print-config
uv run python -m proyecto_modelos_lenguaje.llm --check
```

Resultado esperado:

- `--print-config` muestra `provider: deepseek`, el modelo, la URL y `api_key_present: true`.
- La salida **no** contiene la clave.
- `--check` devuelve `ok: true` y una latencia; código de salida `0`.

Casos de fallo esperados (código `2`):

| Condición | Código | Mensaje |
|-----------|--------|---------|
| Sin `.env` | `config_missing_key` | «Define `DEEPSEEK_API_KEY`…» |
| Clave incorrecta | `auth_failed` | «La clave no es válida o fue revocada…» |
| Modelo inexistente | `model_unavailable` | «El modelo configurado no está disponible…» |

## 4. Ejecutar las tres tareas

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa \
  --question "¿Qué productos ofrece Manuelita?" --json
uv run python -m proyecto_modelos_lenguaje.tasks summary --json
uv run python -m proyecto_modelos_lenguaje.tasks faq --limit 10 --json
```

Resultado esperado:

- Las tres respuestas citan unidades y declaran el modelo configurado.
- `status=ok` con citas, o `status=fallback` sin inventar.
- Cada resultado incluye `model`, `input_tokens`, `output_tokens` y `latency_seconds`.

## 5. App

```bash
uv run streamlit run app.py
```

Resultado esperado:

- El chip de estado indica el proveedor disponible.
- El panel muestra modelo, tokens y costo estimado de la sesión.
- Con `PML_DEMO=1`, el chip muestra «Modo demo» y no hay llamadas remotas.

## 6. Modo demostración sin red

1. Desconectar la red o bloquear el dominio del proveedor.
2. Activar el modo demostración (`PML_DEMO=1` o el interruptor de la barra lateral).
3. Recorrer las cuatro vistas.

Resultado esperado: todas responden con el modelo falso, sin intentos de red y con el distintivo visible.

## 7. Errores simulados

```bash
# Sin clave
set DEEPSEEK_API_KEY=
uv run python -m proyecto_modelos_lenguaje.llm --check
```

Resultado esperado: código `2`, mensaje accionable y ninguna traza.

Con transporte simulado (suite):

```bash
uv run pytest tests/integration/test_llm_api.py -q
```

Cubre: 401, 403, 404, 429, 500, timeout, respuesta vacía y JSON inválido.

## 8. Costo y tokens

1. Ejecutar una pregunta.
2. Revisar el panel lateral.

Resultado esperado: llamadas, tokens de entrada y salida, y costo estimado. Si la tarifa está en cero, el
panel indica «costo no configurado» en lugar de mostrar `0.00`.

## 9. Sin filtración de la clave

```bash
uv run pytest tests/unit/test_llm.py -q -k secret
```

Resultado esperado: la prueba recorre `config/llm.toml`, las salidas de `--print-config`, los resultados de
tareas y la descarga de sesión, y falla si aparece la clave.

## 10. Criterios de aceptación

| Escenario | Criterio |
|-----------|----------|
| Proveedor disponible | Las tres tareas responden y citan |
| Sin clave | Error `config_missing_key` con instrucción |
| Clave inválida | Error `auth_failed`, sin reintentos |
| Cuota agotada | Error `rate_limited` con alternativa demo |
| Timeout | Error controlado y reintento disponible |
| Sin red | Modo demostración funciona en las cuatro vistas |
| Costo | Panel muestra tokens y costo o «no configurado» |
| Seguridad | 0 apariciones de la clave en artefactos |
| Corpus | Sin cambios en `data/` ni en las capas medallion |
