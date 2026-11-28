"""Operación: sincronizar el workspace y la prueba de 3 minutos (spec 024, T050)."""

from __future__ import annotations

from pathlib import Path

import pytest

import proyecto_modelos_lenguaje.ops as ops
from proyecto_modelos_lenguaje.ops import (
    channel_mode,
    lid_support,
    ops_check,
    render,
    stickers_check,
    workspace_sync,
)


def test_workspace_sync_keeps_memory(tmp_path: Path) -> None:
    source = tmp_path / "src"
    (source / "skills" / "s").mkdir(parents=True)
    (source / "SOUL.md").write_text("alma", encoding="utf-8")
    (source / "skills" / "s" / "SKILL.md").write_text("skill", encoding="utf-8")
    target = tmp_path / "workspace"
    (target / "memory").mkdir(parents=True)
    (target / "memory" / "2026-11-28.md").write_text("bitácora", encoding="utf-8")
    copied = workspace_sync(target, source)
    assert sorted(copied) == ["SOUL.md", "skills/s/SKILL.md"]
    assert (target / "memory" / "2026-11-28.md").read_text(encoding="utf-8") == "bitácora"


def _fetch_ok(url: str, headers: dict | None = None):
    if url.endswith("/api/health"):
        return 200, {"status": "ok"}
    return 200, {
        "model": {"ok": True},
        "qdrant": {"ok": True, "mode": "server"},
        "channels": {"whatsapp": {"messages_1h": 3}},
    }


GREEN = {
    "gateway": "Runtime: running\nConnectivity check: ok",
    "channels": "WhatsApp default: linked, connected",
    "mcp": "- valeria-tools: stdio",
    "security": "Summary: 0 critical · 2 warn · 5 info",
}


def _green(command: list[str]) -> tuple[int, str]:
    return 0, GREEN.get(command[1], "") if command[0] == "openclaw" else ""


