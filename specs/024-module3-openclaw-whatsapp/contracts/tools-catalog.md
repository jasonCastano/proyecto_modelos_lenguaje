# Contrato: catálogo de 20 herramientas (ítem 1.1)

Fuente única: `src/proyecto_modelos_lenguaje/agent/catalog.py`. De ella salen las herramientas del agente, el servidor
MCP (solo lectura), `GET /api/tools`, `agent tools --json` y `docs/herramientas.md`.

Reglas comunes:

- Esquema Pydantic v2 con `extra="forbid"`; textos libres con `max_length`; años en `[2000, 2030]`; `top_k` en `[1, 10]`.
- Toda salida de lectura devuelve texto para el modelo **y** referencias citables (`[U#]` para unidades de oro, `[F#]`
  para filas de series/hechos), validadas por el mismo mecanismo de citas del Módulo 2.
- Sin evidencia → la herramienta lo dice (`"sin resultados"`); nunca inventa.
- Ninguna herramienta escribe en `data/` ni en el repositorio. Las de escritura solo tocan el Store del usuario o el
  registro de contactos en `$MANUELITA_STATE_DIR`, y solo tras aprobación.
- Errores de validación → `ToolArgsError` con mensaje en español; el agente reintenta o pide aclaración.

## Lectura (15; expuestas también por MCP)

| # | Nombre | Estado | Argumentos (tipos y límites) | Fuente | Rutas |
|---|---|---|---|---|---|
| 1 | `search_documents` | existe | `query: str(3–300)`, `top_k: int(1–10)=5`, `topic: str \| None` | Qdrant híbrida (`gold/knowledge_units`) | documental, mixed |
| 2 | `query_structured` | existe | según `QueryStructuredArgs` (conteos y hechos por tipo de entidad) | SQLite estructurada del oro | structured, mixed |
| 3 | `aggregate_series` | existe | `metric`, `operation: sum\|mean\|max\|min\|change`, `year_from`, `year_to`, `business \| None` | `curated/series_anuales.csv` | structured, mixed |
| 4 | `list_indicators` | nueva | `business: str \| None` | `series_anuales.csv` | structured |
| 5 | `compare_indicator` | nueva | `metric: str`, `year_a: int`, `year_b: int` (distintos) | `series_anuales.csv` (`Decimal`) | structured, mixed |
| 6 | `sustainability_lookup` | nueva | `theme: agua\|carbono\|energia\|residuos\|biodiversidad\|social`, `query: str(3–200) \| None`, `top_k(1–10)=5` | Qdrant con **filtro por payload** (`topic_id`/términos) | documental |
| 7 | `list_business_units` | nueva | `country: str \| None` | `gold/entities.jsonl` (subsidiary, company) + series | structured |
| 8 | `list_company_entities` | nueva | `kind: certification\|brand` | `gold/entities.jsonl` | structured |
| 9 | `get_official_channels` | nueva | `purpose: general\|empleo\|proveedores\|clientes\|prensa = general` | `config/official_channels.toml` + oro (contacto) | direct, documental |
| 10 | `faq_lookup` | nueva | `question: str(3–300)`, `top_k(1–5)=3` | `gold/faq_seeds.jsonl` (53) + evidencia | documental |
| 11 | `summarize_topic` | nueva | `topic_id: Literal[catalogos, certificaciones, clientes, empleo, finanzas, fundacion, general, identidad, noticias, precios, …]` | `gold/topics/*.md` (extractivo, con unidades) | documental |
| 12 | `latest_news` | nueva | `limit: int(1–5)=3`, `since_year: int \| None` | unidades con `published_at` del tema `noticias` | documental |
| 13 | `get_fragment` | nueva | `unit_id: str ^unit_[0-9a-f]{16}$` | `gold/knowledge_units.jsonl` (texto, URL, páginas) | documental |
| 14 | `calculate` | nueva | `expression: str(1–120)` con gramática `[0-9.,+\-*/()% ]` o `operation: percent_change\|ratio\|sum` + `values: list[Decimal](1–12)` | aritmética `Decimal` con AST seguro (sin `eval`) | structured, mixed, direct |
| 15 | `get_my_profile` | nueva | — (usa el `user_id` del turno) | `SqliteStore` (`profile`, `preferences`) | direct |

## Escritura (5; requieren aprobación humana; no se exponen por MCP)

| # | Nombre | Estado | Argumentos | Efecto tras aprobar |
|---|---|---|---|---|
| 16 | `save_profile` | existe | `SaveProfileArgs` (al menos un campo) | escribe `("users", id, "profile")` |
| 17 | `save_preference` | existe | `key: response_format\|topics_of_interest\|language`, `value` | escribe `("users", id, "preferences")` |
| 18 | `forget_memory` | existe | `scope: profile\|preferences\|all` | borra del Store |
| 19 | `export_conversation` | existe | `format: markdown`, `last_turns(1–20)` | devuelve el documento (en WhatsApp como texto) |
| 20 | `request_human_contact` | nueva | `topic: str(3–120)`, `preferred_channel: whatsapp\|email\|llamada`, `name: str(1–80) \| None` | registra la solicitud en `contacts.jsonl` (spec 019) con `user_id` seudónimo; responde con el canal oficial |

## Pruebas exigidas

- `tests/unit/agent/test_catalog.py`: ≥ 20 herramientas, nombres únicos, `requires_approval ⇔ write`, `mcp ⇒ read`,
  descripciones en rango, esquemas con `extra="forbid"`.
- Una prueba de contrato por herramienta (argumentos válidos → resultado con referencias; inválidos → error claro).
- `tests/fixtures/agent/tool_routing.jsonl`: ≥ 40 consultas (≥ 2 por herramienta) + 10 saludos/agradecimientos;
  `agent evaluate --tools` reporta exactitud de herramienta (SC-004 ≥ 90 %) y búsquedas en triviales (= 0).
