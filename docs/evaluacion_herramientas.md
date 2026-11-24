# Evaluación del catálogo de herramientas (spec 024, ítems 1.1 y 1.2)

**Ejecución**: `tools-real-20261123T220245Z` · **Modo**: real · **Fecha**: 2026-11-23T22:02:45+00:00 · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent evaluate --tools --mode real`

- Exactitud de herramienta: **88.4%** sobre 43 consultas (meta ≥ 90 %).
- Búsquedas en 10 consultas triviales: **0** (meta 0).
- Latencia p50 / p90: 3723 / 9230 ms · errores: 0.
- Veredicto: ❌ no cumple.

| Herramienta esperada | Casos | Aciertos |
|---|---:|---:|
| `aggregate_series` | 2 | 2 |
| `calculate` | 3 | 3 |
| `compare_indicator` | 2 | 2 |
| `export_conversation` | 2 | 2 |
| `faq_lookup` | 2 | 0 |
| `forget_memory` | 2 | 2 |
| `get_fragment` | 2 | 2 |
| `get_my_profile` | 2 | 0 |
| `get_official_channels` | 3 | 3 |
| `latest_news` | 2 | 2 |
| `list_business_units` | 2 | 2 |
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

- `t21` esperaba `faq_lookup`; ruta `documental`, llamó ['search_documents', 'summarize_topic', 'search_documents']
- `t22` esperaba `faq_lookup`; ruta `documental`, llamó ['summarize_topic', 'search_documents']
- `t32` esperaba `get_my_profile`; ruta `out_of_scope`, llamó —
- `t33` esperaba `get_my_profile`; ruta `out_of_scope`, llamó —
- `t42` esperaba `request_human_contact`; ruta `out_of_scope`, llamó —

## Lectura (2026-11-23)

Dos corridas reales con DeepSeek (`deepseek-flash`) sobre la misma batería, fijada antes de evaluar:

| Corrida | Cambio | Exactitud | Búsquedas en triviales | p50 / p90 |
|---|---|---:|---:|---|
| 1 | `agent.md` 1.6, sin reglas nuevas | 72,1 % (31/43) | 0 | 3,9 / 9,1 s |
| 2 | `agent.md` 1.7 + reglas de señal inequívoca en el enrutador (`tool_cue_decision`) | **88,4 % (38/43)** | **0** | 3,7 / 9,2 s |

En la corrida 1 la mayoría de los fallos no llegaban al agente: el enrutador mandaba «compara 2019 con 2022»,
«cuánto es 1.250 por 3,5» o «muéstrame la unidad unit_…» a la ruta directa o fuera de alcance. Las reglas nuevas
(identificador de unidad, aritmética, comparación entre años y canal oficial de contacto) los llevan al agente
sin llamar al modelo.

Los cinco fallos restantes de la corrida 2 (la meta era ≥ 90 %):

- `faq_lookup` (2): el agente prefirió `search_documents` y `summarize_topic`. La respuesta salió citada, pero
  con otra herramienta.
- `get_my_profile` (2): «¿qué datos míos tienes guardados?» y «¿recuerdas en qué ciudad vivo?» no llegan al
  agente. Las atiende el flujo de memoria y privacidad de las specs 014 y 018, que responde desde el Store sin
  herramienta.
- `request_human_contact` (1): pedir que una persona contacte es una «solicitud inalcanzable» de la spec 019 y
  se responde con los canales oficiales. La herramienta solo aparece si el visitante insiste en dejar sus datos.

No se tocaron esos flujos porque ya están evaluados (`docs/evaluacion_conducta.md`, `docs/evaluacion_atencion.md`)
y cambiarlos sin medirlos de nuevo sería un riesgo a cinco días de la entrega. Queda pendiente decidir con el equipo
si el perfil propio y el contacto humano deben pasar por el agente para mostrarse en la demo.
