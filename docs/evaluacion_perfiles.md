# Evaluación de los perfiles de la plataforma (spec 025, SC-003)

**Ejecución**: `profiles-real-20261124T190428Z` · **Modo**: real · **Fecha**: 2026-11-24T19:04:28+00:00 · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent profiles-eval --mode real --write-docs`

- Perfil correcto (detectado o aplicado): **19/20** (95%; meta ≥ 90 %).
- Herramientas usadas dentro del perfil: **20/20** (meta 100 %).
- Errores: 0. Veredicto: ✅ cumple.

| Caso | Esperado | Obtenido | Herramientas |
|---|---|---|---|
| r01 ✅ | visitante | visitante | summarize_topic, search_documents |
| r02 ✅ | visitante | visitante | search_documents, query_structured |
| r03 ✅ | visitante | visitante | search_documents, summarize_topic, search_documents |
| r04 ✅ | visitante | visitante | search_documents, summarize_topic |
| r05 ✅ | cliente | cliente | list_company_entities |
| r06 ✅ | cliente | cliente | search_documents, search_documents, get_official_channels |
| r07 ✅ | cliente | cliente | list_company_entities, search_documents |
| r08 ✅ | cliente | cliente | — |
| r09 ✅ | proveedor | proveedor | search_documents, search_documents, get_official_channels |
| r10 ✅ | proveedor | proveedor | search_documents, search_documents, get_official_channels |
| r11 ✅ | proveedor | proveedor | search_documents, sustainability_lookup |
| r12 ✅ | proveedor | proveedor | — |
| r13 ❌ | colaborador | visitante | get_official_channels, get_official_channels |
| r14 ✅ | colaborador | colaborador | — |
| r15 ✅ | colaborador | colaborador | search_documents, search_documents |
| r16 ✅ | colaborador | colaborador | search_documents |
| r17 ✅ | planificador | planificador | get_commitments, get_plant_state, search_operating_procedures, optimize_production_plan |
| r18 ✅ | planificador | planificador | get_plant_state, get_commitments |
| r19 ✅ | planificador | planificador | get_commitments, get_plant_state |
| r20 ✅ | planificador | planificador | get_plant_state, get_commitments, simulate_production_scenario, optimize_production_plan |
