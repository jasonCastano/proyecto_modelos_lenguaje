"""Memoria de enfoque y temas sugeridos (spec 035, ``contracts/focus-rules.md`` §3)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent import care
from proyecto_modelos_lenguaje.agent.prompts import load_care

DECISION = {"route": "direct", "confidence": 0.9, "reason": "x"}


def update(memory: care.ConversationMemory, act: str, turn: int, **kwargs) -> None:
    care.update_conversation(
        memory,
        message="mensaje",
        signals=None,
        decision=DECISION,
        act=act,
        turn=turn,
        bridged=None,
        **kwargs,
    )


def test_playbook_loads_the_offer_topics() -> None:
    topics = load_care().topics
    assert 4 <= len(topics) <= 10
    assert {"historia", "productos", "fundacion"} <= set(topics)
    starts = ("sus", "su ", "la ", "los ")
    assert all("Manuelita" in text or text.startswith(starts) for text in topics.values())


def test_streak_follows_the_plan_and_resets() -> None:
    memory = care.empty_conversation()
    assert memory["offtopic_streak"] == 0 and memory["offered_topics"] == []
    update(memory, "smalltalk", 1, streak=1)
    update(memory, "off_topic", 2, streak=2)
    assert memory["offtopic_streak"] == 2
    update(memory, "manuelita", 3, streak=0)
    assert memory["offtopic_streak"] == 0


@pytest.mark.parametrize("act", ["manuelita", "clarify", "about_assistant", "thanks", "closing"])
def test_non_focus_acts_reset_the_streak(act: str) -> None:
    memory = care.empty_conversation()
    update(memory, "smalltalk", 1, streak=3)
    update(memory, act, 2, streak=0)
    assert memory["offtopic_streak"] == 0


def test_offered_topics_accumulate_without_duplicates_and_reset() -> None:
    memory = care.empty_conversation()
    update(memory, "smalltalk", 1, streak=1, offered=("historia", "energia"))
    update(memory, "smalltalk", 2, streak=2, offered=("energia", "paises"))
    assert memory["offered_topics"] == ["historia", "energia", "paises"]
    for turn, key in enumerate(("a", "b", "c", "d", "e"), start=3):
        update(memory, "smalltalk", turn, streak=turn, offered=(key,))
    assert len(memory["offered_topics"]) <= care.MAX_OFFERED_TOPICS


def test_copy_keeps_the_focus_memory() -> None:
    memory = care.empty_conversation()
    update(memory, "smalltalk", 1, streak=1, offered=("historia",))
    copied = care.copy_conversation(memory)
    assert copied["offtopic_streak"] == 1 and copied["offered_topics"] == ["historia"]
    assert care.copy_conversation(None)["offered_topics"] == []


def test_pick_topics_skips_offered_ones_and_rotates() -> None:
    playbook = load_care()
    keys = list(playbook.topics)
    first = care.pick_topics(playbook, [])
    assert first == tuple(keys[:3])
    second = care.pick_topics(playbook, list(first))
    assert not set(first) & set(second)
    almost_all = care.pick_topics(playbook, keys[:-1])
    assert almost_all[0] == keys[-1] and len(almost_all) == 3


def test_topics_offer_is_short_and_has_no_numbers() -> None:
    playbook = load_care()
    for seed in range(6):
        text = care.topics_offer(playbook, ("historia", "productos"), seed=seed)
        assert "Manuelita" in text and not any(ch.isdigit() for ch in text)
        assert len(text) < 130
    assert "Manuelita" in care.topics_offer(playbook, (), language="en")
