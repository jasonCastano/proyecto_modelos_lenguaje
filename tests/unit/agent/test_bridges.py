"""Puentes medidos (spec 020, R5 y ``data-model.md`` §3)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent import bridges
from proyecto_modelos_lenguaje.agent.config import ConversationConfig
from proyecto_modelos_lenguaje.agent.plan import BridgeChoice
from proyecto_modelos_lenguaje.agent.prompts import load_care
from tests.agent_helpers import demo_retriever

CONFIG = ConversationConfig()


def choice(unit: str, angle: str) -> BridgeChoice:
    return BridgeChoice(unit, angle, "Título", "https://x", "texto", "curated")


@pytest.mark.parametrize("sentiment", ["frustrated", "angry", "distressed"])
def test_no_bridge_when_upset(sentiment: str) -> None:
    assert not bridges.eligible("off_topic", sentiment, {}, CONFIG)


@pytest.mark.parametrize("act", ["closing", "minimal", "complaint", "greeting", "manuelita"])
def test_no_bridge_for_these_acts(act: str) -> None:
    assert not bridges.eligible(act, "neutral", {}, CONFIG)


def test_quota_rejection_and_renewed_interest() -> None:
    assert bridges.eligible("off_topic", "neutral", {}, CONFIG)
    just_bridged = {"last_bridge_turn": 3, "offtopic_since_bridge": 0}
    assert not bridges.eligible("off_topic", "neutral", just_bridged, CONFIG)
    one_later = {"last_bridge_turn": 3, "offtopic_since_bridge": 1}
    assert bridges.eligible("smalltalk", "neutral", one_later, CONFIG)
    rejected = {"bridge_rejected_at": 4, "interest_after_rejection": False}
    assert not bridges.eligible("off_topic", "neutral", rejected, CONFIG)
    assert bridges.eligible(
        "off_topic", "neutral", {**rejected, "interest_after_rejection": True}, CONFIG
    )
    assert not bridges.eligible("off_topic", "neutral", {}, CONFIG, reason="unattainable")


def test_curated_candidates_start_with_the_topic_bridge() -> None:
    playbook = load_care()
    options = bridges.candidates("¿cómo estará el clima?", "clima", playbook, None, CONFIG)
    assert options[0].key == "bridge.clima" and options[0].angle == "agua"
    assert all(option.source == "curated" for option in options)


def test_retrieval_candidates_need_the_angle_and_a_minimum_score() -> None:
    playbook = load_care()
    retriever = demo_retriever()
    found = bridges.candidates("qué calor", "clima", playbook, retriever, CONFIG)
    retrieved = [o for o in found if o.source == "retrieval"]
    assert all(o.score >= CONFIG.bridge_min_score and len(o.text) <= 301 for o in retrieved)
    strict = ConversationConfig(bridge_min_score=1.0)
    assert all(
        o.source == "curated"
        for o in bridges.candidates("qué calor", "clima", playbook, retriever, strict)
    )


def test_select_never_repeats_unit_or_angle() -> None:
    options = [choice("u1", "agua"), choice("u2", "agua"), choice("u3", "historia")]
    memory = {"bridges_offered": [{"unit_id": "u1", "angle": "agua", "turn": 1}]}
    assert bridges.select(options, memory).unit_id == "u3"
    memory["bridges_offered"].append({"unit_id": "u3", "angle": "historia", "turn": 3})
    # Todos los ángulos ya se ofrecieron: se permite repetir ángulo, nunca la unidad.
    assert bridges.select(options, memory).unit_id == "u2"
    memory["bridges_offered"].append({"unit_id": "u2", "angle": "agua", "turn": 5})
    assert bridges.select(options, memory) is None


def test_clean_title_discards_pdf_headings() -> None:
    assert bridges.clean_title("INFORME DE\n2021·2022\nSOSTENIBILIDAD") is None
    assert bridges.clean_title("Dulce  historia") == "Dulce historia"


def test_social_topics_guess_a_key() -> None:
    signals = {"requests": [{"text": "qué calor hace", "tier": "social", "topic_key": None}]}
    assert bridges.topic_of(signals) == ("qué calor hace", "clima")
