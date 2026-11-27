# Evaluación del catálogo de herramientas (spec 024, ítems 1.1 y 1.2)

**Ejecución**: `tools-real-20261127T161933Z` · **Modo**: real · **Fecha**: 2026-11-27T16:19:33+00:00 · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent evaluate --tools --mode real`

- Exactitud de herramienta: **86.1%** sobre 43 consultas (meta ≥ 90 %).
- Búsquedas en 10 consultas triviales: **0** (meta 0).
- Latencia p50 / p90: 2603 / 9795 ms · errores: 0.
- Veredicto: ❌ no cumple.

| Herramienta esperada | Casos | Aciertos |
|---|---:|---:|
| `aggregate_series` | 2 | 2 |
| `calculate` | 3 | 3 |
| `compare_indicator` | 2 | 2 |
| `export_conversation` | 2 | 2 |
| `faq_lookup` | 2 | 1 |
| `forget_memory` | 2 | 2 |
| `get_fragment` | 2 | 2 |
| `get_my_profile` | 2 | 0 |
| `get_official_channels` | 3 | 3 |
| `latest_news` | 2 | 1 |
| `list_business_units` | 2 | 1 |
| `list_company_entities` | 2 | 2 |
| `list_indicators` | 2 | 2 |
| `query_structured` | 2 | 2 |
| `request_human_contact` | 2 | 1 |
| `save_preference` | 2 | 2 |
| `save_profile` | 2 | 2 |
| `search_documents` | 2 | 2 |
| `summarize_topic` | 2 | 2 |
| `sustainability_lookup` | 3 | 3 |

## Fallos

- `t15` esperaba `list_business_units`; ruta `documental`, llamó ['search_documents', 'query_structured', 'search_documents']
- `t21` esperaba `faq_lookup`; ruta `documental`, llamó ['search_documents', 'summarize_topic']
- `t25` esperaba `latest_news`; ruta `clarify`, llamó —
- `t32` esperaba `get_my_profile`; ruta `out_of_scope`, llamó —
- `t33` esperaba `get_my_profile`; ruta `out_of_scope`, llamó —
- `t42` esperaba `request_human_contact`; ruta `out_of_scope`, llamó —

## Nota de variabilidad (spec 029, 2026-11-27)

Esta corrida oficial (86,1 %) quedó por debajo de la meta por t15 y t25, que en la corrida anterior (spec 028,
90,7 %) acertaron. Se repitió la evaluación completa en modo real con el mismo código (`tools-real-20261127T162754Z`,
reporte fuera del repositorio): **90,7 % (39/43)**, con t15 y t25 correctas y los mismos cuatro fallos de siempre
(t21, t32, t33, t42; t32, t33 y t42 fallan también en `main`). La diferencia es variación del modelo, no un efecto de
los cambios de la spec 029 (idioma del turno, aviso de datos sensibles y formato de fuentes).
