"""Streamlit app for the Module 1: Summary, FAQ and Q&A with citations.

Read-only by design: the app never writes inside the repository or the medallion layers. The only
writes are the browser download of the session and Streamlit's own in-memory state.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
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
SESSION_FILE = "sesion_rag_manuelita.json"
SUGGESTED_QUESTIONS = (
    "¿Qué productos ofrece Manuelita?",
    "¿Dónde está la casa matriz de Manuelita?",
    "¿En qué países tiene presencia?",
    "¿Qué certificaciones ambientales tiene?",
)


@st.cache_data(show_spinner=False)
def metrics_cached() -> AppMetrics:
    return load_app_metrics()


@st.cache_data(show_spinner=False)
def units_cached():
    return load_gold_units(GOLD_DIR)


@st.cache_data(show_spinner=False)
def seeds_cached():
    return load_faq_seeds(GOLD_DIR)


@st.cache_data(show_spinner=False)
def entity_index_cached():
    return load_entity_index(GOLD_DIR)


@st.cache_resource(show_spinner=False)
def real_model_cached():
    return build_chat_model(load_llm_config())


@st.cache_data(show_spinner=False, ttl=30)
def model_health_cached() -> dict[str, Any]:
    try:
        return health_check(load_llm_config())
    except (
        LLMConfigError,
        LLMUnavailableError,
        LLMModelMissingError,
        LLMResponseError,
    ) as exc:
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
    return {
        "LLMModelMissingError": "model_missing",
        "LLMUnavailableError": "ollama_unavailable",
    }.get(str(health.get("error")), "ollama_unavailable")


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


# --- sesión ------------------------------------------------------------------------------------


def _reset_session() -> None:
    """Clear every app key, keeping nothing on disk."""
    for key in list(st.session_state):
        if key.startswith("_pml_"):
            continue
        del st.session_state[key]


def _session_payload(metrics: AppMetrics) -> str:
    """Serializable snapshot of the session; contains no secrets or absolute paths."""
    chat: list[dict[str, Any]] = []
    for turn in st.session_state.get("chat_history", []):
        if turn["role"] == "user":
            chat.append({"role": "user", "question": turn["content"]})
            continue
        result = turn.get("result")
        if result is not None:
            chat.append(
                {
                    "role": "assistant",
                    "answer": result.answer,
                    "status": result.status,
                    "model": result.model,
                    "prompt_version": result.prompt_version,
                    "citations": [citation.to_dict() for citation in result.citations],
                }
            )
        else:
            turn_error = turn.get("error")
            chat.append(
                {
                    "role": "assistant",
                    "error": type(turn_error).__name__ if turn_error else "unknown",
                }
            )
    summary = st.session_state.get("summary_result")
    faq_items = st.session_state.get("faq_items", ())
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "demo_mode": bool(st.session_state.get("demo_mode")),
        "corpus": metrics.to_dict(),
        "chat": chat,
        "summary": summary.to_dict() if summary is not None else None,
        "faq": [item.to_dict() for item in faq_items],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# --- panel lateral -----------------------------------------------------------------------------


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
        result = st.session_state.get("last_result")
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
        st.subheader("Sesión")
        st.download_button(
            "Descargar sesión (JSON)",
            data=_session_payload(metrics),
            file_name=SESSION_FILE,
            mime="application/json",
            help=(
                "Descarga la conversación, el resumen y la FAQ de esta sesión. "
                "No escribe en el repositorio."
            ),
            use_container_width=True,
        )
        if st.button("Limpiar sesión", use_container_width=True):
            _reset_session()
            st.rerun()
        st.caption(
            "Solo lectura: no se escribe en `data/` ni en el repositorio. "
            "La descarga vive únicamente en tu navegador."
        )
    return "demo" if demo_mode else model_state


# --- consulta (chat) ---------------------------------------------------------------------------


def _run_qa(question: str, demo_mode: bool) -> tuple[TaskResult | None, Exception | None]:
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
        st.session_state.last_result = result
        return result, None
    except Exception as exc:
        st.session_state.qa_result = None
        st.session_state.qa_error = exc
        st.session_state.last_error = exc
        return None, exc


def _append_turn(question: str, demo_mode: bool) -> None:
    history = st.session_state.setdefault("chat_history", [])
    history.append({"role": "user", "content": question})
    with st.spinner("Buscando evidencia y redactando la respuesta…"):
        result, error = _run_qa(question, demo_mode)
    history.append({"role": "assistant", "result": result, "error": error})
    st.session_state.last_question = question


def _retry_last(demo_mode: bool) -> None:
    """Re-run the last question, replacing the failed answer instead of duplicating it."""
    history = st.session_state.setdefault("chat_history", [])
    if history and history[-1]["role"] == "assistant":
        history.pop()
    question = history[-1]["content"] if history else ""
    if not question:
        return
    with st.spinner("Reintentando…"):
        result, error = _run_qa(question, demo_mode)
    history.append({"role": "assistant", "result": result, "error": error})


def _render_history(demo_mode: bool) -> None:
    for turn in st.session_state.get("chat_history", []):
        if turn["role"] == "user":
            with st.chat_message("user"):
                st.markdown(turn["content"])
            continue
        with st.chat_message("assistant", avatar="🌱"):
            if turn.get("result") is not None:
                render_result(turn["result"])
            elif turn.get("error") is not None:
                render_error(turn["error"])
                if st.button("Reintentar", key=f"retry_{id(turn)}"):
                    _retry_last(demo_mode)
                    st.rerun()


def render_chat(demo_mode: bool, data_ready: bool) -> None:
    """Main screen: suggested questions, chat input, history with source cards."""
    st.subheader("Consulta")
    st.caption(
        "Pregunta sobre Manuelita y recibe una respuesta con fuentes verificables. "
        f"Máximo {QA_MAX_CHARS} caracteres por pregunta."
    )
    history = st.session_state.setdefault("chat_history", [])
    if not history:
        st.markdown("**Sugerencias**")
        columns = st.columns(2)
        for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
            if columns[index % 2].button(
                suggestion,
                key=f"suggestion_{index}",
                disabled=not data_ready,
                use_container_width=True,
            ):
                st.session_state.pending_question = suggestion
                st.rerun()
    _render_history(demo_mode)

    if st.session_state.get("pending_question"):
        question = st.session_state.pop("pending_question")
    else:
        question = st.chat_input(
            "Escribe tu pregunta…",
            max_chars=QA_MAX_CHARS,
            disabled=not data_ready,
        )
    if question:
        problem = validate_question(question)
        if problem is not None:
            st.warning(problem)
        else:
            _append_turn(question.strip(), demo_mode)
            st.rerun()


# --- resumen -----------------------------------------------------------------------------------


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
                st.session_state.last_result = result
            except Exception as exc:
                st.session_state.summary_result = None
                st.session_state.summary_error = exc
                st.session_state.last_error = exc
    result = st.session_state.get("summary_result")
    if result is not None:
        render_result(result)
    elif st.session_state.get("summary_error") is not None:
        render_error(st.session_state.summary_error)


# --- faq ---------------------------------------------------------------------------------------


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


# --- métricas ----------------------------------------------------------------------------------


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _money(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _medallion_layers(metrics: AppMetrics) -> None:
    """Explain each medallion layer with the numbers of this corpus."""
    with st.expander("Bronce — adquisición inmutable"):
        st.markdown(
            _bullets(
                [
                    f"**Artefactos activos**: {_money(metrics.active_artifacts)} "
                    f"({_money(metrics.skipped)} descartados, {_money(metrics.omissions)} "
                    "omisiones).",
                    "**Bytes originales** con hash SHA-256, procedencia y fecha de captura; "
                    "nunca se reescriben.",
                    "**Manifiestos y catálogo SQLite** (`data/bronze/_meta/bronze.sqlite3`) "
                    "para procedencia, deduplicación y auditoría.",
                    "**Cuarentena** en `data/quarantine/` con ventana de reversibilidad.",
                ]
            )
        )
    with st.expander("Plata — texto limpio y fragmentos"):
        st.markdown(
            _bullets(
                [
                    f"**{_money(metrics.canonical_documents)} documentos canónicos** y "
                    f"{_money(metrics.aliases)} alias.",
                    f"**{_money(metrics.chunks)} fragmentos** con su ruta de sección.",
                    f"**{_money(metrics.silver_tokens)} tokens** procesados en la última "
                    f"ejecución (`{metrics.silver_run}`).",
                    "Limpieza determinista: sin LLM, embeddings ni OCR.",
                ]
            )
        )
    with st.expander("Oro — base de conocimiento trazable"):
        st.markdown(
            _bullets(
                [
                    f"**{_money(metrics.units)} unidades** extractivas con cita obligatoria.",
                    f"**{_money(metrics.facts)} hechos**, {_money(metrics.entities)} entidades "
                    f"y {_money(metrics.conflicts)} conflictos preservados.",
                    f"**Cobertura {metrics.coverage_covered}/{metrics.coverage_total}** de los "
                    "ítems obligatorios.",
                    f"**Paquetes de contexto** de 8k y 32k con {_money(metrics.gold_tokens)} "
                    "tokens en la última ejecución.",
                ]
            )
        )


def render_metrics(metrics: AppMetrics) -> None:
    """Cards, charts and the medallion explanation."""
    st.subheader("Métricas del corpus")
    st.caption("Lectura directa de los reportes y del catálogo; la app no escribe nada.")
    first = st.columns(4)
    first[0].metric("Documentos", _money(metrics.canonical_documents))
    first[1].metric("Fragmentos", _money(metrics.chunks))
    first[2].metric("Unidades", _money(metrics.units))
    first[3].metric("Hechos", _money(metrics.facts))
    second = st.columns(4)
    second[0].metric("Cobertura", f"{metrics.coverage_covered}/{metrics.coverage_total}")
    second[1].metric("Conflictos", _money(metrics.conflicts))
    second[2].metric("Tokens plata", _money(metrics.silver_tokens))
    second[3].metric("Tokens oro", _money(metrics.gold_tokens))

    st.markdown("#### Volumen del corpus")
    st.bar_chart(
        {
            "Documentos": metrics.canonical_documents,
            "Fragmentos": metrics.chunks,
            "Unidades": metrics.units,
            "Hechos": metrics.facts,
            "Entidades": metrics.entities,
            "Conflictos": metrics.conflicts,
        }
    )
    st.caption(
        "El gráfico usa las mismas cifras de las tarjetas. Los tokens se muestran aparte porque "
        "su escala es mucho mayor."
    )
    st.markdown("#### Tokens por capa")
    st.bar_chart({"Plata": metrics.silver_tokens, "Oro": metrics.gold_tokens})
    st.caption(f"Ejecuciones: plata `{metrics.silver_run}` · oro `{metrics.gold_run}`")

    st.markdown("#### Arquitectura medallion")
    st.caption(
        "Cada capa tiene una responsabilidad distinta; el detalle se explica a continuación con "
        "las cifras de este corpus."
    )
    _medallion_layers(metrics)


def _data_warning(metrics: AppMetrics) -> None:
    if metrics.data_status == "complete":
        return
    st.warning(
        "Los datos de oro no están completos. Ejecuta `git lfs pull` o el pipeline de la capa "
        "y recarga la app."
    )
    if metrics.detail:
        st.caption(metrics.detail)


# --- entrada -----------------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="🌱", layout="wide")
    inject_brand_styles()
    st.html(header_html())
    for key, value in {
        "qa_result": None,
        "qa_question": "",
        "qa_error": None,
        "chat_history": [],
        "pending_question": "",
        "last_question": "",
        "last_result": None,
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
    _data_warning(metrics)

    tabs = st.tabs(["Consulta", "Resumen", "FAQ", "Métricas"])
    with tabs[0]:
        render_chat(demo_mode, data_ready)
    with tabs[1]:
        render_summary(demo_mode, data_ready)
    with tabs[2]:
        render_faq(demo_mode, data_ready)
    with tabs[3]:
        render_metrics(metrics)
    st.html(footer_html())


if __name__ == "__main__":
    main()
