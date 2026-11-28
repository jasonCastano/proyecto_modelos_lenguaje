"""Guion de stickers contra la API en modo demo (spec 034, T023, SC-001 a SC-004).

Corre ``simulate --script tests/fixtures/channels/stickers.jsonl --check`` con el backend real de
FastAPI (``TestClient``) y el modelo guionado. Usa un catálogo temporal con WebP mínimos, porque en
CI los stickers reales son punteros de Git LFS.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.agent_helpers import demo_retriever
from tests.unit.channels.test_stickers import make_catalog

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.channels import __main__ as cli
from proyecto_modelos_lenguaje.channels import bridge as bridge_module

TOKEN = "token-de-prueba-0123456789abcdef"
SCRIPT = Path(__file__).resolve().parents[1] / "fixtures" / "channels" / "stickers.jsonl"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("VALERIA_CHANNEL_TOKEN", TOKEN)
    monkeypatch.setenv("VALERIA_CHANNEL_SALT", "sal-de-prueba-0123456789")
    monkeypatch.setenv("MANUELITA_CHANNEL_MODE", "demo")
    monkeypatch.setenv("OPENCLAW_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("VALERIA_OPERATORS", raising=False)
    catalog = make_catalog(tmp_path / "catalogo")
    monkeypatch.setattr(bridge_module, "load_catalog", lambda: catalog)
    retriever = demo_retriever()
    monkeypatch.setattr(api, "_retriever", lambda _mode: retriever)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()
    yield TestClient(api.app)
    api._chat_service.cache_clear()
    api._channel_bridge.cache_clear()


def test_the_sticker_script_has_no_findings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli.httpx, "post", client.post)
    # Las revisiones de formato de la spec 029 se miden en modo real; aquí cuentan los stickers.
    monkeypatch.setattr(cli, "_check_reply", lambda _item, _payload: 0)
    args = argparse.Namespace(
        script=SCRIPT, sender="+570000000499", channel="whatsapp", timeout=30, check=True
    )
    code = cli.run_script(args, "http://127.0.0.1:8000/api/channels/messages", TOKEN)
    out = capsys.readouterr().out
    assert "sticker_mismatch" not in out and "sticker_overuse" not in out, out
    assert code == cli.EXIT_OK, out


def test_check_sticker_flags_mismatch_and_overuse() -> None:
    sent: list[str] = []
    ok = {"sticker": {"name": "valeria-hola", "path": "x", "position": "before"}}
    assert cli.check_sticker({"expected_sticker": "valeria-hola"}, ok, sent) == 0
    assert cli.check_sticker({"expected_sticker": None}, ok, sent) == 1
    assert cli.check_sticker({"expected_sticker": None}, {"sticker": None}, sent) == 0
    many = list("abcdefgh")  # spec 037: el tope es 8
    assert cli.check_sticker({"expected_sticker": "valeria-hola"}, ok, many) == 1  # noveno sticker


# --- spec 037: uso activo (T015 y T020) -------------------------------------------------------
import itertools  # noqa: E402
import json  # noqa: E402
import uuid  # noqa: E402
from datetime import UTC, datetime  # noqa: E402

ACTIVE = SCRIPT.with_name("stickers_active.jsonl")
TEXTLESS = {"valeria-pulgar"}


def _run_active(client: TestClient) -> dict[str, list[tuple[dict, dict]]]:
    rows = [json.loads(line) for line in ACTIVE.read_text(encoding="utf-8").splitlines() if line]
    by_conversation: dict[str, list[tuple[dict, dict]]] = {}
    for index, row in enumerate(rows):
        number = 10_000 + sorted({r["conversation"] for r in rows}).index(row["conversation"])
        body = {
            "channel": "whatsapp",
            "message_id": uuid.uuid4().hex,
            "sender": f"+5700000{number:05d}",  # ficticio
            "kind": "text",
            "text": row["text"],
            "received_at": datetime.now(UTC).isoformat(),
        }
        response = client.post(
            "/api/channels/messages", json=body, headers={"X-Channel-Token": TOKEN}
        )
        payload = response.json()
        by_conversation.setdefault(row["conversation"], []).append((row, payload))
        del index
    return by_conversation


def _name(payload: dict) -> str | None:
    sticker = payload.get("sticker") or {}
    return sticker.get("name") if isinstance(sticker, dict) else None


def test_spec037_active_use_meets_sc002_to_sc005(client: TestClient) -> None:
    conversations = _run_active(client)
    findings: list[str] = []
    informative = with_sticker = 0
    greeted = greeted_ok = 0
    for cid, turns in conversations.items():
        names = [_name(payload) for _row, payload in turns]
        sent = [n for n in names if n]
        first = turns[0][0]
        if "range" in first and not first["range"][0] <= len(sent) <= first["range"][1]:
            findings.append(f"{cid}: {len(sent)} stickers fuera de {first['range']}")
        if len(sent) > 8:
            findings.append(f"{cid}: {len(sent)} stickers (máximo 8)")  # SC-005
        for before, after in itertools.pairwise(names):
            if before and before == after and before not in {"valeria-pulgar", "valeria-lindo-dia"}:
                findings.append(f"{cid}: {before} repetido seguido")
        texts = [row["text"].lower() for row, _payload in turns]
        opted_out = any("sin stickers" in t for t in texts)  # FR-012: por diseño, sin stickers
        spanish = turns[0][0].get("lang", "es") == "es"  # en inglés solo cabe el pulgar (FR-011)
        farewell = any(t in {"chao", "gracias"} for t in texts)
        if texts[0] == "hola" and farewell and spanish and not opted_out:
            greeted += 1
            greeted_ok += int(len(sent) >= 2)
        for row, payload in turns:
            name = _name(payload)
            fallback = "no encontr" in " ".join(payload.get("messages") or []).lower()
            sensitive = row.get("none") or (row.get("none_if_fallback") and fallback)
            if sensitive and name:
                findings.append(f"{row['id']}: llegó {name} en un momento sensible")  # SC-004
            if row.get("english") and name and name not in TEXTLESS:
                findings.append(f"{row['id']}: sticker con texto en inglés ({name})")
            if row.get("info") and payload.get("status") == "answered":
                informative += 1
                with_sticker += int(bool(name))
    assert not findings, findings
    assert greeted and greeted_ok / greeted >= 0.8, (greeted_ok, greeted)  # SC-002
    # SC-003: al menos una de cada tres respuestas informativas lleva sticker.
    assert informative and with_sticker / informative >= 1 / 3, (with_sticker, informative)


def test_spec037_opt_out_confirms_in_one_sentence(client: TestClient) -> None:
    conversations = _run_active(client)
    _row, payload = conversations["a09"][1]
    assert "no te enviaré más stickers" in " ".join(payload.get("messages") or [])
