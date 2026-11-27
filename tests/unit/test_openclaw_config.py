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
    assert tools["exec"]["security"] == "deny"


def test_sandbox_off_only_leaves_the_mcp(config: dict) -> None:
    """Spec 028 (R12): sin virtualización no hay Docker; el agente nativo solo conserva el MCP."""
    sandbox = config["agents"]["defaults"]["sandbox"]
    assert sandbox == {"mode": "off"} and "docker" not in str(sandbox)
    deny = set(config["tools"]["deny"])
    assert {"group:openclaw", "group:ui", "group:web", "group:messaging", "group:nodes"} <= deny
    assert "group:plugins" not in deny  # el MCP valeria-tools sigue disponible


def test_voice_notes_are_transcribed_by_our_cli(config: dict) -> None:
    media = config["tools"]["media"]
    assert media["audio"]["enabled"] is True
    (model,) = media["models"]
    assert model["type"] == "cli" and model["capabilities"] == ["audio"]
    assert "proyecto_modelos_lenguaje.channels.transcribe_cli" in model["args"]
    assert "{{AttachmentPath}}" in model["args"]


def test_whatsapp_never_in_groups(config: dict) -> None:
    whatsapp = config["channels"]["whatsapp"]
    assert whatsapp["groupPolicy"] == "disabled"
    assert whatsapp["selfChatMode"] is False
    # Spec 028: el modo abierto/cerrado vive en el .env externo, nunca en el archivo versionado.
    assert whatsapp["dmPolicy"] == "${WA_DM_POLICY}"
    assert all(value.startswith("${") for value in whatsapp["allowFrom"])


def test_bridge_timeout_covers_queue_and_voice(config: dict) -> None:
    bridge = config["plugins"]["entries"]["valeria-bridge"]
    assert bridge["config"]["timeoutMs"] == 90000


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


def test_env_example_documents_the_access_modes() -> None:
    """Spec 028 (T038): modo cerrado por defecto, sin números reales."""
    example = (OPENCLAW_CONFIG.parent / ".env.example").read_text(encoding="utf-8")
    assert "WA_DM_POLICY=allowlist" in example and "WA_TEST_1=" in example
    assert not E164.search(example.replace("+57XXXXXXXXXX", ""))
