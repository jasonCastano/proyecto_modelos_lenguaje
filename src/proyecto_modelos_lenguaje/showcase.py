"""Build the Module 1 showcase payload from real corpus metrics."""

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
            id="app",
            order=6,
            title="Una interfaz para preguntar y entender",
            body=(
                "Esta página reemplaza el prototipo: hero editorial, consola RAG, fuentes visibles, "  # noqa: E501
                "modo demo y un recorrido que explica el sistema sin diapositivas."
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
            order=7,
            title="Medir antes de afirmar",
            body=(
                "Las cifras del corpus, la cobertura y los tokens provienen de reportes reales. La "
                "evaluación de 40 preguntas medirá calidad, citas y alucinaciones con una línea base."  # noqa: E501
            ),
            status="partial",
            metrics=[by_key["tokens_silver"], by_key["tokens_gold"], by_key["coverage"]],
            evidence=[
                EvidenceLink(
                    label="Cobertura",
                    href=f"{REPO}/data/gold/coverage.json",
                    kind="report",
                )
            ],
        ),
        ShowcaseSection(
            id="limits",
            order=8,
            title="Lo que todavía falta",
            body=(
                "La evaluación de 40 preguntas, el informe y el guion de demo están en curso. El "
                "sistema declara sus vacíos y no sustituye la información oficial de Manuelita."
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
