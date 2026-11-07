# Quickstart — Validación del RAG (Módulo 2)

**Feature**: `013-semantic-rag-chatbot`
**Rama**: `013-semantic-rag-chatbot` (no `main`)

Guía para validar de extremo a extremo que el chatbot responde con recuperación semántica. No repite el
contrato: ver [contracts/retrieval-trace.md](./contracts/retrieval-trace.md) y
[data-model.md](./data-model.md).

---

## 0. Prerrequisitos

```powershell
git switch 013-semantic-rag-chatbot
uv sync --all-extras
cd web; npm ci; cd ..
```

- `.env` con `DEEPSEEK_API_KEY` (solo para el modo `real`).
- `data/gold/knowledge_units.jsonl` presente (15.211 unidades).
- Espacio libre ≥ 1 GB (modelo ONNX ~120 MB + índice ~23 MB).

---

## 1. Construir el índice

```powershell
uv run python -m proyecto_modelos_lenguaje.rag index build
```

**Esperado**: descarga única del modelo, mensaje con ruta, modelo, dimensión `384` y `count=15211`.
Tarda unos minutos en CPU; se ejecuta una sola vez.

```powershell
uv run python -m proyecto_modelos_lenguaje.rag index verify
```

**Esperado**: `OK` con `count`, `dimension=384`, `gold_sha256` y perfil coincidentes.

**Comprobaciones adicionales**:

```powershell
git status --short          # data/module2/ no debe aparecer (ignorado)
git diff --stat data/gold   # sin cambios: el índice no toca el origen
```

---

## 2. Suite sin red

```powershell
uv run pytest tests/unit/rag tests/contract tests/integration -q
```

**Esperado**: todo en verde, sin descargas ni llamadas de red. Usa `HashEmbedder` y el índice de prueba
en `tests/fixtures/rag/`.

---

## 3. Probar la recuperación desde la CLI (sin LLM)

```powershell
uv run python -m proyecto_modelos_lenguaje.rag search "¿cómo cuida Manuelita el agua?"
```

**Esperado**: lista ordenada de fragmentos con `score`, `origin` (`semantic`/`lexical`/`both`) y
`unit_id`.

Casos de validación:

| Consulta | Qué debe pasar |
|----------|----------------|
| «¿cómo cuida Manuelita el agua?» | Fragmentos de sostenibilidad/agua en el top-3 |
| «¿cuántas hectáreas de caña tiene?» | Cifras exactas: la vía léxica debe aportar el fragmento |
| «manejo del recurso hídrico» (sinónimo de agua) | Recuperación semántica sin coincidencia literal |
| «receta de arepas» | Sin fragmentos sobre el umbral → `mode="none"` |

---

## 4. Preguntar por la API

```powershell
uv run uvicorn proyecto_modelos_lenguaje.api:app --host 127.0.0.1 --port 8000
```

```powershell
curl -s http://127.0.0.1:8000/api/health
curl -s -X POST http://127.0.0.1:8000/api/ask -H "Content-Type: application/json" -d '{\"question\":\"¿Qué hace Manuelita en el tema del agua?\",\"mode\":\"real\"}'
```

**Esperado en la respuesta**:

- `status` en `ok` o `fallback`; nunca `error` por falta de índice.
- `citations` con al menos una unidad cuando `status="ok"`.
- `retrieval.fragments` con `score`, `origin` y `status`.
- `retrieval.mode` en `hybrid`, `lexical`, `semantic` o `none`.

---

## 5. Ver los fragmentos en la interfaz

```powershell
cd web; npm run build; cd ..
uv run uvicorn proyecto_modelos_lenguaje.api:app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000`, hacer una pregunta y verificar:

1. Insignia con el modo de recuperación.
2. Fragmentos usados visibles con título, fuente y puntuación.
3. Descartados en el desplegable, con su motivo.

---

## 6. Modo demostración sin red

```powershell
# desconectar la red (o bloquear salida) y luego:
curl -s -X POST http://127.0.0.1:8000/api/ask -H "Content-Type: application/json" -d '{\"question\":\"¿Qué es Manuelita?\",\"mode\":\"demo\"}'
```

**Esperado**: respuesta del modelo guionizado, `retrieval.fragments` presentes desde el índice de
prueba y distintivo de demo en la interfaz. Sin llamadas externas.

---

## 7. Evaluar y comparar

```powershell
uv run python -m proyecto_modelos_lenguaje.rag evaluate --questions tests/fixtures/rag/eval_questions.jsonl --out docs/evaluacion_modulo2.md
```

**Esperado**: tabla con Recall@1/3/5/8 y MRR para `semantic`, `lexical` y `hybrid`, y un veredicto
explícito.

**Criterio de aceptación**:

- `hybrid.recall@5 >= lexical.recall@5`
- `hybrid.mrr >= lexical.mrr`
- `citation_coverage == 1.0` (toda respuesta `ok` tiene cita)
- Latencia extremo a extremo ≤ 1.2 × la del Módulo 1

Si el híbrido no supera la línea base, **no se hace merge**: se ajusta el umbral y los pesos, se
documenta el análisis de errores y se repite.

---

## 8. Índice desactualizado y errores controlados

| Escenario | Cómo provocarlo | Esperado |
|-----------|-----------------|----------|
| Índice ausente | borrar `data/module2/index/` | `semantic_available=false`, `mode="lexical"`, aviso; la app no falla |
| Perfil distinto | cambiar `dimension` en `config/retrieval.toml` | `index verify` sale con `5` y mensaje accionable |
| Corpus cambiado | agregar una unidad a oro (en una copia) | `index verify` avisa `6` (desactualizado) y sugiere `rebuild` |
| Modelo caído | quitar la red en modo `real` | `status="error"` con código, `retrieval` conservado |
| Pregunta fuera de corpus | «receta de arepas» | `status="fallback"` explícito, sin inventar |

---

## 9. Cierre

```powershell
uv run ruff check .
uv run pytest -q
make check
git status --short   # sin data/module2, sin .env, sin claves
```

Luego: PR a `main` para revisión del propietario. **No se hace merge desde este entorno.**
