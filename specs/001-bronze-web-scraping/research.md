# Phase 0 Research: Capa Bronce de Recolección Web para el RAG de Manuelita

**Feature**: `001-bronze-web-scraping` | **Date**: 2026-10-27 | **Plan**: [plan.md](./plan.md)

All unknowns from the Technical Context are resolved below. No unresolved clarification remains.

## R1. Motor de adquisición: scrapling con extras de fetchers

- **Decision**: Usar `scrapling[fetchers]` 0.5 como motor principal. `AsyncFetcher` para HTTP concurrente
  con impersonación TLS/navegador; `StealthyFetcher` solo como adaptador opcional por fuente cuando el HTML
  útil requiera JavaScript. Instalar el extra en `pyproject.toml` y fijar la versión con `uv.lock`.
- **Rationale**: Cumple el requisito del usuario, cubre sitios estáticos y dinámicos con una sola API,
  incluye `curl_cffi`, `protego` y utilidades de fingerprinting, y evita mantener dos stacks de scraping.
- **Alternatives considered**: `requests`/`httpx` + BeautifulSoup (sin manejo de JS ni fingerprinting);
  Playwright puro (más código y más recursos); APIs comerciales de scraping (costo y dependencia externa).
- **Risk**: verify that `scrapling[fetchers]` resolves and installs on Python 3.14 with `uv lock`; if a browser
  dependency is unavailable, fall back to the HTTP-only adapter (`curl_cffi`) and defer JS sources.

## R2. Estrategia de descubrimiento

- **Decision**: Descubrimiento en dos capas: (1) `sitemap.xml`/`robots.txt` y enlaces de navegación del
  dominio oficial; (2) BFS acotado por profundidad (máximo 3) y por número de páginas, con canonicalización
  previa. Para fuentes externas, partir de listados, paginación y búsquedas declaradas en configuración.
- **Rationale**: El sitemap maximiza cobertura con mínimo costo y es la vía esperada por el sitio; el BFS
  captura contenido no listado. Los límites evitan crawls infinitos y consumo excesivo del cupo.
- **Alternatives considered**: Solo BFS (menor cobertura y más solicitudes); solo sitemap (pierde contenido
  dinámico); motores de búsqueda externos (dependencia y resultados no reproducibles).

## R3. Almacenamiento: archivos crudos + SQLite + JSONL

- **Decision**: Guardar los bytes crudos en el sistema de archivos
  (`data/bronze/raw/<source>/<campaign>/<sha256>.<ext>`), la metadata y el estado en SQLite WAL
  (`data/bronze/_meta/bronze.sqlite3`), y exportar manifiestos JSONL por campaña.
- **Rationale**: Los archivos preservan el original sin overhead y permiten verificación byte a byte;
  SQLite ofrece consultas transaccionales sin servidor; JSONL es portable y legible para auditoría.
- **Alternatives considered**: Solo archivos + CSV (consultas frágiles); Parquet desde el inicio (requiere
  `pyarrow`, pesado y prematuro para bronce); base documental (servicio adicional innecesario); BLOBs en
  SQLite (dificulta acceso directo y respaldo).

## R4. Contrato de metadata por artefacto

- **Decision**: Cada registro incluye los campos de FR-003 más `source_id`, `authority`, `campaign_id`,
  `content_hash`, `text_hash`, `storage_path`, `http_status`, `retrieved_at` (UTC ISO 8601), `language`
  (`es`, `en`, `und`) y `version`. Validación con un esquema JSON versionado (`contracts/artifact.schema.json`).
- **Rationale**: Es el mínimo verificable para auditoría, cobertura y reconstrucción; separar `content_hash`
  de `text_hash` permite deduplicar bytes y detectar cambios de contenido real.
- **Alternatives considered**: Metadata embebida solo en el nombre del archivo (insuficiente para consultas);
  esquema libre (rompe SC-002 y SC-006).

## R5. Deduplicación y versionado

- **Decision**: `content_hash` = SHA-256 de los bytes; `text_hash` = SHA-256 del texto visible normalizado
  (HTML) o del contenido del documento cuando sea extraíble. Un mismo `content_hash` se almacena una sola
  vez. Se crea una nueva versión solo cuando cambia `text_hash`; las URL alternas se registran como alias.
- **Rationale**: Evita duplicados exactos y evita versiones espurias por nonces, publicidad o sellos de tiempo.
  Mantiene el histórico exigido por FR-020 sin inflar el cupo.
- **Alternatives considered**: Versionar por `content_hash` (genera ruido en páginas dinámicas); no versionar
  (pierde trazabilidad); deduplicar por URL canónica (no detecta espejos).

