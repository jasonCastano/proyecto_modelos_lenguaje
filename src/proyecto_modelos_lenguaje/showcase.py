"""Build the Module 1 and Module 2 showcase payload from real corpus metrics."""

from __future__ import annotations

from datetime import UTC, datetime

from .api_models import CorpusMetric, DataStatus, EvidenceLink, ShowcaseResponse, ShowcaseSection
from .app_metrics import AppMetrics, load_app_metrics

REPO = "https://github.com/jasonCastano/proyecto_modelos_lenguaje/blob/main"


def _metric(
    key: str,
    label: str,
    value: float,
    unit: str,
    source: str,
    status: DataStatus,
) -> CorpusMetric:
    return CorpusMetric(
        key=key,
        label=label,
        value=float(value),
        unit=unit,
        source=source,
        status=status,
    )


def _metrics(metrics: AppMetrics) -> list[CorpusMetric]:
    status = metrics.data_status
    return [
        _metric(
            "active_artifacts",
            "Artefactos activos",
            metrics.active_artifacts,
            "artefactos",
            "data/bronze/_meta/bronze.sqlite3",
            status,
        ),
        _metric(
            "canonical_documents",
            "Documentos canónicos",
            metrics.canonical_documents,
            "documentos",
            "data/silver/reports/2026-10-silver-01/quality.json",
            status,
        ),
        _metric(
            "aliases",
            "Alias documentales",
            metrics.aliases,
            "alias",
            "data/silver/reports/2026-10-silver-01/quality.json",
            status,
        ),
        _metric(
            "chunks",
            "Fragmentos",
            metrics.chunks,
            "fragmentos",
            "data/silver/reports/2026-10-silver-01/quality.json",
            status,
        ),
        _metric(
            "units",
            "Unidades de conocimiento",
            metrics.units,
            "unidades",
            "data/gold/reports/2026-10-gold-01/quality.json",
            status,
        ),
        _metric(
            "facts",
            "Hechos",
            metrics.facts,
            "hechos",
            "data/gold/reports/2026-10-gold-01/quality.json",
            status,
        ),
        _metric(
            "entities",
            "Entidades",
            metrics.entities,
            "entidades",
            "data/gold/reports/2026-10-gold-01/quality.json",
            status,
        ),
        _metric(
            "conflicts",
            "Conflictos preservados",
            metrics.conflicts,
            "conflictos",
            "data/gold/reports/2026-10-gold-01/quality.json",
            status,
        ),
        _metric(
            "coverage",
            "Cobertura obligatoria",
            metrics.coverage_covered,
            f"de {metrics.coverage_total} ítems",
            "data/gold/coverage.json",
            status,
        ),
        _metric(
            "tokens_silver",
            "Tokens de plata",
            metrics.silver_tokens,
            "tokens",
            f"data/silver/reports/{metrics.silver_run}/quality.json",
            status,
        ),
        _metric(
            "tokens_gold",
            "Tokens de oro",
            metrics.gold_tokens,
            "tokens",
            f"data/gold/reports/{metrics.gold_run}/quality.json",
            status,
        ),
    ]


