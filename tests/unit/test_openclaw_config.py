"""Plantilla versionada de OpenClaw (spec 024, T009): endurecida y sin secretos."""

from __future__ import annotations

import re

import pytest

from proyecto_modelos_lenguaje.ops import OPENCLAW_CONFIG, load_json5, loads_json5

E164 = re.compile(r"\+[1-9]\d{7,14}")


@pytest.fixture(scope="module")
def config() -> dict:
    return load_json5(OPENCLAW_CONFIG)


def test_json5_subset() -> None:
    text = '{\n  // comentario\n  a: "http://x//y", /* bloque */ b: [1, 2,],\n}'
    assert loads_json5(text) == {"a": "http://x//y", "b": [1, 2]}


def test_gateway_is_loopback_with_token(config: dict) -> None:
    gateway = config["gateway"]
    assert gateway["bind"] == "loopback" and gateway["mode"] == "local"
    assert gateway["auth"] == {"mode": "token", "token": "${OPENCLAW_GATEWAY_TOKEN}"}


def test_cloud_model_with_fallback(config: dict) -> None:
    model = config["agents"]["defaults"]["model"]
    assert model["primary"].startswith("deepseek/") and model["fallbacks"]
    assert "ollama" not in str(config).lower()


def test_hardening(config: dict) -> None:
    tools = config["tools"]
    assert tools["fs"]["workspaceOnly"] is True
    assert {"group:runtime", "group:fs", "group:automation"} <= set(tools["deny"])
    assert tools["elevated"]["enabled"] is False
    assert config["agents"]["defaults"]["sandbox"]["mode"] == "all"


def test_whatsapp_never_in_groups(config: dict) -> None:
    whatsapp = config["channels"]["whatsapp"]
    assert whatsapp["groupPolicy"] == "disabled"
    assert whatsapp["dmPolicy"] in {"allowlist", "pairing"}
    assert all(value.startswith("${") for value in whatsapp["allowFrom"])


def test_bridge_and_mcp(config: dict) -> None:
    bridge = config["plugins"]["entries"]["valeria-bridge"]
    assert bridge["enabled"] and bridge["config"]["backendUrl"].startswith("http://127.0.0.1")
    server = config["mcp"]["servers"]["valeria-tools"]
    assert "proyecto_modelos_lenguaje.mcp_server" in server["args"]


def test_no_literal_secrets_or_numbers() -> None:
    text = OPENCLAW_CONFIG.read_text(encoding="utf-8")
    assert not E164.search(text)
    assert not re.search(r"sk-[A-Za-z0-9]{8,}|lsv2_|ghp_", text)
    for value in re.findall(r'token:\s*"([^"]*)"', text):
        assert value.startswith("${")
