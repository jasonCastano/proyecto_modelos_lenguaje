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
    section = " > ".join(citation.section_path)
    location = f"sección: {section}" if section else "sin sección"
    if citation.page_start is not None:
        location += f", p. {citation.page_start}"
    if citation.time_start is not None:
        location += f", {int(citation.time_start)} s"
    return location


def render_citations(citations) -> None:
    if not citations:
        st.caption("Sin fuentes citadas.")
        return
    st.markdown("**Fuentes**")
    for citation in citations:
        st.markdown(citation_markdown(citation))
        st.caption(citation_location(citation))


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
        f"Modelo: {result.model} · prompt: {result.prompt_version} · "
        f"latencia: {result.latency_seconds:.2f} s · citas: {len(result.citations)} · "
        f"estado: {format_status(result.status)}"
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
                if kind == "success":
                    st.success(label)
                elif kind == "warning":
                    st.warning(label)
                else:
                    st.info(label)
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


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="🏭", layout="wide")
    st.title(PAGE_TITLE)
    st.caption("Resumen, FAQ y Q&A sobre información pública de Manuelita, con citas verificables.")
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
    _render_panel(metrics, bool(st.session_state.demo_mode))
    if not data_ready:
        st.warning("Los datos de oro no están completos. Ejecuta `git lfs pull` y recarga la app.")
    tabs = st.tabs(["Resumen", "FAQ", "Q&A"])
    demo_mode = bool(st.session_state.demo_mode)
    with tabs[0]:
        render_summary(demo_mode, data_ready)
    with tabs[1]:
        render_faq(demo_mode, data_ready)
    with tabs[2]:
        render_qa(demo_mode, data_ready)


if __name__ == "__main__":
    main()