def test_all_green(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("WA_DM_POLICY=allowlist\n", encoding="utf-8")
    _plugin(tmp_path, "parcheado")  # spec 033: soporte para cuentas por ID
    # Spec 034: en CI los stickers son punteros de Git LFS; aquí solo importa que el check exista.
    monkeypatch.setattr(ops, "stickers_check", lambda: ops.CheckResult("stickers", True, "9/9"))
    monkeypatch.setattr(ops, "stickers_today", lambda: ops.CheckResult("stickers-hoy", True, "0"))
    support = ops.CheckResult("soporte-sticker", True, "v1")
    monkeypatch.setattr(ops, "sticker_support", lambda: support)
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    results = ops_check(run=_green, fetch=_fetch_ok)
    assert all(result.ok for result in results)
    assert {r.name for r in results} >= {"backend", "gateway", "whatsapp", "auditoria", "git"}
    assert render(results).endswith("Todo en verde.")


def test_failures_are_reported() -> None:
    def run(command):
        return (1, "critical: 2") if command[:3] == ["openclaw", "security", "audit"] else (0, "")

    results = ops_check(run=run, fetch=lambda url, headers=None: (0, "sin conexión"))
    failed = {r.name for r in results if not r.ok}
    assert {"backend", "canal-backend", "auditoria"} <= failed
    assert "fallaron" in render(results)


# --- spec 028: el código 0 del CLI no basta (falso verde en la Fase A) ----------------------------


def test_stopped_gateway_is_red_even_with_exit_code_0() -> None:
    from proyecto_modelos_lenguaje.ops import judge_openclaw

    output = (
        "\x1b[38;2;1;1;1mRuntime:\x1b[39m stopped (no gateway listener detected)\n"
        "Connectivity check: failed\n  connect ECONNREFUSED 127.0.0.1:18790\n"
        "Support: https://community.openclaw.ai/"
    )
    result = judge_openclaw("gateway", 0, output)
    assert result.ok is False and result.detail == "detenido"


def test_running_gateway_ignores_the_openclaw_service_diagnostic() -> None:
    """El gateway de Valer-IA corre como tarea propia: «Runtime: stopped» es del servicio ajeno."""
    from proyecto_modelos_lenguaje.ops import judge_openclaw

    output = (
        "Runtime: stopped (Startup-folder login item installed; no gateway listener detected on "
        "port 18789.) (diagnostic only, not the check target)\n"
        "Check target: ws://127.0.0.1:18790\nConnectivity check: ok"
    )
    assert judge_openclaw("gateway", 0, output).ok is True


def test_whatsapp_tip_is_not_a_link() -> None:
    from proyecto_modelos_lenguaje.ops import judge_openclaw

    tip = "Tip: https://docs.openclaw.ai/cli/status adds gateway health checks."
    assert judge_openclaw("whatsapp", 0, tip).ok is False
    assert judge_openclaw("whatsapp", 0, "WhatsApp: not linked").ok is False
    assert judge_openclaw("whatsapp", 0, "WhatsApp default: linked").ok is True


def test_mcp_requires_valeria_tools() -> None:
    from proyecto_modelos_lenguaje.ops import judge_openclaw

    assert judge_openclaw("mcp", 0, "No MCP servers configured in C:/x.json5.").ok is False
    assert judge_openclaw("mcp", 0, "- valeria-tools: stdio").ok is True


def test_audit_counts_critical_findings() -> None:
    from proyecto_modelos_lenguaje.ops import judge_openclaw

    assert judge_openclaw("auditoria", 0, "Summary: 2 critical · 1 warn").detail == "2 críticos"
    assert judge_openclaw("auditoria", 0, "trust model: personal assistant").ok is True


# --- spec 031: modo del canal (T011) ---


def test_channel_mode_open_closed_and_missing(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "VALERIA_CHANNEL_TOKEN=secreto\nWA_DM_POLICY=open\nWA_ALLOW_1=*\nWA_TEST_1=+573001234567\n",
        encoding="utf-8",
    )
    opened = channel_mode(tmp_path)
    assert opened.ok and opened.detail.startswith("ABIERTO al público")
    env.write_text(
        "WA_DM_POLICY=allowlist\nWA_ALLOW_1=+573001234567\nWA_ALLOW_2=+573007654321\nWA_ALLOW_3=\n",
        encoding="utf-8",
    )
    closed = channel_mode(tmp_path)
    assert closed.ok and closed.detail == "cerrado (2 números de prueba)"
    assert not any(char.isdigit() for char in closed.detail.replace("2 números", ""))
    missing = channel_mode(tmp_path / "no-existe")
    assert not missing.ok and missing.detail == "sin .env de OpenClaw"


def test_ops_check_reports_the_channel_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("WA_DM_POLICY=open\nWA_ALLOW_1=*\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    results = ops_check(run=_green, fetch=_fetch_ok)
    mode = next(r for r in results if r.name == "modo-canal")
    assert "ABIERTO" in mode.detail and "ABIERTO" in render(results)


# --- spec 033: soporte para cuentas de WhatsApp identificadas solo por ID (T018) -----------------

THROW = 'throw new Error("WhatsApp inbound LID identity unavailable")'


def _plugin(state: Path, kind: str) -> None:
    """Instalación mínima del componente: «ausente», «parcheado» o «nativo»."""
    setup = (
        state / "npm" / "projects" / "openclaw-whatsapp-test" / "node_modules" / "@openclaw"
        / "whatsapp" / "dist" / ".setup"
    )  # fmt: skip
    setup.mkdir(parents=True, exist_ok=True)
    mark = "/* valeria-lid v1 */" if kind == "parcheado" else ""
    throw = "" if kind == "nativo" else THROW
    (setup / "monitor-x.mjs").write_text(f"const from = null; {mark}\n{throw}\n", encoding="utf-8")
    (setup / "normalize-target-x.mjs").write_text(f"const phone = 1; {mark}\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("kind", "ok", "detail"),
    [
        ("parcheado", True, "parche valeria-lid v1"),
        ("nativo", True, "nativo del componente"),
        ("ausente", False, "openclaw_env.ps1 -Install"),
    ],
)
def test_lid_support_states(tmp_path: Path, kind: str, ok: bool, detail: str) -> None:
    _plugin(tmp_path, kind)
    result = lid_support(tmp_path)
    assert result.name == "soporte-lid" and result.ok is ok and detail in result.detail


def test_lid_support_without_the_component(tmp_path: Path) -> None:
    result = lid_support(tmp_path)
    assert result.ok is False and "no instalado" in result.detail


def test_ops_check_includes_lid_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("WA_DM_POLICY=open\nWA_ALLOW_1=*\n", encoding="utf-8")
    _plugin(tmp_path, "ausente")
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path))
    results = ops_check(run=_green, fetch=_fetch_ok)
    names = [r.name for r in results]
    assert names.index("soporte-lid") == names.index("whatsapp") + 1
    assert not next(r for r in results if r.name == "soporte-lid").ok


