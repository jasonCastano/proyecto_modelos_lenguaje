"""Agente RAG con memoria y enrutador (spec 014).

Depende de ``rag`` (spec 013) y de ``tasks``; la API y la web solo consumen ``agent.graph``.
Las funciones de grafo y de la tabla estructurada se exportan aquí a medida que se implementan
sus historias.
"""

from .config import AgentConfig, AgentConfigError, load_agent_config, resolve_state_dir
from .guard import GuardedDocument, detect_instructions, render_documents
from .models import PendingAction, RouteDecision, Turn, TurnMetrics
from .router import RouterResult, route_message
from .structured import StructuredStore, build_structured_store

__all__ = [
    "AgentConfig",
    "AgentConfigError",
    "GuardedDocument",
    "PendingAction",
    "RouteDecision",
    "RouterResult",
    "StructuredStore",
    "Turn",
    "TurnMetrics",
    "build_structured_store",
    "detect_instructions",
    "load_agent_config",
    "render_documents",
    "resolve_state_dir",
    "route_message",
]
