# Documentación — RAG Ingenio Manuelita

Índice de la documentación viva del proyecto. La fuente única de verdad es
[`../CONSTITUTION.md`](../CONSTITUTION.md); cada documento amplía un tema y debe enlazarse desde el
README o la constitución.

## Documentos principales

| Documento | Contenido |
|-----------|-----------|
| [`alcance.md`](alcance.md) | Alcance del Q&A y banco de 40 preguntas. |
| [`data_card.md`](data_card.md) | Fuentes, licencias, volumen, LFS y limitaciones del corpus. |
| [`fuentes_oficiales.md`](fuentes_oficiales.md) | Canales oficiales, robots, bloqueos y cobertura. |
| [`prompt_log.md`](prompt_log.md) | Versiones de prompts, modelos, parámetros y resultados. |
| [`arquitectura.html`](arquitectura.html) | Diagrama interactivo del pipeline (Archify). |
| [`arquitectura.json`](arquitectura.json) | Fuente tipada del diagrama. |
| [`decisions/`](decisions/) | ADRs de arquitectura, modelo, datos y app. |

## Especificaciones

Las features viven en [`../specs/`](../specs/) con `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`
y contratos cuando aplica. La más reciente es
[`012-manuelita-rag-showcase`](../specs/012-manuelita-rag-showcase/spec.md).

## Bitácoras

Las bitácoras fechadas están en [`../bitacora/`](../bitacora/). Se regeneran con:

```bash
uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py
```

## Convenciones

- Un documento, un tema.
- Fechas ISO (`AAAA-MM-DD`).
- Sin datos sensibles, credenciales ni rutas absolutas.
- Los diagramas se regeneran desde su JSON; el HTML no se edita a mano.
