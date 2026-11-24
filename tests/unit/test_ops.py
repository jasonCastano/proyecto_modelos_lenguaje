"""Operación: sincronizar el workspace y la prueba de 3 minutos (spec 024, T050)."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.ops import ops_check, render, workspace_sync


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


def test_all_green() -> None:
    results = ops_check(run=lambda command: (0, "ok"), fetch=_fetch_ok)
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
