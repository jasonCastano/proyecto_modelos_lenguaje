"""``pml channels simulate --profile`` (spec 025, T049)."""

from __future__ import annotations

from typing import Any

import pytest

from proyecto_modelos_lenguaje.channels import __main__ as cli


class FakeResponse:
    status_code = 200
    content = b"{}"

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_profile_is_sent_before_the_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange
    sent: list[dict[str, Any]] = []

    def fake_post(url: str, json: dict[str, Any], **_: Any) -> FakeResponse:
        sent.append(json)
        return FakeResponse({"status": "answered", "messages": ["ok"]})

    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", "token-de-prueba")
    monkeypatch.setattr(cli.httpx, "post", fake_post)

    # Act
    code = cli.main(
        [
            "simulate",
            "--sender",
            "+570000000001",
            "--profile",
            "planificador",
            "--text",
            "Tenemos 15 % menos caña esta semana",
        ]
    )

    # Assert
    assert code == 0
    assert [body["text"] for body in sent] == [
        "/perfil planificador",
        "Tenemos 15 % menos caña esta semana",
    ]
    assert sent[0]["sender"] == sent[1]["sender"]
    assert '"status": "answered"' in capsys.readouterr().out


def test_without_profile_sends_one_message(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict[str, Any]] = []
    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", "token-de-prueba")
    monkeypatch.setattr(
        cli.httpx, "post", lambda url, json, **_: sent.append(json) or FakeResponse({})
    )
    assert cli.main(["simulate", "--sender", "+570000000001", "--text", "hola"]) == 0
    assert len(sent) == 1
