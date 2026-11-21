"""Pruebas offline del gatekeeper Jev (spec 021): configuración, cliente, simulación y señales."""

from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from proyecto_modelos_lenguaje.agent.config import (
    AgentConfigError,
    JevConfig,
    jev_config,
    load_agent_config,
)
from proyecto_modelos_lenguaje.agent.jev import (
    ROUTES,
    FakeJevGate,
    GateOutcome,
    GateSignals,
    TypeSafeJevGate,
    build_gate,
    build_state,
    fake_outcome,
    health_check,
    load_gate_prompts,
    merge_signals,
)

KEY = "sk-prueba-0123456789"
CONFIG = JevConfig(enabled=True)


# ---------------------------------------------------------------- configuración (T008)


def test_jev_config_defaults_are_disabled_and_pinned() -> None:
    config = jev_config(None, environ={})
    assert config.enabled is False
    assert config.model == "jev-1.14.0"
    assert config.route_threshold == 0.75
    assert config.signals == ("route", "scope", "annoyance", "crisis")


def test_repository_config_loads_the_jev_section() -> None:
    config = load_agent_config().jev
    assert config.model.startswith("jev-") and not config.model.endswith("latest")


@pytest.mark.parametrize(
    ("section", "message"),
    [
        ({"base_url": "http://api.typesafe.ai"}, "https://"),
        ({"base_url": "https://api.typesafe.ai/"}, "https://"),
        ({"model": "jev-latest"}, "versión fija"),
        ({"model": ""}, "no vacío"),
        ({"route_threshold": 0.4}, "route_threshold"),
        ({"route_threshold": 1.2}, "route_threshold"),
        ({"crisis_threshold": 0.05}, "crisis_threshold"),
        ({"crisis_threshold": 0.95}, "crisis_threshold"),
        ({"timeout_seconds": 0.1}, "timeout_seconds"),
        ({"timeout_seconds": 11}, "timeout_seconds"),
        ({"max_input_chars": 100}, "max_input_chars"),
        ({"max_input_chars": 40_000}, "max_input_chars"),
        ({"signals": ["crisis"]}, "route"),
        ({"signals": ["route", "magia"]}, "desconocidas"),
        ({"enabled": "sí"}, "booleano"),
    ],
)
def test_jev_config_rejects_out_of_range(section: dict, message: str) -> None:
    with pytest.raises(AgentConfigError, match=message):
        jev_config(section, environ={})


@pytest.mark.parametrize(("value", "expected"), [("1", True), ("true", True), ("0", False)])
def test_env_var_overrides_enabled(value: str, expected: bool) -> None:
    section = {"enabled": not expected}
    assert jev_config(section, environ={"MANUELITA_JEV_ENABLED": value}).enabled is expected


def test_signals_keep_canonical_order() -> None:
    assert jev_config({"signals": ["crisis", "route"]}, environ={}).signals == ("route", "crisis")


# ---------------------------------------------------------------- cliente HTTP (T012)


def _answers(route: str = "documental", p: float = 0.9, **extra: object) -> dict:
    rest = round((1 - p) / 5, 6)
    probabilities = {key: (p if key == route else rest) for key in ROUTES}
    probabilities[route] = round(1 - rest * 5, 6)
    answers: dict = {"route": {"type": "choice", "choice": route, "probabilities": probabilities}}
    answers.update(extra)
    return {"model": "jev-1.14.0", "answers": answers, "usage": {"input_tokens": 1000}}


