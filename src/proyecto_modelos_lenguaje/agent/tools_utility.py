"""Herramientas utilitarias del catálogo (spec 024, herramientas 9, 14 y 15).

- ``get_official_channels``: canales oficiales por propósito. Los canales digitales (sitio, YouTube,
  Linktree, Instagram, Fundación) salen de ``config/official_channels.toml``; los de contacto por
  propósito (empleo, proveedores, clientes, prensa) de ``OFFICIAL_CONTACTS``, cada uno con la
  unidad de oro que lo publica. Nunca se inventa un correo ni un teléfono.
- ``calculate``: aritmética con ``Decimal`` sobre un AST validado (sin ``eval``): solo números,
  ``+ - * / % **`` y paréntesis; potencias acotadas y división por cero con error claro.
- ``get_my_profile``: perfil y preferencias del ``user_id`` del turno, nunca de otro usuario.
"""

from __future__ import annotations

import ast
import re
import tomllib
from dataclasses import dataclass
from decimal import Decimal, DivisionByZero, InvalidOperation, localcontext
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..config import PROJECT_ROOT
from .catalog import ToolArgsError, ToolContext, ToolSpec
from .memory import PREFERENCE_LABELS, PROFILE_LABELS, UserMemory, UserProfile
from .series import _fmt
from .structured import Citation, StructuredFact, normalize
from .tools_series import cite_facts

CHANNELS_CONFIG = PROJECT_ROOT / "config" / "official_channels.toml"
WEBSITE = "https://www.manuelita.com/"
Purpose = Literal["general", "empleo", "proveedores", "clientes", "prensa"]
PURPOSE_LABELS = {
    "general": "información general",
    "empleo": "empleo y vacantes",
    "proveedores": "proveedores",
    "clientes": "clientes y servicio al cliente",
    "prensa": "prensa y noticias",
}
PLATFORM_LABELS = {
    "fundacion_manuelita": "Sitio de la Fundación Manuelita",
    "youtube": "Canal de YouTube",
    "linktree": "Linktree (enlaces oficiales)",
    "instagram": "Instagram",
}


@dataclass(frozen=True, slots=True)
class OfficialContact:
    label: str
    url: str
    unit_id: str  # unidad de oro que publica el canal


# Propósito → canales publicados por Manuelita (verificados contra el oro en las pruebas).
OFFICIAL_CONTACTS: dict[str, tuple[OfficialContact, ...]] = {
    "general": (
        OfficialContact(
            "Sitio oficial www.manuelita.com", WEBSITE + "contacto", "unit_001300c9d792657f"
        ),
        OfficialContact(
            "Línea Ética (anónima e independiente) para reportar hechos irregulares",
            WEBSITE + "linea-etica",
            "unit_7f7df6ba16b27d13",
        ),
    ),
    "empleo": (
        OfficialContact(
            "Vacantes publicadas en www.manuelita.com/vacantes (envío de hoja de vida)",
            WEBSITE + "vacantes",
            "unit_70fa8cee05a06aa3",
        ),
    ),
    "proveedores": (
        OfficialContact(
            "Portal de Proveedores de Caña", WEBSITE + "proveedores-cana", "unit_b023bce4cb61054c"
        ),
    ),
    "clientes": (
        OfficialContact(
            "Contáctenos de Manuelita Azúcar y Línea Dulce Manuelita",
            WEBSITE + "azucar/contactenos",
            "unit_2caa0eb10be16f88",
        ),
        OfficialContact(
            "Servicio al cliente de aceites: servicioalcliente_aceites@manuelita.com",
            "https://www.manuelita.com/wp-content/uploads/2025/03/Documentos-Manuelita.pdf",
            "unit_692ab2fc6520b04b",
        ),
    ),
    "prensa": (
        OfficialContact(
            "Noticias y comunicados en www.manuelita.com/manuelita-noticias",
            "https://www.manuelita.com/manuelita-noticias/manuelita-alcanza-creditos-de-"
            "reduccion-de-emisiones-de-carbono-en-sus-operaciones-del-valle-del-cauca",
            "unit_0446a70f32d32fe1",
        ),
    ),
}