# --- spec 034: stickers disponibles (T022) ------------------------------------------------------


def test_stickers_check_states() -> None:
    from proyecto_modelos_lenguaje.channels.stickers import StickerCatalog

    full = StickerCatalog(stickers={"a": object(), "b": object()})  # type: ignore[dict-item]
    assert stickers_check(True, full).detail == "2/2 disponibles"
    partial = StickerCatalog(stickers={"a": object()}, unavailable={"b": "archivo no encontrado"})  # type: ignore[dict-item]
    result = stickers_check(True, partial)
    assert result.ok and "1/2" in result.detail and "faltan: b" in result.detail
    assert not stickers_check(True, StickerCatalog(unavailable={"a": "x"})).ok
    assert stickers_check(False).detail == "apagados"


# --- spec 037: stickers del día (T006) ----------------------------------------------------------


def _gateway(path: Path, day: str, messages: list[str]) -> None:
    import json as _json

    path.mkdir(parents=True, exist_ok=True)
    rows = [
        _json.dumps({"0": '{"subsystem":"plugins"}', "1": m, "_meta": {"date": f"{day}T12:00:00Z"}})
        for m in messages
    ]
    (path / f"openclaw-{day}.log").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _journal(path: Path, day: str, stickers: list[str | None]) -> Path:
    import json as _json

    rows = [_json.dumps({"ts": f"{day}T10:00:00+00:00", "sticker": s}) for s in stickers]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_spec037_stickers_today_red_amber_green(tmp_path: Path) -> None:
    from proyecto_modelos_lenguaje.ops import stickers_today

    day = "2026-11-28"
    journal = _journal(tmp_path / "channels.jsonl", day, ["valeria-hola", None, "valeria-listo"])
    gateway = tmp_path / "gw"
    _gateway(
        gateway,
        day,
        [
            "valeria-bridge: sticker no enviado (valeria-hola.webp): sin-listener",
            "valeria-bridge: sticker no enviado (valeria-pensando.webp): sin-listener",
            "valeria-bridge: sin vía de stickers (compartido: sin controlador)",
        ],
    )
    red = stickers_today(journal, gateway, day)
    assert not red.ok and "elegidos 2" in red.detail and "entregados 0" in red.detail
    assert "fallidos 1 (sin-listener)" in red.detail  # «Pensando» no cuenta
    _gateway(
        gateway,
        day,
        [
            "valeria-bridge: stickers listos vía compartido",
            "valeria-bridge: sticker enviado (valeria-hola.webp) vía compartido",
        ],
    )
    amber = stickers_today(journal, gateway, day)
    assert amber.ok and amber.detail.startswith("⚠") and "vía compartido" in amber.detail
    _gateway(
        gateway,
        day,
        [
            "valeria-bridge: sticker enviado (valeria-hola.webp) vía compartido",
            "valeria-bridge: sticker enviado (valeria-listo.webp) vía compartido",
        ],
    )
    green = stickers_today(journal, gateway, day)
    assert green.ok and not green.detail.startswith("⚠")
    empty = stickers_today(_journal(tmp_path / "e.jsonl", day, []), tmp_path / "nada", day)
    assert empty.ok and "elegidos 0" in empty.detail


def test_spec037_sticker_support(tmp_path: Path) -> None:
    from proyecto_modelos_lenguaje.ops import sticker_support

    assert not sticker_support(tmp_path).ok  # sin componente
    plugin = "npm/projects/openclaw-whatsapp-x/node_modules/@openclaw/whatsapp"
    setup = tmp_path / plugin / "dist" / ".setup"
    setup.mkdir(parents=True)
    (setup / "monitor-a.mjs").write_text("sendReaction: x", encoding="utf-8")
    send = setup / "send-a.mjs"
    send.write_text("const accepted = 1;", encoding="utf-8")
    (setup / "send-api-a.mjs").write_text("/* valeria-sticker v2 */", encoding="utf-8")  # no cuenta
    missing = sticker_support(tmp_path)
    assert not missing.ok and "openclaw_env.ps1 -Install" in missing.detail
    (setup / "monitor-a.mjs").write_text("sendSticker /* valeria-sticker v2 */", "utf-8")
    assert not sticker_support(tmp_path).ok  # falta la parte de envío
    send.write_text("const valeriaSticker = 1; /* valeria-sticker v2 */", "utf-8")
    assert sticker_support(tmp_path).ok
