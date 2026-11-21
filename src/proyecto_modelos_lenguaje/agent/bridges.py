"""Puentes medidos hacia temas de Manuelita (spec 020, R5 y ``data-model.md`` §3).

Tres pasos:

1. **Elegibilidad** (``eligible``): reglas sobre el plan y la memoria del hilo (cuota, emoción,
   cierre, rechazo).
2. **Candidatos** (``candidates``): búsqueda en el oro con el tema del visitante ampliado por el
   mapa de ángulos de ``prompts/care.md`` (``angles.<tema>``), más los puentes curados.
3. **Selección** (``select``): sin repetir unidad ni ángulo en el hilo mientras queden ángulos.

El puente es opcional: el plan lo permite y el modelo decide si lo usa.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..rag.hybrid import HybridRetriever
from .config import ConversationConfig
from .plan import UPSET, BridgeChoice
from .prompts import CarePlaybook
from .structured import normalize
from .tools import search_documents_impl

BRIDGE_ACTS = frozenset({"off_topic", "smalltalk"})
NO_BRIDGE_ACTS = frozenset({"closing", "minimal", "complaint"})
EXCERPT_CHARS = 300
CANDIDATES_TOP_K = 6

__all__ = ["BridgeChoice", "angle_for", "candidates", "eligible", "select"]


def eligible(
    act: str,
    sentiment: str,
    memory: Mapping[str, Any] | None,
    config: ConversationConfig,
    *,
    reason: str | None = None,
) -> bool:
    """¿Se permite un puente en este turno? (FR-012, FR-013)."""
    memory = memory or {}
    if act in NO_BRIDGE_ACTS or act not in BRIDGE_ACTS:
        return False
    if reason == "unattainable":
        return False  # se ofrece el canal oficial, no un tema
    if sentiment in UPSET:
        return False
    if memory.get("bridge_rejected_at") is not None and not memory.get("interest_after_rejection"):
        return False
    if memory.get("last_bridge_turn") is None:
        return True
    return int(memory.get("offtopic_since_bridge") or 0) >= config.bridge_every - 1


def angle_for(playbook: CarePlaybook, topic_key: str | None) -> tuple[str, tuple[str, ...]]:
    """Ángulo y palabras clave del tema (``angles.<tema>``; si no hay, ``angles.default``)."""
    entry = playbook.angles.get(topic_key or "") or playbook.angles.get("default")
    if entry is None:
        return "otro", ()
    return entry.angle, entry.keywords


def _excerpt(text: str) -> str:
    clean = " ".join(text.split())
    if len(clean) <= EXCERPT_CHARS:
        return clean
    return clean[:EXCERPT_CHARS].rsplit(" ", 1)[0] + "…"


def _mentions_angle(text: str, keywords: Sequence[str]) -> bool:
    """El candidato debe tocar el ángulo: alguna palabra clave (por su raíz) en título o texto."""
    normalized = normalize(text)
    return any(normalize(k)[:5] in normalized for k in keywords if len(k) >= 4)


def clean_title(raw: str) -> str | None:
    """Título legible para mencionar el puente; los títulos de PDF en mayúsculas se descartan."""
    title = " ".join(str(raw or "").split())
    title = title.lstrip("0123456789.-) ").strip()  # «01 Informe Manuelita» → «Informe…»
    letters = [ch for ch in title if ch.isalpha()]
    if not letters or len(title) > 90:
        return None
    if sum(ch.isupper() for ch in letters) / len(letters) > 0.6:
        return None
    return title


def _curated(playbook: CarePlaybook, topic_key: str | None) -> list[BridgeChoice]:
    """Puentes curados de ``care.md``: primero el del tema, después los demás."""
    keys = [key for key in playbook.citations if key.startswith("bridge.")]
    own = f"bridge.{topic_key}" if topic_key else None
    ordered = ([own] if own in keys else []) + [key for key in keys if key != own]
    choices: list[BridgeChoice] = []
    for key in ordered:
        citation = playbook.citations[key]
        angle, _keywords = angle_for(playbook, key.removeprefix("bridge."))
        choices.append(
            BridgeChoice(
                unit_id=citation.unit_id,
                angle=angle,
                title=citation.title,
                url=citation.url,
                text=playbook.variants[key][0],
                source="curated",
                score=0.0,
                key=key,
            )
        )
    return choices


def candidates(
    topic_text: str,
    topic_key: str | None,
    playbook: CarePlaybook,
    retriever: HybridRetriever | None,
    config: ConversationConfig,
) -> list[BridgeChoice]:
    """Candidatos relacionados con lo que dijo el visitante: buscados en el oro y curados."""
    angle, keywords = angle_for(playbook, topic_key)
    found: list[BridgeChoice] = []
    if retriever is not None and keywords:
        query = f"Manuelita {' '.join(keywords)} {topic_text}".strip()[:300]
        try:
            fragments, documents = search_documents_impl(
                retriever, query, top_k=CANDIDATES_TOP_K, neutralize=True
            )
        except Exception:  # el puente es opcional: un fallo del índice no rompe el turno
            fragments, documents = [], []
        for fragment, document in zip(fragments, documents, strict=False):
            if fragment.score < config.bridge_min_score or fragment.anomalous:
                continue
            text = _excerpt(document.text)
            title = clean_title(fragment.title)
            if not text or not title or not _mentions_angle(f"{title} {text}", keywords):
                continue
            found.append(
                BridgeChoice(
                    unit_id=fragment.unit_id,
                    angle=angle,
                    title=title,
                    url=fragment.url,
                    text=text,
                    source="retrieval",
                    score=round(float(fragment.score), 4),
                )
            )
    return [*found, *_curated(playbook, topic_key)]


def select(
    options: Sequence[BridgeChoice], memory: Mapping[str, Any] | None
) -> BridgeChoice | None:
    """Mejor candidato sin repetir unidad ni ángulo del hilo (FR-015)."""
    offered = list((memory or {}).get("bridges_offered") or [])
    units = {str(item.get("unit_id")) for item in offered}
    angles = {str(item.get("angle")) for item in offered}
    fresh = [option for option in options if option.unit_id not in units]
    for option in fresh:
        if option.angle not in angles:
            return option
    all_angles = {option.angle for option in options}
    if all_angles <= angles and fresh:
        # Todos los ángulos ya se ofrecieron: se permite repetir ángulo, nunca la unidad.
        return fresh[0]
    return None


def topic_of(signals: Mapping[str, Any] | None) -> tuple[str, str | None]:
    """Texto y clave del tema del visitante (partes externas o sociales) para buscar el puente."""
    parts = list((signals or {}).get("requests") or [])
    chosen = [p for p in parts if p.get("tier") in {"external", "social"}] or parts
    keys = [str(p["topic_key"]) for p in chosen if p.get("topic_key")]
    text = " ".join(str(p.get("text") or "") for p in chosen)
    key = keys[0] if keys else _guess_key(text)
    return text, key


SOCIAL_KEYS = {
    "calor": "clima",
    "frio": "clima",
    "sol": "clima",
    "lluvia": "clima",
    "estudi": "tareas",
    "tarea": "tareas",
    "clase": "tareas",
    "trabaj": "otras_empresas",
    "cocin": "cocina",
    "comida": "cocina",
    "dulce": "cocina",
    "viaj": "viajes",
    "music": "entretenimiento",
    "pelicul": "entretenimiento",
    "futbol": "deportes",
    "partido": "deportes",
    "energ": "energia",
}


def _guess_key(text: str) -> str | None:
    normalized = normalize(text)
    for stem, key in SOCIAL_KEYS.items():
        if stem in normalized:
            return key
    return None
