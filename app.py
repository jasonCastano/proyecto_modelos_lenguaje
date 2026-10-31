"""Streamlit app for the Module 1: Summary, FAQ and Q&A with citations."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from proyecto_modelos_lenguaje.app_metrics import (
    AppMetrics,
    format_status,
    load_app_metrics,
    metric_rows,
    response_rows,
    status_rows,
)
from proyecto_modelos_lenguaje.brand import (
    citation_location as brand_citation_location,
)
from proyecto_modelos_lenguaje.brand import (
    footer_html,
    header_html,
    inject_brand_styles,
    source_cards_html,
    status_bar_html,
    status_variant,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.llm import (
    LLMConfigError,
    LLMModelMissingError,
    LLMResponseError,
    LLMUnavailableError,
    build_chat_model,
    health_check,
    load_llm_config,
)
from proyecto_modelos_lenguaje.retrieval import (
    RetrievalError,
    load_entity_index,
    load_faq_seeds,
    load_gold_units,
)
from proyecto_modelos_lenguaje.tasks import (
    TaskError,
    TaskResult,
    answer_question,
    build_scripted_model,
    generate_faq,
    summarize_corpus,
)

GOLD_DIR = PROJECT_ROOT / "data" / "gold"
DEMO_ENV = os.getenv("PML_DEMO", "").strip().lower() in {"1", "true", "yes", "on"}
PAGE_TITLE = "RAG Ingenio Manuelita — Módulo 1"
SUMMARY_PACKS = ("8000", "32000")
QA_MAX_CHARS = 500


@st.cache_data(ttl=60, show_spinner=False)
def metrics_cached() -> AppMetrics:
    return load_app_metrics(project_root=PROJECT_ROOT)


@st.cache_resource(show_spinner=False)
def units_cached():
    return load_gold_units(GOLD_DIR)


@st.cache_resource(show_spinner=False)
def seeds_cached():
    return load_faq_seeds(GOLD_DIR)


@st.cache_resource(show_spinner=False)
def entity_index_cached():
    return load_entity_index(GOLD_DIR)


@st.cache_resource(show_spinner=False)
def real_model_cached():
    return build_chat_model(load_llm_config())


@st.cache_data(ttl=30, show_spinner=False)
def model_health_cached() -> dict[str, Any]:
    try:
        return {"ok": True, **health_check(load_llm_config())}
    except (LLMConfigError, LLMUnavailableError, LLMModelMissingError, LLMResponseError) as exc:
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)}


def model_for(task: str, demo_mode: bool):
    if demo_mode or DEMO_ENV:
        return build_scripted_model(task)
    return real_model_cached()


def current_model_status(demo_mode: bool) -> str:
    if demo_mode or DEMO_ENV:
        return "demo"
    health = model_health_cached()
    if health.get("ok"):
        return "ollama_ready"
    if health.get("error") == "LLMModelMissingError":
        return "model_missing"
    return "ollama_unavailable"


def validate_question(question: str) -> str | None:
    text = question.strip()
    if not text:
        return "Escribe una pregunta antes de enviar."
    if len(text) > QA_MAX_CHARS:
        return f"La pregunta supera {QA_MAX_CHARS} caracteres."
    return None


def faq_status_badge(status: str) -> tuple[str, str]:
    if status == "ready":
        return "success", "Lista"
    if status == "review":
        return "warning", "Revisar"
    return "info", "Sin evidencia"


def citation_markdown(citation) -> str:
    return f"**[{citation.label}]** [{citation.title}]({citation.url})"


def citation_location(citation) -> str:
    return brand_citation_location(citation)


def render_citations(citations) -> None:
    if not citations:
        st.caption("Sin fuentes citadas.")
        return
    st.markdown("**Fuentes**")
    st.html(source_cards_html(citations))


def render_result(result: TaskResult) -> None:
    if result.status == "error":
        st.error(result.answer)
    elif result.status == "fallback":
        st.info(result.answer)
    elif result.status == "review":
        st.warning(result.answer)
    else:
        st.markdown(result.answer)
    render_citations(result.citations)
    st.caption(
        f"{status_variant(result.status).text} · Modelo: {result.model} · "
        f"prompt: {result.prompt_version} · latencia: {result.latency_seconds:.2f} s · "
        f"citas: {len(result.citations)} · estado: {format_status(result.status)}"
    )


def render_error(exc: Exception) -> None:
    message = error_message(exc)
    st.error(message)
    if isinstance(exc, TaskError):
        st.caption(f"Código: {exc.code}")
    st.session_state.last_error = type(exc).__name__


def error_message(exc: Exception) -> str:
    if isinstance(exc, TaskError):
        return exc.message
    if isinstance(exc, LLMUnavailableError):
        return "Ollama no responde. Ejecuta `ollama serve` o activa el modo demostración."
    if isinstance(exc, LLMModelMissingError):
        return "El modelo no está descargado. Ejecuta `ollama pull llama3.1:8b`."
    if isinstance(exc, LLMResponseError):
        return (
            "El modelo no devolvió una respuesta utilizable. Reintenta o usa el modo demostración."
        )
    if isinstance(exc, RetrievalError):
        return "No se pudo leer la base de conocimiento. Verifica `git lfs pull`."
    if isinstance(exc, LLMConfigError):
        return "La configuración del modelo es inválida. Revisa `config/llm.toml`."
    return "Ocurrió un error controlado. Revisa el panel y reintenta."


def _render_panel(metrics: AppMetrics, demo_mode: bool) -> str:
    with st.sidebar:
        st.header("Panel")
        st.toggle(
            "Modo demostración (modelo falso)",
            key="demo_mode",
            help="Usa respuestas de prueba sin Ollama. No representa al modelo real.",
        )
        demo_mode = bool(st.session_state.demo_mode)
        model_state = current_model_status(demo_mode)
        st.subheader("Estado")
        for row in status_rows(metrics, model_status=model_state, demo_mode=demo_mode):
            st.metric(row.label, row.value, help=row.help)
        st.subheader("Corpus")
        for row in metric_rows(metrics):
            st.metric(row.label, row.value, help=row.help)
        if metrics.data_status != "complete":
            st.error("Datos incompletos.")
            st.caption(metrics.detail or "Ejecuta `git lfs pull`.")
        if not demo_mode and model_state in {"ollama_unavailable", "model_missing"}:
            st.warning(format_status(model_state))
        st.subheader("Última respuesta")
        result = st.session_state.get("qa_result") or st.session_state.get("summary_result")
        if result is None:
            st.caption("Sin respuestas todavía.")
        else:
            for row in response_rows(
                model=result.model,
                prompt_version=result.prompt_version,
                latency_seconds=result.latency_seconds,
                citations=len(result.citations),
                status=result.status,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            ):
                st.metric(row.label, row.value, help=row.help)
        st.caption(
            "Panel de solo lectura: URLs, tokens, descartes y citas "
            "se muestran sin escribir en data/."
        )
    return "demo" if demo_mode else model_state


def render_summary(demo_mode: bool, data_ready: bool) -> None:
    st.subheader("Resumen del corpus")
    st.caption("Síntesis estructurada con citas verificables.")
    pack = st.radio(
        "Paquete de contexto",
        options=list(SUMMARY_PACKS),
        index=0
        if st.session_state.get("summary_pack", SUMMARY_PACKS[0]) == SUMMARY_PACKS[0]
        else 1,
        horizontal=True,
        disabled=not data_ready,
    )
    if st.button("Generar resumen", disabled=not data_ready):
        st.session_state.summary_pack = pack
        with st.spinner("Generando resumen…"):
            try:
                result = summarize_corpus(
                    pack=pack,
                    model=model_for("summary", demo_mode),
                    units=units_cached(),
                    gold_dir=GOLD_DIR,
                    project_root=PROJECT_ROOT,
                )
                st.session_state.summary_result = result
                st.session_state.summary_error = None
                st.session_state.last_error = None
            except Exception as exc:
                st.session_state.summary_result = None
                st.session_state.summary_error = exc
                st.session_state.last_error = exc
    result = st.session_state.get("summary_result")
    if result is not None:
        render_result(result)
    elif st.session_state.get("summary_error") is not None:
        render_error(st.session_state.summary_error)


def render_faq(demo_mode: bool, data_ready: bool) -> None:
    st.subheader("Preguntas frecuentes")
    st.caption("Preguntas semilla con respuesta, citas y estado de revisión.")
    limit = st.slider(
        "Número de preguntas",
        min_value=10,
        max_value=20,
        value=int(st.session_state.get("faq_limit", 12)),
        disabled=not data_ready,
    )
    if st.button("Generar FAQ", disabled=not data_ready):
        st.session_state.faq_limit = limit
        with st.spinner("Generando FAQ…"):
            try:
                items = generate_faq(
                    limit=limit,
                    model=model_for("faq", demo_mode),
                    units=units_cached(),
                    seeds=seeds_cached(),
                    gold_dir=GOLD_DIR,
                    project_root=PROJECT_ROOT,
                )
                st.session_state.faq_items = tuple(items)
                st.session_state.faq_error = None
                st.session_state.last_error = None
            except Exception as exc:
                st.session_state.faq_items = ()
                st.session_state.faq_error = exc
                st.session_state.last_error = exc
    items = st.session_state.get("faq_items", ())
    if items:
        for index, item in enumerate(items, start=1):
            with st.expander(f"{index}. {item.question}"):
                st.markdown(item.answer)
                kind, label = faq_status_badge(item.status)
                badge = f"{status_variant(item.status).icon} {label}"
                if kind == "success":
                    st.success(badge)
                elif kind == "warning":
                    st.warning(badge)
                else:
                    st.info(badge)
                render_citations(item.citations)
    elif st.session_state.get("faq_error") is not None:
        render_error(st.session_state.faq_error)


def _run_qa(question: str, demo_mode: bool) -> None:
    try:
        result = answer_question(
            question,
            model=model_for("qa", demo_mode),
            units=units_cached(),
            entity_index=entity_index_cached(),
            gold_dir=GOLD_DIR,
            project_root=PROJECT_ROOT,
        )
        st.session_state.qa_result = result
        st.session_state.qa_error = None
        st.session_state.last_error = None
    except Exception as exc:
        st.session_state.qa_result = None
        st.session_state.qa_error = exc
        st.session_state.last_error = exc


def render_qa(demo_mode: bool, data_ready: bool) -> None:
    st.subheader("Preguntas y respuestas")
    st.caption("Responde solo con evidencia de la base de conocimiento y cita la fuente.")
    with st.form("qa_form", clear_on_submit=False):
        question = st.text_area(
            "Pregunta",
            value=st.session_state.get("qa_question", ""),
            height=110,
            max_chars=QA_MAX_CHARS,
            placeholder="¿Qué productos ofrece Manuelita?",
            disabled=not data_ready,
        )
        submitted = st.form_submit_button("Preguntar", disabled=not data_ready)
    if submitted:
        problem = validate_question(question)
        if problem is not None:
            st.warning(problem)
        else:
            text = question.strip()
            st.session_state.qa_question = text
            with st.spinner("Generando respuesta…"):
                _run_qa(text, demo_mode)
    result = st.session_state.get("qa_result")
    if result is not None:
        render_result(result)
    elif st.session_state.get("qa_error") is not None:
        render_error(st.session_state.qa_error)
    if st.session_state.get("qa_question") and st.button("Reintentar", disabled=not data_ready):
        with st.spinner("Reintentando…"):
            _run_qa(st.session_state.qa_question, demo_mode)


def status_items(metrics: AppMetrics, model_state: str) -> list[tuple[str, str, str]]:
    """Status chips for the header: data, model and demo mode."""
    data = (
        ("ok", "✓", "Datos completos")
        if metrics.data_status == "complete"
        else ("error", "×", "Datos incompletos")
    )
    model = {
        "ollama_ready": ("ok", "✓", "Modelo listo"),
        "ollama_unavailable": ("error", "×", "Ollama no responde"),
        "model_missing": ("error", "×", "Modelo no descargado"),
        "demo": ("demo", "●", "Modo demo"),
    }.get(model_state, ("review", "!", format_status(model_state)))
    items = [data, model]
    if model_state == "demo" and data[0] != "demo":
        items.append(("demo", "●", "Modo demo"))
    return items


def _bullets(items: list[str]) -> str:
    """Join short bullet texts as a Markdown list."""
    return "\n".join(f"- {item}" for item in items)


def _data_warning(metrics: AppMetrics) -> None:
    if metrics.data_status != "complete":
        st.warning(
            "Los datos no están completos. Ejecuta `git lfs pull` o el pipeline de la capa "
            "y recarga la app."
        )
        if metrics.detail:
            st.caption(metrics.detail)


def _money(value: int) -> str:
    """Format an integer with dots as thousands separator."""
    return f"{value:,}".replace(",", ".")


def render_home(demo_mode: bool, data_ready: bool) -> None:
    """Consola de consulta: Resumen, FAQ y Q&A."""
    tabs = st.tabs(["Resumen", "FAQ", "Q&A"])
    with tabs[0]:
        render_summary(demo_mode, data_ready)
    with tabs[1]:
        render_faq(demo_mode, data_ready)
    with tabs[2]:
        render_qa(demo_mode, data_ready)


def render_bronze_page(metrics: AppMetrics) -> None:
    """Explica la capa bronce: adquisición inmutable de los originales."""
    st.subheader("Capa bronce — adquisición inmutable")
    st.markdown(
        "El bronce guarda **los bytes originales** de cada fuente pública, tal como se "
        "descargaron, con su hash SHA-256, su procedencia y la fecha de captura. Nada se "
        "reescribe: si una página cambia, se guarda una versión nueva. Es la evidencia "
        "primaria del proyecto."
    )
    _data_warning(metrics)
    columns = st.columns(4)
    columns[0].metric("Artefactos activos", _money(metrics.active_artifacts))
    columns[1].metric("Descartados", _money(metrics.skipped))
    columns[2].metric("Omisiones", _money(metrics.omissions))
    columns[3].metric("Estado de datos", format_status(metrics.data_status))

    st.markdown("#### Cómo se construyó")
    st.markdown(
        _bullets(
            [
                "**Fuentes declaradas**: sitio oficial, prensa, gremios, datos abiertos, YouTube "
                "y Linktree, cada una con su política en `config/sources.toml`.",
                "**Rastreo respetuoso**: `scrapling` con `robots.txt`, sitemaps, límite de tasa "
                "y exclusión de los dominios que lo prohíben.",
                "**Identidad por contenido**: cada archivo se nombra con su SHA-256, de modo que "
                "un duplicado no se vuelve a almacenar.",
                "**Catálogo SQLite** (`data/bronze/_meta/bronze.sqlite3`): procedencia, "
                "deduplicación, versiones, cobertura y auditoría.",
                "**Cuarentena**: lo retirado se mueve a `data/quarantine/` con auditoría y "
                "ventana de reversibilidad; no se borra sin rastro.",
            ]
        )
    )
    st.markdown("#### Dónde vive")
    st.code(
        "data/bronze/raw/<fuente>/<campaña>/<sha256>.<ext>\n"
        "data/bronze/manifests/<campaña>.jsonl\n"
        "data/bronze/reports/<campaña>/\n"
        "data/bronze/_meta/bronze.sqlite3",
        language="text",
    )
    st.markdown("#### Límites")
    st.caption(
        "No se hace OCR ni se interpreta contenido: un PDF escaneado sin texto se registra como "
        "omitido. Los originales se versionan en Git LFS, no en el historial de Git."
    )


def render_silver_page(metrics: AppMetrics) -> None:
    """Explica la capa plata: texto limpio, secciones y fragmentos."""
    st.subheader("Capa plata — texto limpio y fragmentos")
    st.markdown(
        "La plata convierte cada original en **texto legible y citable**: quita navegación y "
        "ruido, repara la codificación, detecta el idioma, reconstruye secciones y corta el "
        "contenido en fragmentos recuperables. Es determinista: no usa LLM, embeddings ni OCR."
    )
    _data_warning(metrics)
    columns = st.columns(4)
    columns[0].metric("Documentos canónicos", _money(metrics.canonical_documents))
    columns[1].metric("Fragmentos", _money(metrics.chunks))
    columns[2].metric("Alias", _money(metrics.aliases))
    columns[3].metric("Tokens", _money(metrics.silver_tokens))
    st.caption(f"Última ejecución de plata: `{metrics.silver_run}`")

    st.markdown("#### Cómo se construyó")
    st.markdown(
        _bullets(
            [
                "**Extracción por formato**: HTML, PDF y subtítulos VTT; cada formato tiene su "
                "extractor y sus reglas de limpieza.",
                "**Normalización**: espacios, saltos, mojibake y caracteres de control; el texto "
                "conserva las palabras y las cifras originales.",
                "**Deduplicación**: los documentos duplicados se enlazan como alias de un "
                "canónico, sin perder la trazabilidad del artefacto.",
                "**Secciones y chunks**: se reconstruye la jerarquía de títulos y se corta en "
                "fragmentos con su ruta de sección y su rango de caracteres.",
                "**Idioma**: detección heurística por documento para no mezclar contenido en "
                "inglés.",
            ]
        )
    )
    st.markdown("#### Dónde vive")
    st.code(
        "data/silver/documents.jsonl   # documentos canónicos y alias\n"
        "data/silver/chunks.jsonl      # fragmentos recuperables\n"
        "data/silver/markdown/         # revisión humana con frontmatter\n"
        "data/silver/reports/          # calidad por ejecución",
        language="text",
    )
    st.markdown("#### Límites")
    st.caption(
        "La plata no resume ni responde: eso ocurre en las tareas del Módulo 1 sobre la capa "
        "de oro. Un documento sin texto útil se omite con una razón registrada."
    )


def render_gold_page(metrics: AppMetrics) -> None:
    """Explica la capa oro: base de conocimiento extractiva y trazable."""
    st.subheader("Capa oro — base de conocimiento trazable")
    st.markdown(
        "El oro es la **base de conocimiento del proyecto**: unidades extractivas que conservan "
        "su cita, hechos numéricos, entidades, conflictos, la matriz de cobertura de los 24 "
        "ítems, las preguntas semilla de la FAQ y los paquetes de contexto de 8k y 32k. Cada "
        "afirmación puede rastrearse hasta su URL y su sección."
    )
    _data_warning(metrics)
    columns = st.columns(4)
    columns[0].metric("Unidades", _money(metrics.units))
    columns[1].metric("Hechos", _money(metrics.facts))
    columns[2].metric("Entidades", _money(metrics.entities))
    columns[3].metric("Conflictos", _money(metrics.conflicts))
    columns = st.columns(3)
    columns[0].metric("Cobertura", f"{metrics.coverage_covered}/{metrics.coverage_total}")
    columns[1].metric("Tokens", _money(metrics.gold_tokens))
    columns[2].metric("Ejecución", metrics.gold_run)
    st.caption(f"Última ejecución de oro: `{metrics.gold_run}`")

    st.markdown("#### Cómo se construyó")
    st.markdown(
        _bullets(
            [
                "**Unidades extractivas**: texto con tema, autoridad, estado, entidades y "
                "banderas de calidad; nunca texto generado por un modelo.",
                "**Hechos y entidades**: cifras, fechas y actores normalizados para responder "
                "preguntas concretas sin inventar.",
                "**Conflictos preservados**: si dos fuentes discrepan, se guardan ambas versiones "
                "con su cita en lugar de promediar.",
                "**Cobertura de los 24 ítems**: cada ítem declara si está cubierto, parcial o "
                "ausente, y por qué.",
                "**Paquetes de contexto**: selección por cobertura, autoridad, vigencia y "
                "diversidad, con presupuesto de 8.000 y 32.000 tokens.",
            ]
        )
    )
    st.markdown("#### Dónde vive")
    st.code(
        "data/gold/knowledge_units.jsonl   # unidades con evidencia\n"
        "data/gold/facts.jsonl             # hechos numéricos y fechados\n"
        "data/gold/entities.jsonl          # entidades canónicas y alias\n"
        "data/gold/conflicts.jsonl         # contradicciones con su cita\n"
        "data/gold/faq_seeds.jsonl         # preguntas semilla de la FAQ\n"
        "data/gold/context_8000.json       # paquete de contexto por defecto\n"
        "data/gold/coverage.json           # matriz de los 24 ítems",
        language="text",
    )
    st.markdown("#### Límites")
    st.caption(
        "El oro no resume ni responde: eso lo hacen las tareas del Módulo 1 con LangChain, "
        "citando estas unidades. Si la evidencia no alcanza, la app responde con un fallback "
        "explícito."
    )


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="🌱", layout="wide")
    inject_brand_styles()
    st.html(header_html())
    for key, value in {
        "qa_result": None,
        "qa_question": "",
        "qa_error": None,
        "summary_result": None,
        "summary_error": None,
        "summary_pack": "8000",
        "faq_items": (),
        "faq_error": None,
        "faq_limit": 12,
        "last_error": None,
    }.items():
        st.session_state.setdefault(key, value)
    if "demo_mode" not in st.session_state:
        st.session_state.demo_mode = DEMO_ENV

    metrics = metrics_cached()
    data_ready = metrics.data_status == "complete"
    demo_mode = bool(st.session_state.demo_mode)
    st.html(status_bar_html(status_items(metrics, current_model_status(demo_mode))))
    _render_panel(metrics, demo_mode)
    if not data_ready:
        st.warning("Los datos de oro no están completos. Ejecuta `git lfs pull` y recarga la app.")

    pages = [
        st.Page(
            lambda: render_home(demo_mode, data_ready),
            title="Consulta",
            icon=":material/chat:",
            default=True,
        ),
        st.Page(
            lambda: render_bronze_page(metrics),
            title="Bronce",
            icon=":material/archive:",
            url_path="bronce",
        ),
        st.Page(
            lambda: render_silver_page(metrics),
            title="Plata",
            icon=":material/layers:",
            url_path="plata",
        ),
        st.Page(
            lambda: render_gold_page(metrics),
            title="Oro",
            icon=":material/diamond:",
            url_path="oro",
        ),
    ]
    st.navigation(pages).run()
    st.html(footer_html())


if __name__ == "__main__":
    main()
