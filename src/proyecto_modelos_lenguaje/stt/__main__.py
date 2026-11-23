"""CLI del dictado (spec 023, contracts/stt-api.md §5).

    uv run python -m proyecto_modelos_lenguaje.stt --check [--json]
    uv run python -m proyecto_modelos_lenguaje.stt transcribe ARCHIVO.wav [--json]
    uv run python -m proyecto_modelos_lenguaje.stt eval [--models base small] [--voices Rebeca …]
        [--audio-dir DIR] [--include-human-text] [--json-out PATH] [--export-sample PATH]

Códigos de salida: 0 OK · 1 argumentos, error o metas no cumplidas · 2 dictado no disponible.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from ..config import PROJECT_ROOT
from .audio import AudioTooLargeError, EmptyAudioError, UnsupportedAudioError, parse_wav16k
from .engine import SttService, SttUnavailableError

CHECK_PHRASE = "¿Qué produce Manuelita?"
EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 2


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _check_clip() -> tuple[np.ndarray, int, str]:
    """La frase de prueba sintetizada con Phonon; sin voz disponible, 1 s de silencio."""
    try:
        from ..voice.engine import get_voice_service
        from .audio import resample

        result = get_voice_service().synthesize(CHECK_PHRASE)
        samples = resample(result.samples, result.sample_rate)
        return samples, round(samples.size / 16), CHECK_PHRASE
    except Exception:
        print("Phonon no está disponible: se transcribe 1 s de silencio.", file=sys.stderr)
        return np.zeros(16_000, dtype=np.float32), 1000, ""


def _check(service: SttService, as_json: bool) -> int:
    started = time.perf_counter()
    try:
        service.ensure_loaded()
    except SttUnavailableError:
        _print(service.status().to_dict(), as_json)
        return EXIT_UNAVAILABLE
    load_ms = round((time.perf_counter() - started) * 1000.0, 1)
    samples, audio_ms, expected = _check_clip()
    result = service.transcribe(samples, audio_ms)
    payload = {
        **service.status().to_dict(),
        "license": service.license,
        "load_ms": load_ms,
        "audio_ms": result.audio_ms,
        "stt_ms": result.stt_ms,
        "expected": expected,
        "text": result.text,
    }
    _print(payload, as_json)
    return EXIT_OK


def _transcribe(service: SttService, path: str, as_json: bool) -> int:
    config = service.config
    try:
        samples, audio_ms = parse_wav16k(
            Path(path).read_bytes(), max_bytes=config.max_bytes, max_seconds=config.max_seconds
        )
        result = service.transcribe(samples, audio_ms)
    except (OSError, EmptyAudioError, UnsupportedAudioError, AudioTooLargeError) as exc:
        print(f"No se pudo leer el audio: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except SttUnavailableError:
        _print(service.status().to_dict(), as_json)
        return EXIT_UNAVAILABLE
    if as_json:
        _print(result.to_dict(), True)
    else:
        print(result.text if not result.empty else "(sin texto)")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m proyecto_modelos_lenguaje.stt",
        description="Dictado de Valer-IA Caña (faster-whisper): verificar, transcribir y evaluar.",
    )
    parser.add_argument("--check", action="store_true", help="carga el modelo y transcribe")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    commands = parser.add_subparsers(dest="command")
    transcribe = commands.add_parser("transcribe", help="transcribe un WAV PCM16 mono a 16 kHz")
    transcribe.add_argument("path")
    transcribe.add_argument("--json", action="store_true", dest="json_sub")
    evaluate = commands.add_parser("eval", help="batería de evaluación (research R11)")
    evaluate.add_argument(
        "--models", nargs="+", help="modelos a comparar (defecto: el configurado)"
    )
    evaluate.add_argument("--voices", nargs="+", default=None, help="voces de Phonon")
    evaluate.add_argument(
        "--audio-dir", type=Path, help="grabaciones humanas locales (.wav + .txt)"
    )
    evaluate.add_argument(
        "--include-human-text",
        action="store_true",
        help="publica las hipótesis de las grabaciones humanas en el informe",
    )
    evaluate.add_argument(
        "--json-out",
        type=Path,
        default=PROJECT_ROOT / "docs" / "evaluacion_stt.json",
        help="informe JSON (el Markdown va al lado)",
    )
    evaluate.add_argument(
        "--export-sample",
        type=Path,
        help="solo escribe un WAV de muestra en esta ruta (para curl o Playwright) y termina",
    )
    evaluate.add_argument("--limit", type=int, help="usa solo las primeras N frases (pruebas)")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_ERROR if exc.code else EXIT_OK
    if args.command == "eval":
        from .eval import main_eval

        return main_eval(args)
    service = SttService()
    if args.command == "transcribe":
        return _transcribe(service, args.path, args.json or args.json_sub)
    if args.check:
        return _check(service, args.json)
    build_parser().print_help()
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
