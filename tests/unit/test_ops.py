"""Operación: sincronizar el workspace y la prueba de 3 minutos (spec 024, T050)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.ops import channel_mode, ops_check, render, workspace_sync


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
