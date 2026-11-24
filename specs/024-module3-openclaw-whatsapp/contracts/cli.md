# Contrato: comandos nuevos

Todos con `uv run`; salida legible por defecto y `--json` estable. Códigos: 0 OK · 1 error o meta no cumplida · 2 no
disponible (servicio o dependencia ausente).

| Comando | Qué hace | Salidas |
|---|---|---|
| `pml corpus rebuild [--from bronze\|silver] [--workdir DIR] [--in-place] [--scrape --campaign ID] [--limit N] [--json]` | Plata → oro → índice → Qdrant en un directorio de trabajo (por defecto `$TMP/pml-rebuild-<run>`); verifica procedencia. `--in-place` reescribe `data/` (solo con pedido explícito). | `<workdir>/manifest.json` (data-model §11) |
| `python -m proyecto_modelos_lenguaje.agent tools [--json] [--markdown PATH]` | Lista el catálogo (20) con esquemas; `--markdown` genera `docs/herramientas.md`. | stdout / archivo |
| `python -m proyecto_modelos_lenguaje.agent evaluate --tools [--fake] [--json-out PATH]` | Batería de enrutamiento de herramientas (≥ 40 + 10 triviales). | `docs/evaluacion_herramientas.{json,md}` |
| `python -m proyecto_modelos_lenguaje.agent shield --channel` | Ataques de inyección llegados por el canal (directos e indirectos). | `docs/evaluacion_blindaje_canal.{json,md}` |
| `python -m proyecto_modelos_lenguaje.agent memory list --user ID` | Auditoría de la memoria a largo plazo de un seudónimo (qué, cuándo). | stdout |
| `python -m proyecto_modelos_lenguaje.rag evaluate --queries tests/fixtures/rag/module3_queries.jsonl --qdrant-url URL` | Recall@10, nDCG@10 y MRR sobre el servidor; compara con la línea base. | `docs/evaluacion_modulo3.{json,md}` |
| `python -m proyecto_modelos_lenguaje.rag project [--sample 5000] [--seed 2026]` | t-SNE de fragmentos + consultas, figura y coordenadas. | `docs/proyeccion_embeddings.{png,json}` |
| `python -m proyecto_modelos_lenguaje.mcp_server [--list]` | Servidor MCP stdio (o lista de herramientas). | stdio |
| `pml channels simulate --sender +570000000000 --text "…"` | Envía un mensaje al endpoint del canal como lo haría el puente (pruebas y ensayo sin teléfono). | respuesta JSON |
| `pml ops workspace sync` | Copia `openclaw/workspace/` al workspace de ejecución. | — |
| `pml ops check [--json]` | Prueba de 3 minutos: backend, Qdrant, modelo, `openclaw gateway status`, `channels status --probe`, `security audit`, `git status`. | informe; código ≠ 0 si algo falla |
| `make corpus`, `make openclaw-workspace`, `make ops-check`, `make mcp` | Atajos de los anteriores. | |
