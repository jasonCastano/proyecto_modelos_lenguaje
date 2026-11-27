"""CLI de transcripción que ejecuta OpenClaw por cada nota de voz (spec 028, channel-api-v2 §3).

``openclaw.json5`` → ``tools.media.models[].type = "cli"`` con ``{{AttachmentPath}}``. Envía el
archivo al backend (``POST /api/channels/transcriptions``, dictado ya cargado) y, si el backend no
responde, transcribe en proceso. Escribe la transcripción en stdout (una línea UTF-8):

- código 0 y texto → OpenClaw reemplaza el cuerpo del mensaje por la transcripción;
- código 0 y nada → no hubo habla;
- código 1 → error (OpenClaw entrega el ``<media:audio>`` original y Valer-IA pide repetir).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

DEFAULT_BACKEND = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 20
TOKEN_ENV = "VALERIA_CHANNEL_TOKEN"
BACKEND_ENV = "VALERIA_BACKEND_URL"

Poster = Callable[[str, bytes, dict[str, str], float], dict]


def _post(url: str, data: bytes, headers: dict[str, str], timeout: float) -> dict:
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _is_loopback(url: str) -> bool:
    host = url.split("://", 1)[-1].split("/", 1)[0].rsplit(":", 1)[0].strip("[]")
    return host in {"127.0.0.1", "localhost", "::1"}


def via_backend(data: bytes, env: dict[str, str], post: Poster = _post) -> str:
    base = (env.get(BACKEND_ENV) or DEFAULT_BACKEND).rstrip("/")
    if not _is_loopback(base):
        raise ValueError("VALERIA_BACKEND_URL debe ser loopback")
    headers = {
        "Content-Type": "application/octet-stream",
        "X-Channel-Token": env.get(TOKEN_ENV, ""),
    }
    body = post(f"{base}/api/channels/transcriptions", data, headers, TIMEOUT_SECONDS)
    return str(body.get("text") or "")


def in_process(data: bytes) -> str:
    from .transcription import transcribe_bytes

    return transcribe_bytes(data).text


def transcribe_file(
    path: Path,
    env: dict[str, str] | None = None,
    *,
    post: Poster = _post,
    local: Callable[[bytes], str] = in_process,
) -> str:
    """Transcripción del archivo: primero el backend; si falla la red, en proceso."""
    environment = dict(os.environ if env is None else env)
    data = Path(path).read_bytes()
    try:
        return via_backend(data, environment, post)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        if isinstance(exc, urllib.error.HTTPError) and exc.code in (400, 413):
            raise  # el audio es inválido o demasiado largo: no tiene sentido reintentar
        return local(data)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        usage = "uso: python -m proyecto_modelos_lenguaje.channels.transcribe_cli <ruta>"
        print(usage, file=sys.stderr)
        return 1
    try:
        text = transcribe_file(Path(args[0]))
    except Exception as exc:  # nunca imprime el contenido: solo el tipo de error
        print(f"transcripción fallida: {type(exc).__name__}", file=sys.stderr)
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    print(" ".join(text.split()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
