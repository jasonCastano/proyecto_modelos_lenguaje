"""Compilación de la web para quien clona el repositorio.

``web/dist`` no se versiona: cada equipo la compila. Este módulo evita los dos tropiezos de un clon
o de un ``git pull``:

- **Dependencias viejas**: si ``web/package-lock.json`` cambió desde el último ``npm ci``, lo
  vuelve a correr antes de compilar.
- **Compilación vieja**: cada compilación deja en ``web/dist/.build-stamp`` la huella de sus
  fuentes. Si las fuentes cambiaron, la web está desactualizada y se recompila.

Uso::

    uv run python -m proyecto_modelos_lenguaje.webbuild             # compila siempre
    uv run python -m proyecto_modelos_lenguaje.webbuild --if-needed # solo si falta o está vieja
    uv run python -m proyecto_modelos_lenguaje.webbuild --check     # informa, no compila
    uv run python -m proyecto_modelos_lenguaje.webbuild --install   # solo npm ci
    uv run python -m proyecto_modelos_lenguaje.webbuild --serve     # compila si hace falta y abre
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"

BUILD_STAMP = ".build-stamp"
DEPS_STAMP = ".pml-lock.sha256"

# Lo que entra en la compilación de producción (``tsc -b && vite build``).
INPUT_FILES = (
    "index.html",
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
)
INPUT_DIRS = ("src", "public")
# Las pruebas no cambian el resultado de la compilación.
IGNORED_PARTS = frozenset({"test", "__tests__", "node_modules"})

Status = Literal["ok", "stale", "missing"]
Runner = Callable[[Sequence[str], Path], int]

MESSAGES: dict[Status, str] = {
    "ok": "La web está compilada y al día.",
    "stale": "La web compilada está desactualizada: sus fuentes cambiaron desde la última"
    " compilación.",
    "missing": "La web no está compilada (web/dist no existe en un clon nuevo).",
}
FIX = "Ejecuta `make app` o `uv run python -m proyecto_modelos_lenguaje.webbuild --serve`."


class WebBuildError(RuntimeError):
    """La compilación no se pudo hacer; el mensaje dice cómo resolverlo."""


def _input_paths(web_dir: Path) -> Iterable[Path]:
    for name in INPUT_FILES:
        path = web_dir / name
        if path.is_file():
            yield path
    for name in INPUT_DIRS:
        base = web_dir / name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(web_dir)
            if IGNORED_PARTS.intersection(relative.parts) or ".test." in path.name:
                continue
            yield path


def _normalized(path: Path) -> bytes:
    # Los finales de línea dependen de core.autocrlf; la huella es igual en todos los equipos.
    return path.read_bytes().replace(b"\r\n", b"\n")


def fingerprint(web_dir: Path = WEB_DIR) -> str:
    """Huella de las fuentes de la web: ruta relativa y contenido de cada archivo."""
    digest = hashlib.sha256()
    for path in sorted(_input_paths(web_dir), key=lambda p: p.relative_to(web_dir).as_posix()):
        digest.update(path.relative_to(web_dir).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(_normalized(path)).digest())
    return digest.hexdigest()


def status(web_dir: Path = WEB_DIR) -> Status:
    """``missing`` sin compilación, ``stale`` si las fuentes cambiaron, ``ok`` si está al día."""
    dist = web_dir / "dist"
    if not (dist / "index.html").is_file():
        return "missing"
    stamp = dist / BUILD_STAMP
    if not stamp.is_file() or stamp.read_text(encoding="utf-8").strip() != fingerprint(web_dir):
        return "stale"
    return "ok"


def _lock_hash(web_dir: Path) -> str:
    return hashlib.sha256(_normalized(web_dir / "package-lock.json")).hexdigest()


def deps_current(web_dir: Path = WEB_DIR) -> bool:
    """¿``node_modules`` corresponde al ``package-lock.json`` actual?"""
    stamp = web_dir / "node_modules" / DEPS_STAMP
    return stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == _lock_hash(web_dir)


def _npm() -> str:
    npm = shutil.which("npm")
    if npm is None:
        raise WebBuildError("No se encontró npm. Instala Node.js 24 (https://nodejs.org) y repite.")
    return npm


def _run(command: Sequence[str], cwd: Path) -> int:
    return subprocess.call(list(command), cwd=cwd)


def install(
    web_dir: Path = WEB_DIR, *, runner: Runner = _run, npm: str | None = None, force: bool = False
) -> bool:
    """``npm ci`` si ``package-lock.json`` cambió (o siempre con ``force``). ``True`` si instaló."""
    if not force and deps_current(web_dir):
        return False
    npm = npm or _npm()
    print("Instalando dependencias de la web (npm ci)...", flush=True)
    if runner([npm, "ci"], web_dir) != 0:
        raise WebBuildError("`npm ci` falló en web/. Revisa la salida anterior.")
    (web_dir / "node_modules" / DEPS_STAMP).write_text(_lock_hash(web_dir), encoding="utf-8")
    return True


def build(web_dir: Path = WEB_DIR, *, runner: Runner = _run, npm: str | None = None) -> None:
    """Instala dependencias si cambiaron, compila y deja la huella de la compilación."""
    npm = npm or _npm()
    install(web_dir, runner=runner, npm=npm)
    print("Compilando la web (npm run build)...", flush=True)
    if runner([npm, "run", "build"], web_dir) != 0:
        raise WebBuildError("`npm run build` falló en web/. Revisa la salida anterior.")
    (web_dir / "dist" / BUILD_STAMP).write_text(fingerprint(web_dir), encoding="utf-8")


def ensure_built(web_dir: Path = WEB_DIR, *, runner: Runner = _run, npm: str | None = None) -> bool:
    """Compila solo si falta o está vieja. Devuelve ``True`` si compiló."""
    current = status(web_dir)
    if current == "ok":
        print(MESSAGES["ok"], flush=True)
        return False
    print(MESSAGES[current], flush=True)
    build(web_dir, runner=runner, npm=npm)
    return True


def _utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _utf8_output()
    parser = argparse.ArgumentParser(description="Compila la web de Valer-IA (web/dist).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="solo informa el estado")
    mode.add_argument("--install", action="store_true", help="solo npm ci (siempre)")
    mode.add_argument("--if-needed", action="store_true", help="compila solo si falta o está vieja")
    mode.add_argument("--serve", action="store_true", help="compila si hace falta y abre la app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.check:
        current = status(WEB_DIR)
        print(MESSAGES[current])
        if current != "ok":
            print(FIX)
        return 0 if current == "ok" else 1
    try:
        if args.install:
            install(WEB_DIR, force=True)
            return 0
        if args.if_needed or args.serve:
            ensure_built(WEB_DIR)
        else:
            build(WEB_DIR)
    except WebBuildError as error:
        print(error, file=sys.stderr)
        return 1
    if args.serve:
        import uvicorn

        print(f"Abriendo la app en http://{args.host}:{args.port}", flush=True)
        uvicorn.run("proyecto_modelos_lenguaje.api:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
