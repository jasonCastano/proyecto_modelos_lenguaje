"""Simula el puente de OpenClaw contra el backend local (spec 024, T026).

    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 --text hola
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 --kind image
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 \\
        --profile planificador --text "Tenemos 15 % menos caña esta semana"   # spec 025
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 \\
        --kind audio --language en --text "What does Manuelita produce?"      # spec 028 (voz)
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 \\
        --script tests/fixtures/channels/natural_conversation.jsonl          # spec 028
    uv run python -m proyecto_modelos_lenguaje.channels simulate --sender +570000000001 \\
        --script tests/fixtures/channels/language_format.jsonl --check       # spec 029
    uv run python -m proyecto_modelos_lenguaje.channels simulate \
        --script tests/fixtures/channels/conversation_start.jsonl --check    # spec 032
    uv run python -m proyecto_modelos_lenguaje.channels simulate \
        --script tests/fixtures/channels/stickers.jsonl --check              # spec 034
    uv run python -m proyecto_modelos_lenguaje.channels pseudonym --sender <número>   # spec 031
    uv run python -m proyecto_modelos_lenguaje.channels block --sender <número>
    uv run python -m proyecto_modelos_lenguaje.channels unblock --sender <número>
    uv run python -m proyecto_modelos_lenguaje.channels block --pseudonym wa-<16 hex>   # spec 033
    uv run python -m proyecto_modelos_lenguaje.channels blocked

Usa ``VALERIA_CHANNEL_TOKEN`` del ``.env`` y llama ``POST /api/channels/messages`` como lo haría el
plugin ``valeria-bridge``: sirve para ensayar sin teléfono y para la prueba de carga
(``--concurrency``). Códigos de salida: 0 OK · 1 error · 2 backend no disponible.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

from ..config import PROJECT_ROOT

EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 2
PSEUDONYM = re.compile(r"(?:wa|tg)-[0-9a-f]{16}")  # spec 033: bloqueo por seudónimo
COMMAND_MENTION = re.compile(r"(?<![\w/])/[a-záéíóúñ]+", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m proyecto_modelos_lenguaje.channels")
    commands = parser.add_subparsers(dest="command", required=True)
    # Spec 031: comandos del operador (en el servidor). Calculan el seudónimo; nunca guardan ni
    # imprimen el número.
    for name, text in (
        ("pseudonym", "imprime el seudónimo wa-… de un número (para VALERIA_OPERATORS)"),
        ("block", "bloquea un número o un seudónimo (no recibe respuesta)"),
        ("unblock", "desbloquea un número o un seudónimo"),
    ):
        operator = commands.add_parser(name, help=text)
        if name == "pseudonym":
            operator.add_argument("--sender", required=True, help="número E.164")
        else:
            # Spec 033: las cuentas que WhatsApp entrega solo con su ID no tienen número conocido;
            # se bloquean con el seudónimo que muestran los registros.
            who = operator.add_mutually_exclusive_group(required=True)
            who.add_argument("--sender", help="número E.164")
            who.add_argument("--pseudonym", help="seudónimo wa-<16 hex> de los registros")
        operator.add_argument("--channel", default="whatsapp", choices=("whatsapp", "telegram"))
    commands.add_parser("blocked", help="lista los seudónimos bloqueados")
    simulate = commands.add_parser("simulate", help="envía un mensaje como el puente de OpenClaw")
    simulate.add_argument(
        "--sender",
        default="+570000000001",
        help="número E.164 de prueba (ficticio por defecto; los guiones con «conversation» "
        "usan uno nuevo por conversación)",
    )
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
    simulate.add_argument("--timeout", type=float, default=120.0)
    simulate.add_argument(
        "--language",
        default=None,
        choices=("es", "en"),
        help="spec 028: pista de idioma de una nota de voz simulada (--kind audio)",
    )
    simulate.add_argument(
        "--script",
        type=Path,
        default=None,
        help="spec 028: JSONL con mensajes (text, kind, lang) que envía un mismo remitente",
    )
    simulate.add_argument(
        "--check",
        action="store_true",
        help="spec 029: revisa idioma, fuentes y aviso de cada respuesta (y voz si fue audio)",
    )
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


def _message(
    args: argparse.Namespace, sender: str, text: str | None, kind: str, language: str | None
) -> dict:
    body = {
        "channel": args.channel,
        "message_id": uuid.uuid4().hex,
        "sender": sender,
        "kind": kind,
        "text": text,
        "received_at": datetime.now(UTC).isoformat(),
    }
    if kind == "audio":  # spec 028: así llega una nota de voz ya transcrita por el gateway
        body["input_mode"] = "voice"
        if language:
            body["language_hint"] = language
    return body


def _send(args: argparse.Namespace, url: str, token: str, index: int) -> dict:
    if getattr(args, "profile", None):
        _post_profile(args, url, token, index)
    body = _message(
        args, _sender(args.sender, index), args.text, args.kind, getattr(args, "language", None)
    )
    if index == 0 and args.message_id:
        body["message_id"] = args.message_id
    started = time.perf_counter()
    response = httpx.post(url, json=body, headers={"X-Channel-Token": token}, timeout=args.timeout)
    elapsed = round((time.perf_counter() - started) * 1000)
    payload = response.json() if response.content else {}
    return {"http": response.status_code, "elapsed_ms": elapsed, **payload}


def run_script(args: argparse.Namespace, url: str, token: str) -> int:
    """Spec 028 (T034): conversación completa de un mismo remitente, mensaje por mensaje."""
    lines = args.script.read_text(encoding="utf-8").splitlines()
    mentions = 0
    findings = 0
    check = bool(getattr(args, "check", False))
    senders: dict[str, str] = {}  # spec 032: cada «conversation» es un número ficticio nuevo
    stickers: dict[str, list[str]] = {}  # spec 034: stickers por conversación
    for raw in lines:
        if not raw.strip():
            continue
        item = json.loads(raw)
        kind = item.get("kind", "text")
        sender = args.sender
        if item.get("conversation"):
            sender = senders.setdefault(str(item["conversation"]), fresh_sender())
        body = _message(args, sender, item.get("text"), kind, item.get("lang"))
        response = httpx.post(
            url, json=body, headers={"X-Channel-Token": token}, timeout=args.timeout
        )
        payload = response.json() if response.content else {}
        delivered = delivered_text(payload)
        text = "\n".join(delivered)
        found = COMMAND_MENTION.findall("\n".join(payload.get("messages") or []))
        mentions += len(found)
        voice = payload.get("voice") or {}
        print(f"> {item.get('id', '')} {item.get('text', '')}")
        if voice:
            print(f"  (nota de voz {voice.get('language')}, {voice.get('duration_ms')} ms)")
            label = "solo fuentes" if delivered else "sin texto"
            print(f"  [{payload.get('status')}] (texto: {label}) {text}")
        else:
            print(f"  [{payload.get('status')}] (texto: completo) {text}")
        if found:
            print(f"  ⚠ menciona comandos: {', '.join(found)}")
        if check:
            findings += _check_reply(item, payload)
            if "new_conversation" in item:
                findings += check_introduction(item, payload)
            if "expected_sticker" in item:
                sent = stickers.setdefault(str(item.get("conversation") or ""), [])
                findings += check_sticker(item, payload, sent)
    print(f"Mensajes con comandos mencionados: {mentions}")
    if check:
        print(f"Hallazgos de formato y presentación (specs 029 a 032): {findings}")
    return EXIT_OK if mentions == 0 and findings == 0 else EXIT_ERROR


def delivered_text(payload: dict) -> list[str]:
    """Spec 030: el texto que entregaría el plugin si la nota de voz llega (solo fuentes)."""
    if payload.get("voice") and isinstance(payload.get("sources_messages"), list):
        return [m for m in payload["sources_messages"] if m.strip()]
    return list(payload.get("messages") or [])


def fresh_sender() -> str:
    """Número ficticio nuevo por corrida (+57 00000 …): la conversación siempre empieza de cero."""
    return f"+5700000{secrets.randbelow(100_000):05d}"


def check_introduction(item: dict, payload: dict) -> int:
    """Spec 032 (contrato §6): presentación en la primera respuesta y nunca repetida.

    El guion marca cada mensaje con ``new_conversation`` (``true`` si abre la conversación). La
    longitud de la presentación (≤ 2 frases) la garantizan las variantes de ``channels.greeting``.
    """
    if payload.get("status") in {"ignored", "busy"}:
        return 0
    text = "\n".join(payload.get("messages") or [])
    introduced = "valer-ia" in text.lower()
    if item.get("new_conversation") and not introduced:
        print("  ✗ intro_missing: la primera respuesta de la conversación no se presenta")
        return 1
    if not item.get("new_conversation") and introduced:
        print("  ✗ intro_repeated: la presentación se repite dentro de la conversación")
        return 1
    return 0


def check_sticker(item: dict, payload: dict, sent: list[str], limit: int = 8) -> int:
    """Spec 034: el sticker esperado (o ninguno) y sin exceso (spec 037: máximo 8)."""
    sticker = payload.get("sticker") or {}
    name = sticker.get("name") if isinstance(sticker, dict) else None
    if name:
        sent.append(str(name))
    findings = 0
    if name != item.get("expected_sticker"):
        print(f"  ✗ sticker_mismatch: esperado {item.get('expected_sticker')}, llegó {name}")
        findings += 1
    if len(sent) > limit:
        print(f"  ✗ sticker_overuse: {len(sent)} stickers en la conversación (máximo {limit})")
        findings += 1
    return findings


def _check_reply(item: dict, payload: dict) -> int:
    """Specs 029 y 030: un idioma, fuentes ordenadas, aviso oportuno, voz y sin texto repetido."""
    from .quality import review_reply

    language = item.get("lang") or "es"
    issues = review_reply(
        delivered_text(payload),
        language,
        sensitive_input=bool(item.get("sensitive")),
        voice=bool(payload.get("voice")),
    )
    for issue in issues:
        print(f"  ✗ {issue.code} (mensaje {issue.message_index + 1}): {issue.detail}")
    missing_voice = item.get("kind") == "audio" and not payload.get("voice")
    if missing_voice:
        print("  ✗ voice_missing: la nota de voz no recibió respuesta en audio")
    return len(issues) + int(missing_voice)


def _operator_store():
    from ..agent.config import load_agent_config, resolve_state_dir
    from .store import ChannelStore

    config = load_agent_config()
    return ChannelStore(resolve_state_dir(config.state_env_var) / "channels.sqlite3")


def run_operator(args: argparse.Namespace) -> int:
    """Spec 031: seudónimo y bloqueo por número, sin guardar ni imprimir el número."""
    from .identity import SenderError, channel_salt, pseudonym

    if args.command == "blocked":
        store = _operator_store()
        rows = store.blocked()
        store.close()
        for user_id, blocked_at in rows:
            print(f"{user_id}  {blocked_at}")
        print(f"Bloqueados: {len(rows)}")
        return EXIT_OK
    if getattr(args, "pseudonym", None):
        if not PSEUDONYM.fullmatch(args.pseudonym):
            print("El seudónimo debe tener la forma wa-<16 hex>.", file=sys.stderr)
            return EXIT_ERROR
        user_id = args.pseudonym
    else:
        try:
            user_id = pseudonym(args.sender, channel_salt(), args.channel)
        except SenderError as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_ERROR
    if args.command == "pseudonym":
        print(user_id)
        return EXIT_OK
    store = _operator_store()
    if args.command == "block":
        changed = store.block(user_id)
        print(f"bloqueado {user_id}" if changed else f"ya estaba bloqueado {user_id}")
    else:
        changed = store.unblock(user_id)
        print(f"desbloqueado {user_id}" if changed else f"no estaba bloqueado {user_id}")
    store.close()
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    args = build_parser().parse_args(argv)
    if args.command in {"pseudonym", "block", "unblock", "blocked"}:
        return run_operator(args)
    token = os.environ.get("VALERIA_CHANNEL_TOKEN", "")
    if not token:
        print("Falta VALERIA_CHANNEL_TOKEN en el entorno o en .env.", file=sys.stderr)
        return EXIT_ERROR
    backend = (args.backend or "http://127.0.0.1:8000").rstrip("/")
    url = f"{backend}/api/channels/messages"
    if args.script is not None:
        try:
            return run_script(args, url, token)
        except httpx.HTTPError as exc:
            print(f"Backend no disponible en {backend}: {exc}", file=sys.stderr)
            return EXIT_UNAVAILABLE
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