## R6. Idempotencia y reanudación

- **Decision**: Máquina de estados por objetivo (`discovered → allowed|excluded → fetching → stored|deduped|
  failed|deferred`) persistida en SQLite. Escritura atómica (`temporal + os.replace`) y checkpoint por lote.
  Reanudar = seleccionar objetivos en estado no terminal e incrementar el contador de intentos.
- **Rationale**: Cumple FR-012/SC-005, tolera interrupciones y permite auditar por qué una URL no se procesó.
- **Alternatives considered**: Re-crawl completo desde cero (duplica trabajo y riesgo de bloqueo); archivo de
  checkpoint plano (sin consultas ni transacciones).

## R7. Guardia de 10 GB

- **Decision**: Contar bytes reales de `data/bronze/` antes de cada escritura. Reservar el tamaño declarado
  (`Content-Length`) cuando exista, transmitir en streaming con contador y abortar si la proyección supera el
  tope. Umbral de alerta al 90% y priorización por categoría: P0 identidad y sitio oficial, P1 oferta y datos
  duros, P2 noticias y blogs, P3 redes sociales y material pesado. Lo diferido se registra con causa
  `storage_cap`.
- **Rationale**: Garantiza el límite duro de FR-010/SC-003 incluso con archivos grandes o respuestas sin
  `Content-Length`.
- **Alternatives considered**: Verificar solo al final (riesgo de exceder); confiar en cuotas de disco
  (no distingue etapas ni prioriza).

## R8. Políticas por fuente, robots y tasa

- **Decision**: Evaluar `robots.txt` con `urllib.robotparser` más parseo explícito de `Crawl-delay`, cachear
  por host y registrar la decisión. Aplicar allowlist de dominios, `User-Agent` identificable, concurrencia
  máxima por host (2) y global (8), intervalo mínimo entre solicitudes y respeto de `Retry-After`.
  Rechazar esquemas distintos de HTTP(S) y direcciones privadas (protección SSRF).
- **Rationale**: Cumple FR-008/FR-009 y SC-007; reduce bloqueos y riesgos legales.
- **Alternatives considered**: `protego` (ya incluido, pero la API estándar basta); sin control de tasa
  (bloqueos y sobrecarga); rotación de proxies (elusión, contraria a la ética del proyecto).

## R9. YouTube: metadatos y subtítulos sin medios

- **Decision**: `yt-dlp` en modo `--skip-download --write-subs --write-auto-subs --sub-langs "es.*,en.*"
  --sub-format vtt`, más `--dump-json` para metadatos. Fallback a `oEmbed` cuando el video no exponga
  subtítulos. Guardar VTT/JSON y metadatos; nunca el archivo de video o audio.
- **Rationale**: Es la vía más estable para subtítulos sin descargar medios y respeta FR-015.
- **Alternatives considered**: YouTube Data API (requiere clave y cuota); endpoint `timedtext` directo
  (frágil y no documentado); transcripción con modelos de voz (fuera de alcance y costo alto).

## R10. Redes sociales y contenido de terceros

- **Decision**: Capturar solo páginas públicas sin sesión mediante `AsyncFetcher`/`StealthyFetcher`, usando
  metadatos Open Graph y HTML visible. Matriz de plataformas: Facebook e Instagram públicos (mejor esfuerzo,
  sin login), YouTube (vía R9), X/Twitter y LinkedIn excluidos por requerir sesión o prohibir automatización.
  Toda exclusión se documenta como vacío de cobertura.
- **Rationale**: Cumple FR-009/FR-016 y el supuesto de contenido público; evita eludir controles de acceso.
- **Alternatives considered**: APIs oficiales (requieren credenciales y permisos); scraping autenticado
  (viola términos y la constitución); compra de datasets (fuera de alcance).

## R11. Detección de idioma

- **Decision**: Usar el atributo `lang` del HTML cuando exista y, en su ausencia, un heurístico de palabras
  vacías español/inglés; valor `und` si no hay evidencia suficiente. Registrar el método usado.
- **Rationale**: Evita una dependencia pesada para una decisión binaria y es reproducible.
- **Alternatives considered**: `lingua-language-detector` (preciso pero pesado); `langdetect` (poco mantenido
  y no determinista por semillas); modelos de NLP (innecesario en bronce).

## R12. Configuración declarativa

- **Decision**: TOML leído con `tomllib` (stdlib): `config/sources.toml`, `config/coverage-items.toml` y
  `config/exclusions.toml`. Validar al inicio, calcular `config_hash` SHA-256 y persistirlo en la campaña.