@lru_cache(maxsize=2)
def digital_channels(path: str = str(CHANNELS_CONFIG)) -> tuple[tuple[str, str], ...]:
    """(etiqueta, URL) de los canales digitales oficiales activos de la configuración."""
    source = Path(path)
    if not source.is_file():
        return ()
    table = tomllib.loads(source.read_text(encoding="utf-8"))
    channels: list[tuple[str, str]] = []
    for item in table.get("sources", []):
        if not item.get("enabled", True):
            continue
        label = PLATFORM_LABELS.get(str(item.get("id")), str(item.get("id")))
        for seed in item.get("seeds", [])[:1]:
            channels.append((label, str(seed)))
    return tuple(channels)


def purpose_for(topic: str) -> str:
    """Propósito del canal según el tema de una solicitud de contacto."""
    text = normalize(topic)
    cues = (
        ("empleo", r"\b(empleo|trabajo|vacante\w*|hoja de vida|practica\w*)\b"),
        ("proveedores", r"\b(proveedor\w*|proveer|suministr\w*)\b"),
        ("clientes", r"\b(cliente\w*|compra\w*|pedido\w*|producto\w*|reclamo\w*|queja\w*)\b"),
        ("prensa", r"\b(prensa|periodis\w*|medio\w*|entrevista\w*|comunicado\w*)\b"),
    )
    return next((name for name, cue in cues if re.search(cue, text)), "general")


def channels_text(purpose: str) -> str:
    """Canales oficiales en una línea, para respuestas sin traza (p. ej. tras una acción)."""
    contacts = OFFICIAL_CONTACTS.get(purpose) or OFFICIAL_CONTACTS["general"]
    return "; ".join(f"{contact.label} ({contact.url})" for contact in contacts)


# ---------------------------------------------------------------- 9. get_official_channels


class GetOfficialChannelsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Purpose = Field(
        default="general",
        description="general, empleo, proveedores, clientes o prensa.",
    )


def get_official_channels_impl(ctx: ToolContext, args: GetOfficialChannelsArgs) -> str:
    ctx.trace.calls += 1
    units = ctx.retriever.units_by_id if ctx.retriever is not None else {}
    facts: list[StructuredFact] = []
    for index, contact in enumerate(OFFICIAL_CONTACTS[args.purpose], start=1):
        unit = units.get(contact.unit_id)
        evidence = f" Evidencia: «{' '.join(unit.text.split())}»" if unit is not None else ""
        title = (unit.title or unit.topic_title) if unit is not None else contact.label
        facts.append(
            StructuredFact(
                fact_id=f"channel_{args.purpose}_{index}",
                subject_id="manuelita",
                subject_label="Manuelita",
                attribute=f"canal oficial para {PURPOSE_LABELS[args.purpose]}",
                value=contact.url,
                year=None,
                unit_id=contact.unit_id,
                snippet=f"{contact.label}.{evidence}",
                citations=(Citation(url=contact.url, title=title),),
            )
        )
    if args.purpose in ("general", "prensa"):
        for index, (label, url) in enumerate(digital_channels(), start=1):
            facts.append(
                StructuredFact(
                    fact_id=f"channel_digital_{index}",
                    subject_id="manuelita",
                    subject_label="Manuelita",
                    attribute="canal digital oficial (config/official_channels.toml)",
                    value=url,
                    year=None,
                    unit_id="",
                    snippet=f"{label}: {url}",
                    citations=(Citation(url=url, title=label),),
                )
            )
    header = (
        f"Canales oficiales de Manuelita para {PURPOSE_LABELS[args.purpose]}. "
        "No compartas otros correos o teléfonos distintos de estos."
    )
    return f"{header}\n{cite_facts(ctx, facts)}"


# -------------------------------------------------------------------------- 14. calculate

