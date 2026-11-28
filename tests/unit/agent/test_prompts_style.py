"""Prompts con la regla de estilo caleño (spec 036, T009 y T018)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent.prompts import load_agent_prompt, load_converse


def test_converse_prompt_has_the_caleno_style() -> None:
    converse = load_converse()
    assert converse.version == "1.2"
    assert "Estilo caleño" in converse.style and "como máximo una" in converse.style
    assert "nunca voseo" in converse.style
    assert "glosario" in converse.style
    assert "<estilo>" in converse.system


def test_agent_prompt_has_the_caleno_style() -> None:
    agent = load_agent_prompt("agent")
    assert agent.version == "1.11"
    assert "Estilo caleño" in agent.text and "<estilo>" in agent.text


def test_voice_script_prompt_has_the_spoken_style() -> None:
    voice = load_agent_prompt("voice_script")
    assert voice.version == "1.1"
    assert "<estilo>" in voice.text and "como máximo dos" in voice.text