def _gate(handler, config: JevConfig = CONFIG) -> tuple[TypeSafeJevGate, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return TypeSafeJevGate(config, KEY, transport=httpx.MockTransport(wrapped)), seen


def test_request_body_follows_the_contract() -> None:
    gate, seen = _gate(lambda request: httpx.Response(200, json=_answers()))
    outcome = gate.assess("¿Qué produce Manuelita?", ["Hola"])

    assert outcome.status == "ok"
    request = seen[0]
    assert request.url.path == "/v1/systemone"
    assert request.headers["Authorization"] == f"Bearer {KEY}"
    body = json.loads(request.content)
    assert body["model"] == "jev-1.14.0"
    assert body["state"] == {"mensaje": "¿Qué produce Manuelita?", "historial": ["Hola"]}
    assert set(body["questions"]) == {"route", "scope", "annoyance", "crisis"}
    assert body["questions"]["route"]["type"] == "choice"
    assert set(body["questions"]["route"]["criteria"]) == set(ROUTES)
    assert body["questions"]["annoyance"]["type"] == "score"
    assert len(body["questions"]["annoyance"]["criteria"]) == 4
    assert body["questions"]["crisis"]["type"] == "noul"


def test_only_configured_signals_are_asked() -> None:
    config = replace(CONFIG, signals=("route",))
    gate, seen = _gate(lambda request: httpx.Response(200, json=_answers()), config)
    gate.assess("¿Qué produce Manuelita?")
    assert set(json.loads(seen[0].content)["questions"]) == {"route"}


def test_personal_data_is_masked_before_leaving() -> None:
    gate, seen = _gate(lambda request: httpx.Response(200, json=_answers()))
    gate.assess("Soy ana@correo.com, mi celular es 3001234567", ["mi cédula 1234567890"])
    sent = seen[0].content.decode("utf-8")
    assert "ana@correo.com" not in sent and "3001234567" not in sent


def test_history_is_trimmed_before_the_message() -> None:
    state = build_state("m" * 400, ["a" * 300, "b" * 300], max_chars=900)
    assert state["mensaje"] == "m" * 400
    assert state["historial"] == ["b" * 300]


def test_valid_response_gives_confidence_alternative_and_signals() -> None:
    payload = _answers(
        "out_of_scope",
        0.8,
        scope={
            "type": "choice",
            "choice": "advice",
            "probabilities": {
                "off_topic": 0.1,
                "abuse": 0,
                "harmful": 0,
                "third_party": 0,
                "prompt_extraction": 0,
                "advice": 0.9,
            },
        },
        annoyance={
            "type": "score",
            "score": 2.05,
            "probabilities": {"0": 0, "1": 0, "2": 0.95, "3": 0.05},
        },
        crisis={"type": "noul", "noul": 0.03},
    )
    payload["answers"]["route"]["probabilities"]["clarify"] = 0.08
    payload["answers"]["route"]["probabilities"]["direct"] = 0.0
    payload["answers"]["route"]["probabilities"]["documental"] = 0.04
    payload["answers"]["route"]["probabilities"]["structured"] = 0.04
    payload["answers"]["route"]["probabilities"]["mixed"] = 0.04
    gate, _ = _gate(lambda request: httpx.Response(200, json=payload))

    outcome = gate.assess("¿En qué acciones invierto?")

    assert outcome.status == "ok" and outcome.decision is not None
    assert outcome.decision.route == "out_of_scope"
    assert outcome.decision.confidence == pytest.approx(0.8)
    assert outcome.decision.alternative == "clarify"
    assert outcome.decision.scope_reason == "advice"
    assert outcome.signals == GateSignals(crisis_probability=0.03, annoyance=2.05)
    assert outcome.cost == pytest.approx(1000 * 0.042 / 1_000_000)
    assert outcome.model == "jev-1.14.0"


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (httpx.Response(401, json={}), "http_401"),
        (httpx.Response(402, json={}), "http_402"),
        (httpx.Response(422, json={}), "http_422"),
        (httpx.Response(429, json={}), "http_429"),
        (httpx.Response(503, json={}), "http_5xx"),
        (httpx.Response(200, json={"model": "x"}), "invalid_response"),
        (httpx.Response(200, text="no es json"), "invalid_response"),
        (httpx.Response(200, json={"answers": {"route": {"type": "refusal"}}}), "refusal"),
        (
            httpx.Response(
                200,
                json={
                    "answers": {
                        "route": {
                            "type": "choice",
                            "choice": "magia",
                            "probabilities": {"magia": 1.0},
                        }
                    }
                },
            ),
            "invalid_response",
        ),
        (
            httpx.Response(
                200,
                json={
                    "answers": {
                        "route": {
                            "type": "choice",
                            "choice": "direct",
                            "probabilities": {route: 0.5 for route in ROUTES},
                        }
                    }
                },
            ),
            "invalid_response",
        ),
    ],
)
def test_every_failure_becomes_a_failed_outcome(response: httpx.Response, reason: str) -> None:
    gate, _ = _gate(lambda request: response)
    outcome = gate.assess("¿Qué produce Manuelita?")
    assert outcome.status == "failed" and outcome.reason == reason
    assert outcome.decision is None


