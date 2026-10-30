# Quickstart: Capa Plata (Silver)

**Feature**: `003-silver-medallion-layer`

Guía de validación end-to-end. No contiene la implementación; los detalles de datos están en
[data-model.md](./data-model.md) y los contratos en [contracts/](./contracts/).

## 1. Prerrequisitos

- Python 3.14 y `uv` instalados.
- Repositorio sincronizado y dependencias resueltas:

  ```bash
  uv sync --frozen
  ```

- Catálogo bronce disponible en `data/bronze/_meta/bronze.sqlite3` con al menos 500 artefactos activos.
  Si no existe, restaurar el corpus o ejecutar una campaña de bronce primero.
- Sin acceso a internet durante la validación (la etapa plata no lo requiere).

Comprobación rápida:

```bash
uv run python -c "from pathlib import Path; p=Path('data/bronze/_meta/bronze.sqlite3'); print(p.exists(), p.stat().st_size)"
```

## 2. Configuración

Revisar `config/silver.toml` (se crea en la implementación). Valores iniciales:

```toml
[chunking]
target_tokens = 800
max_tokens = 1000
min_tokens = 200
overlap_tokens = 120
chars_per_token = 3.5

[dedup]
near_threshold = 0.90
shingle_size = 5
num_perm = 128
bands = 16

[quality]
min_text_chars = 100
min_alpha_ratio = 0.50
table_line_ratio = 0.30
repeated_line_ratio = 0.30

[output]
root = "data/silver"
markdown = true
```

Cualquier cambio de configuración cambia el `config_hash` y obliga a regenerar.

## 3. Humo con diez artefactos

```bash
uv run pml silver build --run 2026-10-silver-00 --limit 10 --json
```

**Esperado**:

- Código de salida 0 o 1 (1 solo si algún artefacto falla y se reporta).
- `input_artifacts = 10`.
- Al menos 8 documentos y 1 fragmento por documento procesado.
- `data/silver/reports/2026-10-silver-00/quality.json` y `.md` creados.
- Ningún registro con `title`, `section_title`, `section_path`, `url` o `language` nulos.

## 4. Ejecución completa

```bash
uv run python scripts/build_silver.py --run 2026-10-silver-01 --json
```

o, equivalentemente:

```bash
uv run pml silver build --config config/silver.toml --run 2026-10-silver-01 --json
```

**Esperado**:

- `input_artifacts = 557` (o el total activo del corte).
- `processed + skipped + failed = 557`.
- `canonical_documents` cercano a `processed`; `alias_documents` recoge los duplicados.
- `chunks` en el orden de miles (estimación: 8.000–15.000).
- Duración ≤30 minutos en el equipo de referencia.
- Reporte con conteos por fuente, formato, estado, flags y cobertura de secciones.

## 5. Validar contratos

```bash
uv run pml silver verify --run 2026-10-silver-01 --sample 50 --seed 1 --json
```

**Esperado**:

- 0 fallos de esquema.
- 0 IDs duplicados.
- 0 secciones nulas.
- 0 chunks que crucen secciones.
- 50/50 fragmentos rastreados hasta una URL pública.
- Texto del fragmento contenido en el texto del documento en el rango declarado.

La validación de esquema también se ejecuta en las pruebas de contrato:

```bash
uv run pytest tests/contract/silver -q
```

## 6. Idempotencia

```bash
uv run pml silver build --run 2026-10-silver-01 --json
uv run pml silver build --run 2026-10-silver-02 --json
```

**Esperado**:

- La segunda ejecución no procesa de nuevo los artefactos sin cambios.
- `documents.jsonl` y `chunks.jsonl` conservan los mismos `doc_id`, `chunk_id`, textos y hashes.
- `duration_seconds` de la segunda ejecución es sustancialmente menor.
- `processing` no queda en estado colgado.

## 7. Cambio de un solo artefacto

1. Elegir un artefacto de prueba y registrar su `artifact_id` y `content_hash`.
2. Modificar su contenido en una copia de trabajo del bronce (nunca en el corpus real de producción) o usar un
   catálogo temporal de prueba.
3. Ejecutar de nuevo.

**Esperado**:

- Solo ese documento cambia de `doc_id` (si cambió el contenido) y se reprocesa.
- El resto conserva IDs y hashes.
- El reporte muestra el nuevo conteo y no duplica registros.

## 8. Deduplicación

Con un catálogo temporal que contenga:

- dos copias exactas del mismo texto,
- dos versiones casi idénticas,
- una versión oficial y una de tercero,
- dos idiomas distintos del mismo contenido,

**Esperado**:

- Un canónico por grupo exacto y cercano.
- Los alias apuntan al canónico y conservan su URL.
- La fuente oficial gana ante contenido equivalente.
- Las versiones en español e inglés no se colapsan.
- `duplicates_exact` y `duplicates_near` aparecen en el reporte.

## 9. Formatos

| Formato | Verificación mínima |
|---------|---------------------|
| HTML | El artículo principal aparece sin menús ni “Artículos relacionados”; los `h1`–`h6` generan secciones |
| PDF | Texto por página, `page_start/page_end` correctos y outline usado cuando existe |
| VTT | Sin cues duplicados; `time_start/time_end` presentes y crecientes |
| JSON | Registro estructurado legible, sin documento vacío |
| XML | Sitemap omitido con `navigation_artifact` |
| XLSX | Una sección por hoja, valores sin fórmulas |
| PDF escaneado | Omitido con `scanned_pdf`, sin documento vacío |

## 10. Integridad del bronce

Antes y después de la ejecución:

```bash
uv run python scripts/verify_bronze.py --campaign 2026-10-official-channels-3 --sample 50 --seed 1 --json
```

**Esperado**:

- Los hashes de los artefactos muestreados coinciden.
- `data/bronze/` no tiene archivos nuevos ni modificados por la etapa plata.
- Ningún registro de plata apunta a un artefacto en cuarentena o retirado.

## 11. Reporte de calidad

Abrir `data/silver/reports/2026-10-silver-01/quality.md` y comprobar:

- Conteos de entrada, procesados, omitidos y fallidos.
- Tokens de entrada y salida.
- Documentos y fragmentos.
- Duplicados exactos y cercanos.
- Cobertura de secciones (`with_title` / `without_title`).
- Distribución de flags (`scanned_pdf`, `no_section`, `low_text_density`, etc.).
- Duración y tamaño de salida.

## 12. Criterios de aceptación

| Criterio | Comprobación |
|----------|--------------|
| SC-001 | `processed + skipped + failed = input_artifacts` |
| SC-002 | ≥95% de artefactos con texto producen documento y fragmento; PDF escaneados marcados |
| SC-003 | `verify` no encuentra campos faltantes en 50 fragmentos |
| SC-004 | 0 `section_title` nulos o vacíos |
| SC-005 | ≥85% de secciones con título explícito |
| SC-006 | 100 fragmentos rastreados a URL en <2 minutos |
| SC-007 | Duplicados exactos colapsados; cercanos agrupados |
| SC-008 | Segunda ejecución sin cambios: 0 documentos/fragmentos nuevos |
| SC-009 | Cambio de un artefacto: solo ese documento se actualiza |
| SC-010 | ≥99% de fragmentos ≤ `max_tokens`; 0 cruces de sección |
| SC-011 | Duración ≤30 minutos en 4 núcleos / 8 GB |
| SC-012 | Reporte generado automáticamente |
| SC-013 | Hashes del bronce idénticos antes y después |
| SC-014 | Regeneración offline desde un clon limpio |

## 13. Problemas frecuentes

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `no_text` masivo en PDF | PDF escaneado o sin capa de texto | Revisar flags; no forzar OCR en esta etapa |
| `no_section` masivo en HTML | Extracto sin encabezados o bloqueo de `trafilatura` | Revisar muestra; ajustar reglas de respaldo |
| Chunks mayores al máximo | Proxy de tokens mal calibrado | Ajustar `chars_per_token` y regenerar |
| Duplicados no agrupados | Umbral demasiado alto | Bajar `near_threshold` con una muestra etiquetada |
| Segunda ejecución reprocesa todo | `config_hash` distinto o estado ausente | Verificar `config/silver.toml` y `_meta/state.jsonl` |
| Fallo de esquema | Campo nuevo no declarado | Actualizar contrato y versión de esquema |
