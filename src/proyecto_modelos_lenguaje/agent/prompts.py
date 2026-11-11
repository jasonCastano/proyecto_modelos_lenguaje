"""Prompts versionados del agente (``prompts/router.md``, ``agent.md``, ``memory_summary.md``).

Reutiliza el formato de los prompts del Módulo 1 (versión en comentario, título y seis secciones
obligatorias) sin ampliar ``tasks.VALID_TASKS``, que solo cubre Q&A, resumen y FAQ.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import PROJECT_ROOT
from ..tasks import (
    HEADING_PATTERN,
    PROMPT_VERSION_PATTERN,
    PromptTemplate,
    TaskError,
    _parse_sections,
)

AGENT_PROMPTS = ("router", "agent", "memory_summary")


def load_agent_prompt(name: str, *, project_root: Path | None = None) -> PromptTemplate:
    """Carga y valida un prompt del agente."""
    if name not in AGENT_PROMPTS:
        raise TaskError("invalid_config", f"Prompt de agente desconocido: {name}.", task=name)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    path = root / "prompts" / f"{name}.md"
    if not path.is_file():
        raise TaskError("invalid_config", f"No existe prompts/{name}.md.", task=name)
    text = path.read_text(encoding="utf-8")
    version = PROMPT_VERSION_PATTERN.search(text)
    if version is None:
        raise TaskError(
            "invalid_config", f"prompts/{name}.md no declara prompt_version.", task=name
        )
    if HEADING_PATTERN.search(text) is None:
        raise TaskError("invalid_config", f"prompts/{name}.md no tiene título.", task=name)
    return PromptTemplate(
        task=name,
        version=version.group(1),
        path=f"prompts/{name}.md",
        text=text,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        sections=_parse_sections(text, task=name),
    )
