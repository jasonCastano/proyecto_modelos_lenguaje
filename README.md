# Proyecto Modelos de Lenguaje — RAG Ingenio Manuelita

Proyecto de curso para la asignatura **Técnicas Avanzadas de IA aplicadas en Modelos de Lenguaje**.
Maestría en Ciencia de Datos e Inteligencia Artificial — Universidad Autónoma de Occidente, Cali, Colombia.

El objetivo final es construir un RAG sobre información pública de **Ingenio Manuelita**. Este repositorio
implementa la **fase 1: capa bronce** de una arquitectura medallion: adquisición web, almacenamiento crudo
inmutable, catálogo de procedencia y reporte de cobertura.

## Estado actual

- ✅ Capa bronce de recolección web (sitio oficial, noticias, YouTube, redes públicas y datos abiertos).
- ✅ Catálogo SQLite con deduplicación, versionado y reanudación de campañas.
- ✅ Límite duro de 10 GB con priorización y alerta al 90%.
- ⏳ Capas plateada y dorada, indexación y generación (fases posteriores).

## Requisitos

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Conexión a internet para campañas reales (las pruebas no la necesitan)

## Instalación

```bash
uv sync --frozen
uv run ruff check .
uv run pytest
```

## Uso

```bash
# 1. Crear el catálogo y sembrar fuentes + los 24 requisitos de información
uv run pml init --config config/sources.toml --json

# 2. Simular descubrimiento y políticas sin descargar contenido
uv run pml campaign start --config config/sources.toml \
  --campaign smoke-001 --dry-run --max-targets 20 --json

# 3. Campaña real (reanudable)
uv run python scripts/run_campaign.py --config config/sources.toml --campaign 2026-10-baseline

# 4. Verificar integridad de una muestra
uv run python scripts/verify_bronze.py --campaign 2026-10-baseline --sample 20 --seed 42 --json

# 5. Reporte de cobertura de los 24 ítems
uv run python scripts/report_coverage.py --campaign 2026-10-baseline

# 6. Consultar el catálogo
uv run python scripts/query_catalog.py list --campaign 2026-10-baseline --category identity --limit 10 --json
```

Comandos disponibles: `pml init`, `pml campaign start|status`, `pml verify`, `pml report campaign|coverage`,
`pml coverage`, `pml catalog list|show|export`, `pml curate ...`.

### Depuración de relevancia

El corpus bronce puede contener páginas de portales genéricos que no tratan sobre Manuelita. El flujo de
curaduría clasifica cada artefacto y retira lo irrelevante con auditoría:

```bash
# Análisis en seco: no escribe nada
uv run pml curate analyze --relevance-config config/relevance.toml --json

# Aplicar evaluaciones y generar la cola de revisión
uv run pml curate analyze --relevance-config config/relevance.toml \
  --run 2026-10-curation-01 --apply --json

# Revisar ambiguos y aprobar
uv run pml curate review list --run 2026-10-curation-01 --json
uv run pml curate review decide --artifact 12345 --decision remove \
  --reviewer "tu nombre" --note "Mención incidental"
uv run pml curate approve --run 2026-10-curation-01 --reviewer "tu nombre"

# Mover lo irrelevante a cuarentena reversible (30 días)
uv run pml curate quarantine --run 2026-10-curation-01 --confirm

# Después del periodo de retención (o con aprobación explícita):
uv run pml curate purge --run 2026-10-curation-01 --expired --confirm
# Purga inmediata: --now --confirm

# Cobertura y catálogo solo con el corpus activo
uv run pml coverage --campaign 2026-10-baseline --active-only --json
uv run pml catalog export --campaign 2026-10-baseline --active-only \
  --format jsonl --output exports/curated.jsonl
```

Los artefactos retirados se mueven a `data/quarantine/<run_id>/` (no versionado) y conservan una fila de
auditoría con URL, hash, motivo y puntuación. El dominio oficial `manuelita.com` nunca se elimina.

## Estructura

```text
src/proyecto_modelos_lenguaje/   # lógica de dominio y CLI
scripts/                         # puntos de entrada operativos
config/                          # fuentes, exclusiones y 24 ítems requeridos
data/                            # capas medallion (no versionado)
specs/001-bronze-web-scraping/   # especificación, plan y contratos
tests/                           # unitarias, integración y contrato
```

### Datos generados

```text
data/bronze/
├── raw/<fuente>/<campaña>/<sha256>.<ext>   # bytes originales, inmutables
├── manifests/<campaña>.jsonl               # metadata de cada artefacto
├── reports/<campaña>/                      # campaña + cobertura (JSON/Markdown)
└── _meta/bronze.sqlite3                    # catálogo SQLite (WAL)
```

El límite de 10 GB se mide sobre todo `data/bronze/`. Los datos, credenciales y entornos virtuales están
excluidos de Git.

## Fuentes y ética

- Solo contenido público, sin autenticación ni elusión de controles.
- Se respetan `robots.txt`, `Crawl-delay`, términos de servicio y límites de tasa.
- Plataformas que exigen sesión (LinkedIn, X) quedan excluidas y se reportan como vacío de cobertura.
- De YouTube se guardan metadatos y subtítulos, nunca el video o audio.
- Cada artefacto conserva URL, fecha UTC, huella SHA-256, categoría e idioma.

## Pruebas

```bash
uv run pytest              # suite offline (servidor HTTP local)
uv run pytest -q tests/unit
uv run ruff check .
```

Las pruebas cubren canonicalización de URL, extracción, detección de idioma y MIME, guardia de
almacenamiento, políticas y robots, cobertura, contratos JSON y campañas de extremo a extremo
(incluida deduplicación y reanudación).

## Documentación

- Constitución del proyecto: `.specify/memory/constitution.md`
- Especificación: `specs/001-bronze-web-scraping/spec.md`
- Plan técnico: `specs/001-bronze-web-scraping/plan.md`
- Decisiones de investigación: `specs/001-bronze-web-scraping/research.md`
- Modelo de datos y contratos: `specs/001-bronze-web-scraping/data-model.md`, `contracts/`
- Guía de validación: `specs/001-bronze-web-scraping/quickstart.md`

## Licencia

Uso académico. El contenido recolectado pertenece a sus respectivas fuentes.
