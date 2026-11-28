"""Operación del despliegue del Módulo 3 (spec 024, research R18, contracts/cli.md).

- ``workspace_sync``: copia el workspace versionado (``openclaw/workspace``) al de ejecución sin
  tocar la bitácora diaria (``memory/``).
- ``ops_check``: la «prueba de 3 minutos» del Anuncio 007 en un solo informe (backend, Qdrant,
  modelo, gateway, canal, auditoría de seguridad y estado de Git). Código 1 si algo falla.
- ``load_json5``: lector mínimo de la plantilla ``openclaw/openclaw.json5`` (comentarios, claves
  sin comillas y comas finales) para validarla en pruebas sin depender de OpenClaw.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT

WORKSPACE_SOURCE = PROJECT_ROOT / "openclaw" / "workspace"
OPENCLAW_CONFIG = PROJECT_ROOT / "openclaw" / "openclaw.json5"
PROTECTED = {"memory"}
KEY = re.compile(r"(?P<prefix>[{,]\s*)(?P<key>[A-Za-z_$][\w$-]*)\s*:")
TRAILING_COMMA = re.compile(r",(\s*[}\]])")


# --- JSON5 mínimo -----------------------------------------------------------------------------


def _strip_comments(text: str) -> str:
    out: list[str] = []
    index, quote = 0, ""
    while index < len(text):
        char = text[index]
        if quote:
            out.append(char)
            if char == "\\" and index + 1 < len(text):
                out.append(text[index + 1])
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
            out.append(char)
        elif text.startswith("//", index):
            newline = text.find("\n", index)
            index = len(text) if newline == -1 else newline
            continue
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end == -1 else end + 2
            continue
        else:
            out.append(char)
        index += 1
    return "".join(out)


def loads_json5(text: str) -> Any:
    """Subconjunto de JSON5 usado en la plantilla: comentarios, claves sin comillas y comas."""
    cleaned = _strip_comments(text)
    cleaned = KEY.sub(lambda m: f'{m.group("prefix")}"{m.group("key")}":', cleaned)
    cleaned = TRAILING_COMMA.sub(r"\1", cleaned)
    return json.loads(cleaned)


def load_json5(path: Path = OPENCLAW_CONFIG) -> Any:
    return loads_json5(Path(path).read_text(encoding="utf-8"))


# --- workspace ---------------------------------------------------------------------------------


def workspace_sync(target: Path, source: Path = WORKSPACE_SOURCE) -> list[str]:
    """Copia los archivos versionados al workspace de ejecución; nunca borra ``memory/``."""
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for path in sorted(Path(source).rglob("*")):
        relative = path.relative_to(source)
        if relative.parts and relative.parts[0] in PROTECTED:
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied.append(relative.as_posix())
    (target / "memory").mkdir(exist_ok=True)
    return copied


# --- prueba de 3 minutos -----------------------------------------------------------------------


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Runner = Callable[[Sequence[str]], tuple[int, str]]


def run_command(command: Sequence[str]) -> tuple[int, str]:
    executable = shutil.which(command[0])
    if executable is None:
        return 127, f"{command[0]} no está instalado"
    try:
        done = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=PROJECT_ROOT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    output = (done.stdout or done.stderr or "").strip()
    return done.returncode, output


def http_json(url: str, headers: dict[str, str] | None = None) -> tuple[int, Any]:
    import httpx

    try:
        response = httpx.get(url, headers=headers or {}, timeout=10)
    except httpx.HTTPError as exc:
        return 0, str(exc)
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Solo la prueba de conexión: «Runtime: stopped» describe el servicio propio de OpenClaw, que no
# usamos (el gateway de Valer-IA corre como tarea «ValerIA-Gateway»).
GATEWAY_DOWN = re.compile(r"connectivity check:\s*failed|econnrefused", re.I)
WHATSAPP_LINKED = re.compile(r"\blinked\b|\bconnected\b", re.I)
WHATSAPP_DOWN = re.compile(r"not linked|unlinked|logged out|disconnected|failed|econnrefused", re.I)
AUDIT_CRITICAL = re.compile(r"\b([1-9]\d*)\s+critical\b|critical:\s*([1-9]\d*)", re.I)


def _last_line(text: str) -> str:
    lines = [line for line in ANSI.sub("", text).splitlines() if line.strip()]
    return lines[-1][:200] if lines else ""


def judge_openclaw(name: str, code: int, output: str) -> CheckResult:
    """Lee el estado real en la salida del CLI (spec 028): el código 0 no basta.

    ``openclaw gateway status`` termina con 0 aunque el gateway esté detenido, y los demás comandos
    imprimen consejos genéricos al final; por eso se buscan las señales de cada estado.
    """
    text = ANSI.sub("", output)
    if code != 0:
        return CheckResult(name, False, _last_line(text) or f"código {code}")
    if name == "gateway":
        down = GATEWAY_DOWN.search(text)
        return CheckResult(name, not down, "detenido" if down else "escuchando")
    if name == "whatsapp":
        linked = WHATSAPP_LINKED.search(text) and not WHATSAPP_DOWN.search(text)
        return CheckResult(name, bool(linked), "vinculado" if linked else "sin vincular o caído")
    if name == "mcp":
        configured = "valeria-tools" in text
        return CheckResult(name, configured, "valeria-tools" if configured else "sin valeria-tools")
    if name == "auditoria":
        critical = AUDIT_CRITICAL.search(text)
        detail = (
            f"{critical.group(1) or critical.group(2)} críticos" if critical else "sin críticos"
        )
        return CheckResult(name, not critical, detail)
    return CheckResult(name, True, _last_line(text))


OPENCLAW_DIR = ".openclaw-valeria"


def _openclaw_env_values(path: Path, keys: Sequence[str]) -> dict[str, str]:
    """Solo las claves pedidas del ``.env`` de OpenClaw (nunca se lee ni se muestra nada más)."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in keys:
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def channel_mode(state_dir: Path | None = None) -> CheckResult:
    """Spec 031: modo del canal de WhatsApp (abierto o cerrado), sin mostrar números."""
    configured = os.environ.get("OPENCLAW_STATE_DIR", "").strip()
    base = state_dir or (Path(configured) if configured else Path.home() / OPENCLAW_DIR)
    env_file = base / ".env"
    if not env_file.is_file():
        return CheckResult("modo-canal", False, "sin .env de OpenClaw")
    keys = ("WA_DM_POLICY", "WA_ALLOW_1", "WA_ALLOW_2", "WA_ALLOW_3")
    values = _openclaw_env_values(env_file, keys)
    policy = values.get("WA_DM_POLICY", "").lower()
    if policy == "open":
        return CheckResult(
            "modo-canal", True, "ABIERTO al público (recuerda cerrarlo al terminar el proyecto)"
        )
    allowed = sum(1 for key in keys[1:] if values.get(key) and values[key] != "*")
    return CheckResult("modo-canal", True, f"cerrado ({allowed} números de prueba)")


