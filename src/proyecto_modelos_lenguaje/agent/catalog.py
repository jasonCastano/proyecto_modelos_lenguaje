"""Catálogo único de las 20 herramientas del agente (spec 024, ítem 1.1).

Contrato: ``specs/024-module3-openclaw-whatsapp/contracts/tools-catalog.md``.

De este registro salen las herramientas que ve el agente LangGraph (por ruta), el servidor MCP
(solo lectura), ``GET /api/tools``, ``agent tools`` y ``docs/herramientas.md``. Una sola fuente
evita que la traza, el MCP y la documentación diverjan.

Regla de oro (constitución): **lectura automática, escritura con aprobación**. Por eso
``requires_approval`` equivale a ``kind == "write"`` y ninguna herramienta de escritura se expone
por MCP.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.store.base import BaseStore
from pydantic import BaseModel, ValidationError

from ..rag.hybrid import HybridRetriever
from .actions import ARG_SCHEMAS, TOOL_DESCRIPTIONS, WRITE_TOOLS, build_write_tools
from .series import AggregateArgs, SeriesTable
from .structured import StructuredStore
from .tools import QueryStructuredArgs, SearchDocumentsArgs, ToolTrace, build_read_tools

ToolKind = Literal["read", "write"]
ROUTES: frozenset[str] = frozenset(
    {"direct", "documental", "structured", "mixed", "out_of_scope", "clarify"}
)
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
MIN_DESCRIPTION, MAX_DESCRIPTION = 20, 300
SUMMARY_CHARS = 200
TOOL_ERROR_PREFIX = "Error de la herramienta:"


class ToolArgsError(ValueError):
    """Argumentos inválidos para una herramienta del catálogo (mensaje en español)."""


@dataclass
class ToolContext:
    """Lo que una herramienta de lectura necesita en un turno (o en una llamada MCP)."""

    retriever: HybridRetriever | None = None
    store: StructuredStore | None = None
    series: SeriesTable | None = None
    trace: ToolTrace = field(default_factory=ToolTrace)
    question: str = ""
    user_id: str = "anon"
    memory_store: BaseStore | None = None
    top_k: int = 8
    neutralize: bool = True


ReadImpl = Callable[[ToolContext, Any], str]


@dataclass(frozen=True)
class ToolSpec:
    """Herramienta del catálogo (data-model §6)."""

    number: int
    name: str
    description: str
    args_schema: type[BaseModel]
    kind: ToolKind
    routes: frozenset[str]
    data_source: str
    impl: ReadImpl | None = None  # None: herramienta existente construida por su fábrica

    @property
    def requires_approval(self) -> bool:
        return self.kind == "write"

    @property
    def mcp(self) -> bool:
        return self.kind == "read"

    def validate(self) -> None:
        """Invariantes del catálogo; falla al cargar si alguna no se cumple."""
        if not NAME_PATTERN.match(self.name):
            raise ValueError(f"nombre inválido: {self.name}")
        if not MIN_DESCRIPTION <= len(self.description) <= MAX_DESCRIPTION:
            raise ValueError(f"{self.name}: la descripción debe tener 20–300 caracteres")
        if not self.routes or not self.routes <= ROUTES:
            raise ValueError(f"{self.name}: rutas inválidas {sorted(self.routes)}")
        if self.args_schema.model_config.get("extra") != "forbid":
            raise ValueError(f"{self.name}: el esquema debe usar extra='forbid'")
        if self.kind not in ("read", "write"):
            raise ValueError(f"{self.name}: tipo inválido {self.kind}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "requires_approval": self.requires_approval,
            "routes": sorted(self.routes),
            "mcp": self.mcp,
            "data_source": self.data_source,
            "schema": self.args_schema.model_json_schema(),
        }


def _routes(*names: str) -> frozenset[str]:
    return frozenset(names)


# --- Las 7 herramientas existentes (specs 014 y 018) --------------------------------------------

EXISTING_READ: tuple[ToolSpec, ...] = (
    ToolSpec(
        1,
        "search_documents",
        "Busca en los documentos públicos de Manuelita (historia, productos, sostenibilidad, "
        "programas, operaciones) con búsqueda híbrida y devuelve fragmentos citables [U#].",
        SearchDocumentsArgs,
        "read",
        _routes("documental", "structured", "mixed"),
        "Qdrant híbrida sobre gold/knowledge_units",
    ),
    ToolSpec(
        2,
        "query_structured",
        "Consulta datos puntuales de Manuelita y sus filiales (años, cifras, capacidades) y "
        "cuenta o lista entidades; cada dato trae su fuente [F#].",
        QueryStructuredArgs,
        "read",
        _routes("documental", "structured", "mixed"),
        "tabla SQLite estructurada derivada del oro",
    ),
    ToolSpec(
        3,
        "aggregate_series",
        "Cifras anuales curadas (ventas, EBITDA, producción…) con suma, promedio, máximo, "
        "mínimo o variación calculados en código con Decimal; cita la fuente [F#].",
        AggregateArgs,
        "read",
        _routes("documental", "structured", "mixed"),
        "data/curated/series_anuales.csv",
    ),
)

WRITE_NUMBERS = {
    "save_profile": 16,
    "save_preference": 17,
    "forget_memory": 18,
    "export_conversation": 19,
    "request_human_contact": 20,
}
WRITE_SOURCES = {
    "save_profile": 'Store ("users", id, "profile")',
    "save_preference": 'Store ("users", id, "preferences")',
    "forget_memory": "Store del usuario",
    "export_conversation": "hilo del checkpointer",
    "request_human_contact": "$MANUELITA_STATE_DIR/contacts.jsonl",
}
ALL_ROUTES = ROUTES


def _write_specs() -> tuple[ToolSpec, ...]:
    specs: list[ToolSpec] = []
    for name in WRITE_TOOLS:
        description = f"{TOOL_DESCRIPTIONS[name]}. Requiere aprobación humana antes de ejecutarse."
        specs.append(
            ToolSpec(
                WRITE_NUMBERS.get(name, 99),
                name,
                description,
                ARG_SCHEMAS[name],
                "write",
                ALL_ROUTES,
                WRITE_SOURCES.get(name, "estado del usuario"),
            )
        )
    return tuple(specs)


def _new_read_specs() -> tuple[ToolSpec, ...]:
    """Las 12 herramientas de lectura nuevas de la spec 024 (módulos ``tools_*``)."""
    specs: list[ToolSpec] = []
    for module_name in ("tools_series", "tools_entities", "tools_knowledge", "tools_utility"):
        try:
            module = __import__(f"{__package__}.{module_name}", fromlist=["SPECS"])
        except ModuleNotFoundError as exc:
            if exc.name and exc.name.endswith(module_name):
                continue  # módulo aún no implementado
            raise
        specs.extend(getattr(module, "SPECS", ()))
    return tuple(specs)


def catalog() -> tuple[ToolSpec, ...]:
    """Las herramientas del catálogo, validadas y ordenadas por número."""
    specs = sorted((*EXISTING_READ, *_new_read_specs(), *_write_specs()), key=lambda s: s.number)
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names):
        raise ValueError("nombres de herramienta repetidos en el catálogo")
    for spec in specs:
        spec.validate()
    return tuple(specs)


def get_spec(name: str) -> ToolSpec:
    for spec in catalog():
        if spec.name == name:
            return spec
    raise KeyError(name)


def read_specs() -> tuple[ToolSpec, ...]:
    return tuple(spec for spec in catalog() if spec.kind == "read")


def write_specs() -> tuple[ToolSpec, ...]:
    return tuple(spec for spec in catalog() if spec.kind == "write")


def specs_for_route(route: str | None, *, include_write: bool = True) -> tuple[ToolSpec, ...]:
    """Subconjunto que se ofrece al agente según la ruta del enrutador (research R9).

    ``direct`` no ofrece búsquedas; sin ruta conocida se ofrece todo el catálogo de lectura.
    """
    specs = catalog()
    if route in ROUTES:
        chosen = [spec for spec in specs if route in spec.routes and spec.kind == "read"]
    else:
        chosen = [spec for spec in specs if spec.kind == "read"]
    if include_write:
        chosen.extend(spec for spec in specs if spec.kind == "write")
    return tuple(chosen)


def to_json_schema() -> list[dict[str, Any]]:
    return [spec.to_dict() for spec in catalog()]


def summarize(text: str) -> str:
    """Resumen corto del resultado para la traza (≤ 200 caracteres)."""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= SUMMARY_CHARS else flat[: SUMMARY_CHARS - 1] + "…"


def run_read(spec: ToolSpec, ctx: ToolContext, args: dict[str, Any]) -> str:
    """Valida los argumentos y ejecuta una herramienta de lectura (agente o MCP)."""
    if spec.kind != "read":
        raise ToolArgsError(f"{spec.name} es de escritura y requiere aprobación humana.")
    try:
        parsed = spec.args_schema.model_validate(args)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc']) or 'argumentos'}: {error['msg']}"
            for error in exc.errors()
        )
        raise ToolArgsError(f"Argumentos inválidos para {spec.name}: {problems}") from exc
    if spec.impl is not None:
        return spec.impl(ctx, parsed)
    return _run_existing(spec.name, ctx, parsed.model_dump(exclude_none=True))


def _existing_tools(ctx: ToolContext) -> dict[str, BaseTool]:
    if ctx.retriever is None:
        raise ToolArgsError("El índice de recuperación no está disponible.")
    built = build_read_tools(
        ctx.retriever,
        ctx.store,
        ctx.trace,
        top_k=ctx.top_k,
        neutralize=ctx.neutralize,
        series=ctx.series,
        question=ctx.question,
    )
    return {tool.name: tool for tool in built}


def _run_existing(name: str, ctx: ToolContext, args: dict[str, Any]) -> str:
    return str(_existing_tools(ctx)[name].invoke(args))


def _as_tool(spec: ToolSpec, ctx: ToolContext) -> BaseTool:
    def call(**kwargs: Any) -> str:
        try:
            return run_read(spec, ctx, kwargs)
        except ToolArgsError as exc:
            return f"{TOOL_ERROR_PREFIX} {exc}"

    return StructuredTool.from_function(
        func=call, name=spec.name, description=spec.description, args_schema=spec.args_schema
    )


def build_catalog_tools(
    ctx: ToolContext,
    *,
    route: str | None = None,
    write_run: Callable[[str, dict[str, Any]], str] | None = None,
    names: Iterable[str] | None = None,
) -> Sequence[BaseTool]:
    """Herramientas LangChain del catálogo para el agente, filtradas por ruta.

    Las tres de lectura existentes conservan su fábrica (descripción con el catálogo de
    métricas); las nuevas se envuelven con :func:`run_read`. Las de escritura solo se incluyen si
    se pasa ``write_run`` (la ejecución tras la aprobación humana).
    """
    offered = specs_for_route(route, include_write=write_run is not None)
    if names is not None:
        wanted = set(names)
        offered = tuple(spec for spec in offered if spec.name in wanted)
    existing = _existing_tools(ctx) if ctx.retriever is not None else {}
    tools: list[BaseTool] = []
    for spec in offered:
        if spec.kind == "write":
            continue
        if spec.impl is None:
            if spec.name in existing:
                tools.append(existing[spec.name])
            continue
        tools.append(_as_tool(spec, ctx))
    if write_run is not None:
        offered_write = {spec.name for spec in offered if spec.kind == "write"}
        tools.extend(tool for tool in build_write_tools(write_run) if tool.name in offered_write)
    return tuple(tools)


# --- Traza de invocaciones y plan del turno (data-model §7, ítem 1.2) --------------------------

PLAN_BY_ROUTE: dict[str, tuple[str, ...]] = {
    "direct": ("responder directo, sin herramientas de búsqueda",),
    "documental": ("buscar evidencia en los documentos públicos", "responder citando [U#]"),
    "structured": (
        "consultar datos estructurados o series anuales",
        "calcular en código si la pregunta lo pide",
        "responder citando [F#]",
    ),
    "mixed": (
        "consultar la cifra (series o tabla estructurada)",
        "buscar el contexto en los documentos",
        "responder citando al menos un [F#] y un [U#]",
    ),
    "clarify": ("pedir una aclaración breve antes de buscar",),
    "out_of_scope": ("declinar con amabilidad y ofrecer un tema de Manuelita",),
}


def _brief_args(args: dict[str, Any]) -> str:
    parts = []
    for key, value in args.items():
        if value in (None, "", [], {}):
            continue
        text = str(value)
        parts.append(f"{key}={text[:40] + '…' if len(text) > 40 else text}")
    return ", ".join(parts)


def plan_steps(route: str | None, executed: Sequence[dict[str, Any]] = ()) -> list[str]:
    """Plan previsto según la ruta (sin LLM) completado con los pasos ejecutados."""
    steps = list(PLAN_BY_ROUTE.get(str(route), ("responder con la evidencia disponible",)))
    for call in executed:
        state = "" if call.get("ok", True) else " (falló)"
        steps.append(f"→ {call['name']}({_brief_args(call.get('args') or {})}){state}")
    return steps


def instrument(tools: Sequence[BaseTool], log: list[dict[str, Any]]) -> list[BaseTool]:
    """Envuelve cada herramienta para registrar nombre, argumentos, duración y resultado.

    Conserva nombre, descripción y esquema: el middleware de aprobación humana sigue
    reconociendo las de escritura por su nombre.
    """
    import time

    wrapped: list[BaseTool] = []
    for original in tools:

        def call(_tool: BaseTool = original, **kwargs: Any) -> str:
            started = time.perf_counter()
            entry: dict[str, Any] = {
                "step": len(log) + 1,
                "name": _tool.name,
                "args": {k: v for k, v in kwargs.items() if v is not None},
                "ok": True,
                "error": None,
            }
            log.append(entry)
            try:
                result = str(_tool.invoke(kwargs))
            except Exception as exc:
                entry["ok"] = False
                entry["error"] = summarize(str(exc))
                raise
            finally:
                entry["duration_ms"] = round((time.perf_counter() - started) * 1000)
            if result.startswith((TOOL_ERROR_PREFIX, "Argumentos inválidos")):
                entry["ok"] = False
                entry["error"] = summarize(result)
            entry["summary"] = summarize(result)
            return result

        wrapped.append(
            StructuredTool.from_function(
                func=call,
                name=original.name,
                description=original.description,
                args_schema=original.args_schema,  # type: ignore[arg-type]
            )
        )
    return wrapped
