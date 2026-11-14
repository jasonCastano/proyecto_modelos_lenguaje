"""CLI de la voz del agente (spec 016, contracts/voice-cli.md).

    uv run python -m proyecto_modelos_lenguaje.voice --check [--json]
    uv run python -m proyecto_modelos_lenguaje.voice --list-voices [--json]
    uv run python -m proyecto_modelos_lenguaje.voice --say "Hola." [--voice Regina] [-o salida.wav]

Códigos de salida: 0 OK · 1 argumentos o error de síntesis · 2 motor no disponible.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from ..config import PROJECT_ROOT
from .audio import to_wav_bytes
from .engine import UnknownVoiceError, VoiceService, VoiceUnavailableError
from .text import clean_for_speech

CHECK_PHRASE = "Hola, soy el asistente de Ingenio Manuelita."
EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 2


def _print(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def _check(service: VoiceService, as_json: bool) -> int:
    started = time.perf_counter()
    try:
        service.ensure_loaded()
        load_ms = round((time.perf_counter() - started) * 1000.0, 1)
        result = service.synthesize(CHECK_PHRASE)
    except VoiceUnavailableError:
        _print(service.status().to_dict(), as_json)
        return EXIT_UNAVAILABLE
    except UnknownVoiceError as exc:
        _print({**service.status().to_dict(), "error": str(exc)}, as_json)
        return EXIT_ERROR
    payload = {
        **service.status().to_dict(),
        "load_ms": load_ms,
        "synth_ms": result.synth_ms,
        "audio_ms": result.audio_ms,
    }
    _print(payload, as_json)
    return EXIT_OK


def _list_voices(service: VoiceService, as_json: bool) -> int:
    try:
        voices = service.voices()
    except VoiceUnavailableError:
        _print(service.status().to_dict(), as_json)
        return EXIT_UNAVAILABLE
    configured = service.config.voice.casefold()
    rows = [
        {
            "name": info.name,
            "id": info.voice_id,
            "accent": info.accent,
            "gender": info.gender,
            "configured": configured in {info.name.casefold(), info.voice_id.casefold()},
        }
        for info in voices
    ]
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            mark = "*" if row["configured"] else " "
            print(f"{mark} {row['name']:<10} {row['id']:<18} {row['accent']:<3} {row['gender']}")
    return EXIT_OK


def _say(
    service: VoiceService, text: str, voice: str | None, output: str | None, as_json: bool
) -> int:
    clean = clean_for_speech(text)
    if not clean:
        print("El texto no tiene nada pronunciable después de limpiarlo.", file=sys.stderr)
        return EXIT_ERROR
    try:
        result = service.synthesize(clean, voice)
    except VoiceUnavailableError:
        _print(service.status().to_dict(), as_json)
        return EXIT_UNAVAILABLE
    except UnknownVoiceError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR
    if output:
        target = Path(output).expanduser().resolve()
    else:
        descriptor, name = tempfile.mkstemp(prefix="manuelita-voz-", suffix=".wav")
        os.close(descriptor)
        target = Path(name)
    data_dir = (PROJECT_ROOT / "data").resolve()
    if target == data_dir or data_dir in target.parents:
        print("No se escribe audio dentro de data/.", file=sys.stderr)
        return EXIT_ERROR
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(to_wav_bytes(result.samples, result.sample_rate))
    payload = {
        "output": str(target),
        "voice": result.voice,
        "text": clean,
        "synth_ms": result.synth_ms,
        "audio_ms": result.audio_ms,
    }
    _print(payload, as_json)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m proyecto_modelos_lenguaje.voice",
        description="Voz del agente con Phonon: verificar, listar voces y sintetizar.",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="carga el motor y sintetiza una frase")
    action.add_argument("--list-voices", action="store_true", help="lista las voces en español")
    action.add_argument("--say", metavar="TEXTO", help="sintetiza TEXTO a un WAV")
    parser.add_argument("--voice", help="voz para esta ejecución (nombre o id)")
    parser.add_argument("-o", "--output", help="ruta del WAV (por defecto, un archivo temporal)")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_ERROR if exc.code else EXIT_OK
    service = VoiceService()
    if args.voice:
        service.config = replace(service.config, voice=args.voice)
    if args.check:
        return _check(service, args.json)
    if args.list_voices:
        return _list_voices(service, args.json)
    return _say(service, args.say, args.voice, args.output, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