EXPRESSION_PATTERN = r"^[0-9.,+\-*/()% ]+$"
MAX_EXPONENT = 10
MAX_DIGITS = 30  # cifras enteras máximas de cualquier resultado intermedio
NUMBER = re.compile(r"\d[\d.,]*")
PERCENT = re.compile(r"(\d[\d.,]*)\s*%(?![\s]*[\d(])")
Operation = Literal["percent_change", "ratio", "sum"]


class CalculationError(ValueError):
    """Expresión fuera de la gramática o cálculo imposible (mensaje en español)."""


class CalculateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        pattern=EXPRESSION_PATTERN,
        description=(
            "Expresión aritmética con números, + - * / ( ) y %. «15%» es 0,15; la coma es "
            "separador decimal y, con coma, el punto es de miles (1.250,5)."
        ),
    )
    operation: Operation | None = Field(
        default=None,
        description="percent_change (de values[0] a values[1]), ratio (values[0]/values[1]) o sum.",
    )
    values: list[Decimal] | None = Field(
        default=None, min_length=1, max_length=12, description="Valores para operation."
    )

    @model_validator(mode="after")
    def one_mode(self) -> CalculateArgs:
        if (self.expression is None) == (self.operation is None):
            raise ValueError("usa exactamente uno: expression u operation con values")
        if self.expression is not None and self.values is not None:
            raise ValueError("values solo se usa con operation")
        if self.operation is not None:
            if not self.values:
                raise ValueError("operation requiere values")
            if self.operation in ("percent_change", "ratio") and len(self.values) != 2:
                raise ValueError(f"{self.operation} requiere exactamente 2 valores")
        return self


def _number(token: str) -> str:
    """Normaliza un número con coma decimal y punto de miles («1.250,5» → «1250.5»)."""
    if "," in token:
        token = token.replace(".", "").replace(",", ".")
    if token.count(".") > 1:
        raise CalculationError(f"número ambiguo: {token}")
    return token


def _prepare(expression: str) -> str:
    expression = PERCENT.sub(lambda m: f"({m.group(1)}/100)", expression)
    return NUMBER.sub(lambda m: _number(m.group(0)), expression)


def _check(value: Decimal) -> Decimal:
    if value.is_finite() and value != 0 and value.adjusted() >= MAX_DIGITS:
        raise CalculationError("el resultado es demasiado grande")
    return value


def _evaluate(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return Decimal(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd | ast.USub):
        operand = _evaluate(node.operand)
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.BinOp):
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Add):
            return _check(left + right)
        if isinstance(node.op, ast.Sub):
            return _check(left - right)
        if isinstance(node.op, ast.Mult):
            return _check(left * right)
        if isinstance(node.op, ast.Div | ast.Mod):
            if right == 0:
                raise CalculationError("división por cero")
            return _check(left / right if isinstance(node.op, ast.Div) else left % right)
        if isinstance(node.op, ast.Pow):
            if right != right.to_integral_value() or abs(right) > MAX_EXPONENT:
                raise CalculationError(f"el exponente debe ser entero y ≤ {MAX_EXPONENT}")
            if left == 0 and right < 0:
                raise CalculationError("división por cero")
            return _check(left ** int(right))
    raise CalculationError("solo se permiten números, + - * / % ** y paréntesis")


def evaluate_expression(expression: str) -> Decimal:
    """Evalúa la expresión con ``Decimal`` sobre un AST validado; nunca usa ``eval``."""
    if not re.fullmatch(EXPRESSION_PATTERN, expression):
        raise CalculationError("caracteres no permitidos en la expresión")
    try:
        tree = ast.parse(_prepare(expression).strip(), mode="eval")
    except SyntaxError as exc:
        raise CalculationError("la expresión no es aritmética válida") from exc
    with localcontext() as context:
        context.prec = 28
        context.traps[DivisionByZero] = True
        try:
            return _evaluate(tree)
        except (InvalidOperation, DivisionByZero, OverflowError) as exc:
            raise CalculationError("operación aritmética inválida") from exc


