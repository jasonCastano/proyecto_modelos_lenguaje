"""Blindaje con el modelo real (DeepSeek): requiere red y clave (spec 015, FR-011).

Excluida por defecto y en la CI (marcador ``network``). Ejecutar en local con::

    uv run pytest -q -m network tests/integration/agent/test_shield_real.py
"""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.shield import ShieldCase, load_cases, run_shield
from proyecto_modelos_lenguaje.llm import load_llm_config

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def real_cases(tmp_path_factory) -> object:
    if not load_llm_config().api_key_present:
        pytest.skip("Falta DEEPSEEK_API_KEY")
    selected: list[ShieldCase] = [c for c in load_cases() if c.case_id in {"s01", "s06"}]
    path = tmp_path_factory.mktemp("shield") / "cases.jsonl"
    import json
    from dataclasses import asdict

    path.write_text(
        "".join(json.dumps(asdict(case), ensure_ascii=False) + "\n" for case in selected),
        encoding="utf-8",
    )
    return path


def test_real_model_ignores_embedded_instructions(real_cases) -> None:
    # Act: «ignora las instrucciones…HACKEADO» y «ignore previous instructions…PWNED»
    report = run_shield(mode="real", cases_path=real_cases, run_id="pytest-network")
    # Assert
    for result in report["results"]:
        assert result["status"] != "error", result
        assert result["obeyed"] is False, result
        assert result["leaked"] is False, result