def build_showcase(metrics: AppMetrics | None = None) -> ShowcaseResponse:
    """Return the narrative plus real metrics for the one-page showcase."""
    current = metrics or load_app_metrics()
    all_metrics = _metrics(current)
    by_key = {metric.key: metric for metric in all_metrics}

    sections = [
        ShowcaseSection(
            id="problem",
            order=1,
            title="La información estaba dispersa",
            body=(
                "La pregunta de un cliente primerizo se repartía entre el sitio oficial, informes, "
                "noticias, videos y portales públicos. Un asistente genérico podía responder rápido, "  # noqa: E501
                "pero no siempre con evidencia."
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Alcance y 40 preguntas",
                    href=f"{REPO}/docs/alcance.md",
                    kind="spec",
                )
            ],
        ),
        ShowcaseSection(
            id="data",
            order=2,
            title="Un corpus público y trazable",
            body=(
                "La adquisición respeta robots.txt, sitemap, límites de tasa y una campaña reanudable. "  # noqa: E501
                "Cada artefacto conserva URL, fecha UTC, tipo y hash; la cuarentena queda auditada y "  # noqa: E501
                "fuera del corpus activo."
            ),
            status="done",
            metrics=[
                by_key["active_artifacts"],
                by_key["canonical_documents"],
                by_key["chunks"],
            ],
            evidence=[
                EvidenceLink(
                    label="Ficha de datos",
                    href=f"{REPO}/docs/data_card.md",
                    kind="report",
                )
            ],
        ),
        ShowcaseSection(
            id="medallion",
            order=3,
            title="Bronce, plata y oro",
            body=(
                "El bronce guarda bytes inmutables; la plata produce documentos canónicos, alias y "
                "fragmentos; el oro consolida unidades extractivas, hechos, entidades, conflictos y "  # noqa: E501
                "paquetes de contexto con citas."
            ),
            status="done",
            metrics=[
                by_key["units"],
                by_key["facts"],
                by_key["entities"],
                by_key["conflicts"],
                by_key["coverage"],
            ],
            evidence=[
                EvidenceLink(
                    label="Capa oro",
                    href=f"{REPO}/specs/004-gold-medallion-layer/spec.md",
                    kind="spec",
                ),
                EvidenceLink(
                    label="ADR de oro",
                    href=f"{REPO}/docs/decisions/0004-gold-layer.md",
                    kind="adr",
                ),
            ],
        ),
        ShowcaseSection(
            id="prompts",
            order=4,
            title="Prompts que prohíben inventar",
            body=(
                "Cada prompt declara rol, tarea, contexto delimitado, reglas, formato de citación y "  # noqa: E501
                "fallback. El texto recuperado es dato no confiable; nunca se ejecuta como instrucción."  # noqa: E501
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Prompt log",
                    href=f"{REPO}/docs/prompt_log.md",
                    kind="report",
                )
            ],
        ),
        ShowcaseSection(
            id="tasks",
            order=5,
            title="Tres tareas, una misma regla",
            body=(
                "Resumen, FAQ y Q&A usan LangChain y recuperación léxica determinista. DeepSeek genera "  # noqa: E501
                "la respuesta, pero las citas [U#] se validan contra el contexto recuperado."
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Proveedor DeepSeek",
                    href=f"{REPO}/specs/011-deepseek-api-model/spec.md",
                    kind="spec",
                )
            ],
        ),
        ShowcaseSection(
            id="retrieval",
            order=6,
            title="Qdrant: buscar por significado, no solo por palabras",
            body=(
                "Los 15.211 fragmentos viven en una colección de Qdrant (coseno, índice HNSW) "
                "con payload filtrable por tema, fuente y tipo. La búsqueda densa top-k se "
                "fusiona con BM25 y se mide con Recall@10, nDCG@10 y MRR en 36 consultas "
                "etiquetadas."
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Recuperación semántica",
                    href=f"{REPO}/specs/013-semantic-rag-chatbot/spec.md",
                    kind="spec",
                ),
                EvidenceLink(
                    label="ADR de Qdrant",
                    href=f"{REPO}/docs/decisions/0018-qdrant-y-rubrica-modulo2.md",
                    kind="adr",
                ),
            ],
        ),
        ShowcaseSection(
            id="agent",
            order=7,
            title="Una conversación que recuerda y decide",
            body=(
                "Corto plazo: cada hilo se guarda con SqliteSaver y sobrevive al reinicio. "
                "Largo plazo: el perfil y las preferencias viven en el Store y se recuperan en "
                "otro hilo. El enrutador elige respuesta directa, documentos, tabla, ambas o "
                "fuera de alcance (35 de 36 aciertos) y no busca ante un saludo."
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Memoria, enrutador y agente",
                    href=f"{REPO}/specs/014-rag-agent-memory-router/spec.md",
                    kind="spec",
                ),
                EvidenceLink(
                    label="ADR del agente",
                    href=f"{REPO}/docs/decisions/0016-rag-agent-langgraph.md",
                    kind="adr",
                ),
                EvidenceLink(
                    label="Rúbrica del Módulo 2",
                    href=f"{REPO}/docs/rubrica_modulo2.md",
                    kind="report",
                ),
            ],
        ),
        ShowcaseSection(
            id="safety",
            order=8,
            title="Leer solo, escribir con permiso",
            body=(
                "El texto recuperado va delimitado como dato pasivo: si un documento dice "
                "«ignora las instrucciones», se marca y no se obedece. Guardar el perfil o una "
                "preferencia, olvidar la memoria o exportar una conversación espera la "
                "aprobación de una persona."
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Política de memoria",
                    href=f"{REPO}/docs/memoria.md",
                    kind="report",
                )
            ],
        ),
        ShowcaseSection(
            id="app",
            order=9,
            title="Una interfaz propia, en streaming",
            body=(
                "React desacoplado de FastAPI: la respuesta llega en streaming (SSE), los hilos "
                "se retoman tras reiniciar, cada turno muestra ruta, fragmentos, fuentes, "
                "tokens y latencia, y los errores de red o del modelo se explican sin romper la "
                "página."
            ),
            status="done",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Especificación del frontend",
                    href=f"{REPO}/specs/012-manuelita-rag-showcase/spec.md",
                    kind="spec",
                )
            ],
        ),
        ShowcaseSection(
            id="metrics",
            order=10,
            title="Medir antes de afirmar",
            body=(
                "Las cifras del corpus provienen de reportes reales. En el Módulo 2, cadena y "
                "agente citan bien el 100 % de las veces y la cadena responde en menos de 10 s. "
                "Cada turno queda trazado en LangSmith o en un log JSON con ruta, herramientas "
                "y tokens."
            ),
            status="partial",
            metrics=[by_key["tokens_silver"], by_key["tokens_gold"], by_key["coverage"]],
            evidence=[
                EvidenceLink(
                    label="Cobertura",
                    href=f"{REPO}/data/gold/coverage.json",
                    kind="report",
                ),
                EvidenceLink(
                    label="Evaluación del Módulo 2",
                    href=f"{REPO}/docs/evaluacion_modulo2.md",
                    kind="report",
                ),
            ],
        ),
        ShowcaseSection(
            id="limits",
            order=11,
            title="Lo que todavía falta",
            body=(
                "Del Módulo 1 falta la evaluación real de 40 preguntas. Del Módulo 2 quedan la "
                "calificación humana de las repreguntas, Qdrant con servidor dedicado, el "
                "gatekeeper Jev y el despliegue. El sistema declara sus vacíos y no sustituye "
                "la información oficial."
            ),
            status="pending",
            metrics=[],
            evidence=[
                EvidenceLink(
                    label="Limitaciones",
                    href=f"{REPO}/README.md",
                    kind="report",
                )
            ],
        ),
    ]

    return ShowcaseResponse(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        data_status=current.data_status,
        sections=sections,
        metrics=all_metrics,
    )