- **Rationale**: Formato legible, con comentarios, sin dependencias y compatible con FR-018.
- **Alternatives considered**: YAML (dependencia adicional); JSON (sin comentarios); variables de entorno
  dispersas (no reproducible).

## R13. Observabilidad y reportes

- **Decision**: `logging` estándar en formato JSONL hacia `data/bronze/_meta/logs/`, con identificador de
  campaña y de objetivo. Reporte de campaña y de cobertura en JSON y Markdown bajo
  `data/bronze/reports/<campaign>/`, con esquemas en `contracts/`.
- **Rationale**: Cumple FR-017/SC-009 y permite revisar sin herramientas propietarias.
- **Alternatives considered**: `loguru`/`structlog` (dependencia innecesaria); solo consola (no auditable).

## R14. Pruebas sin red

- **Decision**: `pytest` con tres capas: unitarias (canonicalización, hashes, guardia de cupo, cobertura),
  integración contra un servidor HTTP local con fixtures estáticas (HTML, PDF, robots, sitemap) y contrato
  de salidas JSON contra los esquemas. `ruff` para lint y formato. Cobertura mínima objetivo: 80% en módulos
  de dominio.
- **Rationale**: Cumple la puerta de calidad de la constitución y evita dependencia de sitios externos.
- **Alternatives considered**: Pruebas contra sitios reales (frágiles y no éticas en CI); `pytest-asyncio`
  (evitable usando `asyncio.run` en las pruebas de integración).

## R15. Flujo Git y GitHub

- **Decision**: Rama `001-bronze-web-scraping`; commits atómicos en Conventional Commits
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`); `.gitignore` para `.venv/`, `data/`, `.env`, cachés;
  integrar por Pull Request con verificación de lint, pruebas y Constitution Check. No se versiona ningún
  artefacto de datos ni credencial.
- **Rationale**: Cumple la instrucción de manejo profesional y la puerta de revisión constitucional.
- **Alternatives considered**: Commits directos a `main` (sin trazabilidad); versionar datos (excede Git y
  rompe el límite de 10 MB del repositorio).

## R16. Preservación de formatos y extracción diferida

- **Decision**: Guardar HTML, PDF, XML, JSON y texto tal como se reciben, con detección de tipo por
  `Content-Type` y firma de bytes. La extracción de texto enriquecido, tablas y OCR pertenece a la capa
  plateada; en bronce solo se calcula `text_hash` cuando sea viable sin alterar el original.
- **Rationale**: Mantiene la inmutabilidad de FR-004 y separa responsabilidades entre capas medallion.
- **Alternatives considered**: Convertir todo a Markdown en bronce (pierde el original); OCR inmediato
  (costo y ruido prematuros).

## R17. Consulta del catálogo

- **Decision**: Interfaz CLI (`catalog list`, `catalog show`, `catalog export`) sobre vistas SQLite;
  exportación JSONL/CSV. Sin servidor ni API HTTP en esta fase.
- **Rationale**: Satisface FR-006 con mínima infraestructura y facilita la auditoría manual.
- **Alternatives considered**: API REST (infraestructura no justificada); notebooks ad hoc (no reproducible).

## R18. Seguridad y secretos

- **Decision**: Sin credenciales en el repositorio; configuración opcional por variables de entorno. Lista
  de dominios permitidos, bloqueo de IP privadas y de esquemas no HTTP(S), límite de tamaño por artefacto y
  validación de rutas de escritura dentro de `data/bronze/`.
- **Rationale**: Evita SSRF, exfiltración y escrituras fuera del área controlada; cumple las restricciones
  técnicas de la constitución.
- **Alternatives considered**: Confiar en la entrada del usuario (riesgo de SSRF); descargar sin límite de
  tamaño (riesgo de agotar el cupo y el disco).

## Resolved Unknowns Summary

| Topic | Resolution |
|-------|------------|
| Extraction engine | scrapling `[fetchers]` 0.5 + optional StealthyFetcher |
| Discovery | Sitemap first, bounded BFS fallback |
| Persistence | Raw files + SQLite WAL + JSONL manifests |
| Dedup/versioning | SHA-256 content hash + normalized text hash |
| Resume | Per-target state machine with atomic writes |
| Storage cap | Streaming counter, 90% alert, priority tiers |
| YouTube | yt-dlp subtitles/metadata, no media |
| Social | Public pages only; login-walled excluded |
| Language | HTML `lang` + stopword heuristic |
| Config | TOML via stdlib `tomllib` |
| Testing | pytest with local fixture server, no network |