def apply_operation(operation: str, values: list[Decimal]) -> tuple[Decimal, str]:
    if operation == "sum":
        return sum(values, Decimal(0)), " + ".join(_fmt(value) for value in values)
    first, second = values
    if first == 0 and operation == "percent_change":
        raise CalculationError("no se puede calcular la variación porcentual con base 0")
    if second == 0 and operation == "ratio":
        raise CalculationError("división por cero")
    if operation == "ratio":
        return first / second, f"{_fmt(first)} / {_fmt(second)}"
    return (second - first) / first * 100, f"({_fmt(second)} − {_fmt(first)}) / {_fmt(first)} × 100"


def calculate_impl(ctx: ToolContext, args: CalculateArgs) -> str:
    ctx.trace.calls += 1
    try:
        if args.operation is not None and args.values is not None:
            result, shown = apply_operation(args.operation, args.values)
        else:
            expression = args.expression or ""
            result, shown = evaluate_expression(expression), expression.strip()
    except CalculationError as exc:
        raise ToolArgsError(f"No se pudo calcular: {exc}.") from exc
    suffix = " %" if args.operation == "percent_change" else ""
    value = f"{_fmt(result)}{suffix}"
    fact = StructuredFact(
        fact_id=f"calc_{args.operation or 'expression'}",
        subject_id="calculo",
        subject_label="Cálculo de la herramienta",
        attribute=shown,
        value=value,
        year=None,
        unit_id="",
        snippet="Resultado exacto calculado en código con Decimal (redondeado a 2 decimales).",
    )
    return cite_facts(ctx, [fact])


# ---------------------------------------------------------------------- 15. get_my_profile


class GetMyProfileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def get_my_profile_impl(ctx: ToolContext, args: GetMyProfileArgs) -> str:
    """Solo el perfil del ``user_id`` del turno; no es evidencia sobre Manuelita (sin ``F#``)."""
    ctx.trace.calls += 1
    if ctx.memory_store is None:
        return "La memoria de largo plazo no está disponible en este servidor."
    profile = UserProfile(ctx.memory_store).list(ctx.user_id)
    # El TTL lo aplica UserMemory al leer; ttl_days no interviene en la lectura.
    preferences = UserMemory(ctx.memory_store, ttl_days=1).list(ctx.user_id)
    if not profile and not preferences:
        return "Sin resultados: no tengo datos guardados de tu perfil ni preferencias."
    lines = ["Datos que guardaste (memoria de largo plazo; no son evidencia sobre Manuelita):"]
    lines += [f"- {PROFILE_LABELS[item.key]}: {item.value}" for item in profile]
    lines += [f"- {PREFERENCE_LABELS[item.key]}: {item.value}" for item in preferences]
    return "\n".join(lines)


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        9,
        "get_official_channels",
        "Canales oficiales de contacto de Manuelita según el propósito (general, empleo, "
        "proveedores, clientes o prensa), publicados en su sitio y redes; cita [F#].",
        GetOfficialChannelsArgs,
        "read",
        frozenset({"direct", "documental"}),
        "config/official_channels.toml + oro (contacto)",
        get_official_channels_impl,
    ),
    ToolSpec(
        14,
        "calculate",
        "Calculadora exacta con Decimal: una expresión aritmética (+ - * / % y paréntesis) o "
        "una operación percent_change, ratio o sum sobre valores; nunca calcules a mano [F#].",
        CalculateArgs,
        "read",
        frozenset({"structured", "mixed", "direct"}),
        "aritmética Decimal con AST seguro (sin eval)",
        calculate_impl,
    ),
    ToolSpec(
        15,
        "get_my_profile",
        "Muestra lo que el usuario guardó de sí mismo (nombre, trabajo, cargo, ciudad) y sus "
        "preferencias; solo del usuario actual.",
        GetMyProfileArgs,
        "read",
        frozenset({"direct"}),
        "SqliteStore (profile, preferences)",
        get_my_profile_impl,
    ),
)
