"""Juez LLM propio con las definiciones de Ragas (spec 014, T067).

Ragas no instala en Python 3.14 (``research.md`` §12: ``ragas`` 0.4.3 exige ``scikit-network``, sin
wheel para 3.14). Se implementan las mismas métricas:

- ``faithfulness`` y ``answer_relevancy`` con un juez LLM (``prompts/judge.md``, DeepSeek a
  temperatura 0);
- ``context_precision`` con referencia, sin LLM: precisión media en las posiciones relevantes del
  ranking, con las unidades esperadas del conjunto como referencia (misma fórmula que Ragas).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from .prompts import load_agent_prompt

JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True, slots=True)
class JudgeScores:
    faithfulness: float
    answer_relevancy: float
    claims: int = 0
    supported: int = 0
    unsupported: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "faithfulness": self.faithfulness,
            "answer_relevancy": self.answer_relevancy,
            "claims": self.claims,
            "supported": self.supported,
            "unsupported": list(self.unsupported),
        }


def _clip(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except TypeError, ValueError:
        return 0.0


def parse_judgement(text: str) -> JudgeScores:
    """Lee el JSON del juez; recalcula la fidelidad desde los conteos si vienen."""
    match = JSON_OBJECT.search(text or "")
    if match is None:
        raise ValueError("el juez no devolvió JSON")
    payload = json.loads(match.group(0))
    claims = int(payload.get("claims") or 0)
    supported = min(int(payload.get("supported") or 0), claims) if claims else 0
    faithfulness = supported / claims if claims else _clip(payload.get("faithfulness", 1.0))
    return JudgeScores(
        faithfulness=round(faithfulness, 4),
        answer_relevancy=round(_clip(payload.get("answer_relevancy")), 4),
        claims=claims,
        supported=supported,
        unsupported=tuple(str(item) for item in payload.get("unsupported") or ())[:10],
    )


def judge_answer(
    question: str, answer: str, contexts: Sequence[str], model: BaseChatModel
) -> JudgeScores | None:
    """Califica una respuesta; ``None`` si el juez falla (la respuesta no cuenta en el promedio)."""
    prompt = load_agent_prompt("judge").render(
        question=question, contexts="\n\n".join(contexts) or "(vacío)", answer=answer
    )
    bound = model.bind(temperature=0.0) if hasattr(model, "temperature") else model
    try:
        response = bound.invoke([HumanMessage(content=prompt)])
        return parse_judgement(str(response.content))
    except ValueError, json.JSONDecodeError:
        return None


def context_precision(retrieved: Sequence[str], relevant: Sequence[str]) -> float:
    """Precisión de contexto con referencia: promedio de precisión@k en cada posición relevante."""
    expected = set(relevant)
    hits = 0
    total = 0.0
    for rank, unit_id in enumerate(retrieved, start=1):
        if unit_id in expected:
            hits += 1
            total += hits / rank
    return total / hits if hits else 0.0