def ops_check(
    *,
    backend: str = "http://127.0.0.1:8000",
    run: Runner = run_command,
    fetch: Callable[..., tuple[int, Any]] = http_json,
) -> list[CheckResult]:
    """Comprobaciones de la jornada; cada una devuelve ``ok`` y un detalle corto."""
    results: list[CheckResult] = []
    status, body = fetch(f"{backend}/api/health")
    results.append(CheckResult("backend", status == 200, f"HTTP {status}"))
    token = os.environ.get("VALERIA_CHANNEL_TOKEN", "")
    status, body = fetch(f"{backend}/api/channels/status", {"X-Channel-Token": token})
    if status == 200 and isinstance(body, dict):
        results.append(CheckResult("modelo", bool(body.get("model", {}).get("ok")), "DeepSeek"))
        qdrant = body.get("qdrant", {})
        results.append(
            CheckResult("qdrant", bool(qdrant.get("ok")), f"modo {qdrant.get('mode', '?')}")
        )
        results.append(CheckResult("canal-backend", True, json.dumps(body.get("channels", {}))))
    else:
        results.append(CheckResult("canal-backend", False, f"HTTP {status}"))
    results.append(channel_mode())
    for name, command in (
        ("gateway", ["openclaw", "gateway", "status"]),
        ("whatsapp", ["openclaw", "channels", "status", "--probe"]),
        ("mcp", ["openclaw", "mcp", "status"]),
        ("auditoria", ["openclaw", "security", "audit"]),
    ):
        code, output = run(command)
        results.append(judge_openclaw(name, code, output))
    code, output = run(["git", "status", "--short"])
    dirty = [line for line in output.splitlines() if line.strip()]
    results.append(
        CheckResult("git", code == 0, "limpio" if not dirty else f"{len(dirty)} cambios sin commit")
    )
    return results


def render(results: Sequence[CheckResult]) -> str:
    lines = [f"{'✅' if r.ok else '❌'} {r.name}: {r.detail}" for r in results]
    failed = sum(1 for r in results if not r.ok)
    lines.append("Todo en verde." if not failed else f"{failed} comprobaciones fallaron.")
    return "\n".join(lines)