@pytest.mark.parametrize(
    ("error", "reason"),
    [(httpx.ReadTimeout("lento"), "timeout"), (httpx.ConnectError("sin red"), "network")],
)
def test_transport_errors_never_escape(error: Exception, reason: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    gate, _ = _gate(handler)
    assert gate.assess("hola").reason == reason


def test_the_key_never_appears_in_repr_or_outcomes() -> None:
    gate, _ = _gate(lambda request: httpx.Response(401, json={"error": "bad key"}))
    outcome = gate.assess("¿Qué produce Manuelita?")
    assert KEY not in repr(gate)
    assert KEY not in outcome.model_dump_json()
    assert KEY not in json.dumps(outcome.trace(0.75))


# ---------------------------------------------------------------- construcción y simulación


def test_build_gate_without_key_or_disabled_returns_none() -> None:
    assert build_gate(JevConfig(enabled=False), environ={"TYPESAFE_API_KEY": KEY}) is None
    assert build_gate(CONFIG, environ={}) is None
    assert isinstance(build_gate(CONFIG, environ={"TYPESAFE_API_KEY": KEY}), TypeSafeJevGate)
    assert isinstance(build_gate(CONFIG, demo=True, environ={}), FakeJevGate)


def test_fake_gate_is_deterministic_and_offline() -> None:
    gate = FakeJevGate(CONFIG)
    first = gate.assess("¿En qué año se fundó Manuelita?")
    assert first == gate.assess("¿En qué año se fundó Manuelita?")
    assert first.decision is not None and first.decision.route == "structured"
    assert sum(first.decision.probabilities.values()) == pytest.approx(1.0)


def test_prompts_have_the_four_questions_with_exact_options() -> None:
    prompts = load_gate_prompts()
    assert [key for key, _ in prompts.questions["route"].options] == list(ROUTES)
    assert [key for key, _ in prompts.questions["annoyance"].options] == [
        "calmado",
        "inconforme",
        "molesto",
        "muy molesto",
    ]


def test_health_check_without_key_is_actionable() -> None:
    result = health_check(CONFIG, environ={})
    assert result["ok"] is False and "TYPESAFE_API_KEY" in result["detail"]


def test_health_check_confirms_a_pinned_version_missing_from_the_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "jev-latest"}]})
        return httpx.Response(200, json={"model": "jev-1.14.0", "answers": {}})

    result = health_check(
        CONFIG, environ={"TYPESAFE_API_KEY": KEY}, transport=httpx.MockTransport(handler)
    )
    assert result["ok"] is True and KEY not in json.dumps(result)


# ---------------------------------------------------------------- señales de atención (T029)


def test_crisis_is_the_union_and_jev_never_removes_it() -> None:
    regex_crisis = {"crisis": True, "sentiment": "distressed"}
    calm = fake_outcome("out_of_scope", 0.9, crisis=0.01)
    assert merge_signals(regex_crisis, calm, CONFIG)["crisis"] is True

    no_regex = {"crisis": False, "sentiment": "neutral"}
    risky = fake_outcome("direct", 0.9, crisis=0.7)
    merged = merge_signals(no_regex, risky, CONFIG)
    assert merged["crisis"] is True and merged["jev_crisis"] is True

    low = fake_outcome("direct", 0.9, crisis=0.2)
    assert merge_signals(no_regex, low, CONFIG)["crisis"] is False


@pytest.mark.parametrize(
    ("annoyance", "before", "after"),
    [
        (2.0, "neutral", "frustrated"),
        (3.0, "neutral", "angry"),
        (3.0, "distressed", "distressed"),
        (2.0, "angry", "angry"),
        (1.0, "neutral", "neutral"),
    ],
)
def test_annoyance_only_intensifies(annoyance: float, before: str, after: str) -> None:
    outcome = fake_outcome("documental", 0.9, annoyance=annoyance)
    merged = merge_signals({"sentiment": before, "crisis": False}, outcome, CONFIG)
    assert merged["sentiment"] == after


def test_disabled_signals_and_failures_leave_signals_untouched() -> None:
    signals = {"sentiment": "neutral", "crisis": False}
    only_route = replace(CONFIG, signals=("route",))
    outcome = fake_outcome("direct", 0.9, crisis=0.99, annoyance=3.0)
    assert merge_signals(signals, outcome, only_route) == signals
    failed = GateOutcome(status="failed", reason="timeout")
    assert merge_signals(signals, failed, CONFIG) == signals
    assert merge_signals(None, outcome, CONFIG) is None
