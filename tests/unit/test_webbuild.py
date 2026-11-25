"""Compilación de la web tras un clon o un ``git pull`` (sin npm real)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import webbuild


@pytest.fixture
def web(tmp_path: Path) -> Path:
    root = tmp_path / "web"
    (root / "src" / "test").mkdir(parents=True)
    (root / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    (root / "package.json").write_text('{"name": "web"}', encoding="utf-8")
    (root / "package-lock.json").write_text('{"lockfileVersion": 3}', encoding="utf-8")
    (root / "src" / "App.tsx").write_text("export const App = 1;\n", encoding="utf-8")
    (root / "src" / "test" / "App.test.tsx").write_text("test", encoding="utf-8")
    return root


class FakeNpm:
    """Registra las órdenes y simula lo que deja ``npm`` en disco."""

    def __init__(self, fail: str | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail = fail

    def __call__(self, command: Sequence[str], cwd: Path) -> int:
        args = tuple(command[1:])
        self.calls.append(args)
        if self.fail and self.fail in args:
            return 1
        if args == ("ci",):
            (cwd / "node_modules").mkdir(exist_ok=True)
        if args == ("run", "build"):
            (cwd / "dist").mkdir(exist_ok=True)
            (cwd / "dist" / "index.html").write_text("<html>", encoding="utf-8")
        return 0


def test_clon_nuevo_sin_dist_esta_missing(web: Path) -> None:
    assert webbuild.status(web) == "missing"


def test_compilar_instala_dependencias_y_deja_la_web_al_dia(web: Path) -> None:
    npm = FakeNpm()

    assert webbuild.ensure_built(web, runner=npm, npm="npm") is True

    assert npm.calls == [("ci",), ("run", "build")]
    assert webbuild.status(web) == "ok"
    assert webbuild.deps_current(web)


def test_sin_cambios_no_vuelve_a_compilar(web: Path) -> None:
    webbuild.ensure_built(web, runner=FakeNpm(), npm="npm")
    npm = FakeNpm()

    assert webbuild.ensure_built(web, runner=npm, npm="npm") is False
    assert npm.calls == []


def test_cambio_en_fuentes_deja_la_web_desactualizada(web: Path) -> None:
    webbuild.ensure_built(web, runner=FakeNpm(), npm="npm")
    (web / "src" / "App.tsx").write_text("export const App = 2;\n", encoding="utf-8")
    npm = FakeNpm()

    assert webbuild.status(web) == "stale"
    assert webbuild.ensure_built(web, runner=npm, npm="npm") is True
    assert npm.calls == [("run", "build")]  # el lock no cambió: no repite npm ci


def test_cambio_en_el_lock_reinstala_dependencias(web: Path) -> None:
    webbuild.ensure_built(web, runner=FakeNpm(), npm="npm")
    (web / "package-lock.json").write_text('{"lockfileVersion": 3, "x": 1}', encoding="utf-8")
    npm = FakeNpm()

    webbuild.ensure_built(web, runner=npm, npm="npm")

    assert npm.calls == [("ci",), ("run", "build")]


def test_las_pruebas_no_cambian_la_huella(web: Path) -> None:
    before = webbuild.fingerprint(web)
    (web / "src" / "test" / "App.test.tsx").write_text("otra prueba", encoding="utf-8")
    (web / "src" / "Extra.test.tsx").write_text("prueba", encoding="utf-8")

    assert webbuild.fingerprint(web) == before


def test_finales_de_linea_no_cambian_la_huella(web: Path) -> None:
    before = webbuild.fingerprint(web)
    (web / "src" / "App.tsx").write_bytes(b"export const App = 1;\r\n")

    assert webbuild.fingerprint(web) == before


def test_dist_sin_huella_se_considera_desactualizada(web: Path) -> None:
    (web / "dist").mkdir()
    (web / "dist" / "index.html").write_text("<html>", encoding="utf-8")

    assert webbuild.status(web) == "stale"


def test_fallo_de_compilacion_no_marca_la_web_al_dia(web: Path) -> None:
    with pytest.raises(webbuild.WebBuildError, match="npm run build"):
        webbuild.build(web, runner=FakeNpm(fail="build"), npm="npm")

    assert webbuild.status(web) == "missing"


def test_sin_npm_explica_como_instalar_node(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webbuild.shutil, "which", lambda _name: None)

    with pytest.raises(webbuild.WebBuildError, match=r"Node.js"):
        webbuild._npm()


def test_check_devuelve_1_si_la_web_no_esta_al_dia(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], web: Path
) -> None:
    monkeypatch.setattr(webbuild, "WEB_DIR", web)

    assert webbuild.main(["--check"]) == 1
    assert "make app" in capsys.readouterr().out
