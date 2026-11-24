"""Simula el puente de OpenClaw contra el backend local (spec 024, T026).

    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 --text hola
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 --kind image
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 \\
        --profile planificador --text "Tenemos 15 % menos caña esta semana"   # spec 025

Usa ``VALERIA_CHANNEL_TOKEN`` del ``.env`` y llama ``POST /api/channels/messages`` como lo haría el
plugin ``valeria-bridge``: sirve para ensayar sin teléfono y para la prueba de carga
(``--concurrency``). Códigos de salida: 0 OK · 1 error · 2 backend no disponible.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import httpx
from dotenv import load_dotenv

from ..config import PROJECT_ROOT

EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m proyecto_modelos_lenguaje.channels")
    commands = parser.add_subparsers(dest="command", required=True)
    simulate = commands.add_parser("simulate", help="envía un mensaje como el puente de OpenClaw")
    simulate.add_argument("--sender", required=True, help="número E.164 (de prueba)")
    simulate.add_argument("--text", default=None)
    simulate.add_argument("--kind", default="text")
    simulate.add_argument("--channel", default="whatsapp", choices=("whatsapp", "telegram"))
    simulate.add_argument("--message-id", default=None)
    simulate.add_argument("--backend", default=os.environ.get("VALERIA_BACKEND_URL", ""))
    simulate.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="N remitentes distintos a la vez (prueba de carga, SC-002)",
    )
    simulate.add_argument("--timeout", type=float, default=60.0)
    simulate.add_argument(
        "--profile",
        default=None,
        help="spec 025: envía antes «/perfil <clave>» desde el mismo remitente",
    )
    return parser


def _sender(base: str, index: int) -> str:
    if index == 0:
        return base
    digits = base.lstrip("+")
    return f"+{digits[:-3]}{(int(digits[-3:]) + index) % 1000:03d}"


def _post_profile(args: argparse.Namespace, url: str, token: str, index: int) -> None:
    """Spec 025: activa el perfil con ``/perfil`` antes del mensaje (como un usuario real)."""
    body = {
        "channel": args.channel,
        "message_id": uuid.uuid4().hex,
        "sender": _sender(args.sender, index),
        "kind": "text",
        "text": f"/perfil {args.profile}",
        "received_at": datetime.now(UTC).isoformat(),
    }
    httpx.post(url, json=body, headers={"X-Channel-Token": token}, timeout=args.timeout)


def _send(args: argparse.Namespace, url: str, token: str, index: int) -> dict:
    if getattr(args, "profile", None):
        _post_profile(args, url, token, index)
    body = {
        "channel": args.channel,
        "message_id": args.message_id if index == 0 and args.message_id else uuid.uuid4().hex,
        "sender": _sender(args.sender, index),
        "kind": args.kind,
        "text": args.text,
        "received_at": datetime.now(UTC).isoformat(),
    }
    started = time.perf_counter()
    response = httpx.post(url, json=body, headers={"X-Channel-Token": token}, timeout=args.timeout)
    elapsed = round((time.perf_counter() - started) * 1000)
    payload = response.json() if response.content else {}
    return {"http": response.status_code, "elapsed_ms": elapsed, **payload}


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    args = build_parser().parse_args(argv)
    token = os.environ.get("VALERIA_CHANNEL_TOKEN", "")
    if not token:
        print("Falta VALERIA_CHANNEL_TOKEN en el entorno o en .env.", file=sys.stderr)
        return EXIT_ERROR
    backend = (args.backend or "http://127.0.0.1:8000").rstrip("/")
    url = f"{backend}/api/channels/messages"
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
            results = list(
                pool.map(lambda i: _send(args, url, token, i), range(max(1, args.concurrency)))
            )
    except httpx.HTTPError as exc:
        print(f"Backend no disponible en {backend}: {exc}", file=sys.stderr)
        return EXIT_UNAVAILABLE
    if len(results) == 1:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    else:
        times = sorted(r["elapsed_ms"] for r in results)
        summary = {
            "requests": len(results),
            "ok": sum(1 for r in results if r["http"] == 200 and r.get("status") != "error"),
            "p90_ms": times[min(len(times) - 1, int(0.9 * len(times)))],
            "max_ms": times[-1],
            "statuses": sorted({str(r.get("status")) for r in results}),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return EXIT_OK if all(r["http"] == 200 for r in results) else EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
