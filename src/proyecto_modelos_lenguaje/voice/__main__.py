"""CLI de la voz del agente (spec 016, contracts/voice-cli.md).

    uv run python -m proyecto_modelos_lenguaje.voice --check [--json]
    uv run python -m proyecto_modelos_lenguaje.voice --list-voices [--json]
    uv run python -m proyecto_modelos_lenguaje.voice --say "Hola." [--voice Regina] [-o salida.wav]
    uv run python -m proyecto_modelos_lenguaje.voice --check --language en   # spec 028
    uv run python -m proyecto_modelos_lenguaje.voice --audition [--out DIR]  # spec 036

Códigos de salida: 0 OK · 1 argumentos o error de síntesis · 2 motor no disponible.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from ..config import PROJECT_ROOT
from .audio import to_wav_bytes
from .config import VoiceConfigError
from .engine import UnknownVoiceError, VoiceService, VoiceUnavailableError
from .text import clean_for_speech

CHECK_PHRASE = "Hola, soy el asistente de Ingenio Manuelita."
CHECK_PHRASES = {"en": "Hi, I'm Valeria, Manuelita's virtual assistant."}
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
        phrase = CHECK_PHRASES.get(service.config.language, CHECK_PHRASE)
        result = service.synthesize(phrase)
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


# Spec 036 (research R6): voces femeninas de español del catálogo que no son castellanas.
AUDITION_VOICES = (
    "Rebeca",
    "Regina",
    "Ximena",
    "Celia",
    "Alicia",
    "Danae",
    "Azucena",
    "Jimena",
    "Yael",
)
AUDITION_PHRASE = (
    "¡Hola, ve! Soy Valer-IA, la asistente virtual de Manuelita. Listo pues, te cuento de su "
    "historia."
)


def _slug(text: str) -> str:
    from ..agent.structured import normalize

    return re.sub(r"[^a-z0-9]+", "_", normalize(text)).strip("_") or "x"


def _audition_dir(out: str | None) -> Path:
    if out:
        target = Path(out).expanduser().resolve()
    else:
        from ..agent.config import resolve_state_dir

        target = resolve_state_dir() / "voice_audition"
    root = PROJECT_ROOT.resolve()
    if target == root or root in target.parents:
        raise ValueError(f"La audición se escribe fuera del repositorio, no en {target}.")
    return target


def _audition(service: VoiceService, out: str | None, as_json: bool) -> int:
    """Spec 036: la frase caleña con cada voz candidata y cada expresión hablada (WAV + índice).

    Los audios quedan fuera del repositorio; el equipo los escucha, elige la voz y marca las
    expresiones mal pronunciadas (``spoken = false`` en ``config/caleno.toml``).
    """
    from ..agent.style import load_lexicon

    try:
        target = _audition_dir(out)
        service.ensure_loaded()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_ERROR
    except VoiceUnavailableError:
        _print(service.status().to_dict(), as_json)
        return EXIT_UNAVAILABLE
    target.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for voice in AUDITION_VOICES:
        name = f"voz_{_slug(voice)}.wav"
        try:
            result = service.synthesize(clean_for_speech(AUDITION_PHRASE), voice)
        except UnknownVoiceError:
            rows.append({"kind": "voz", "item": voice, "file": "(no disponible)"})
            continue
        (target / name).write_bytes(to_wav_bytes(result.samples, result.sample_rate))
        rows.append({"kind": "voz", "item": voice, "file": name})
    for expression in load_lexicon().approved:
        if not expression.spoken:
            continue
        name = f"expresion_{_slug(expression.text)}.wav"
        result = service.synthesize(clean_for_speech(expression.example or expression.text))
        (target / name).write_bytes(to_wav_bytes(result.samples, result.sample_rate))
        rows.append({"kind": "expresión", "item": expression.text, "file": name})
    index = [
        "Audición de voces y expresiones caleñas (spec 036).",
        f"Frase de las voces: {AUDITION_PHRASE}",
        f"Voz configurada para las expresiones: {service.config.voice}",
        "",
        *(f"{row['kind']}\t{row['item']}\t{row['file']}" for row in rows),
    ]
    (target / "index.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    _print({"output": str(target), "files": len(rows), "index": "index.txt"}, as_json)
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
    action.add_argument(
        "--audition",
        action="store_true",
        help="spec 036: frase caleña con cada voz candidata y cada expresión hablada",
    )
    parser.add_argument("--out", help="carpeta de la audición (por defecto, en el estado local)")
    parser.add_argument("--voice", help="voz para esta ejecución (nombre o id)")
    parser.add_argument("-o", "--output", help="ruta del WAV (por defecto, un archivo temporal)")
    parser.add_argument("--json", action="store_true", help="salida JSON")
    parser.add_argument(
        "--language",
        default=None,
        help="spec 028: idioma de la voz (es por defecto; en usa el modelo phonon-31m-en)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_ERROR if exc.code else EXIT_OK
    service = VoiceService()
    if args.language and args.language != service.config.language:
        try:
            service = VoiceService(service.config.for_language(args.language))
        except VoiceConfigError as exc:
            print(str(exc), file=sys.stderr)
            return EXIT_ERROR
    if args.voice:
        service.config = replace(service.config, voice=args.voice)
    if args.check:
        return _check(service, args.json)
    if args.list_voices:
        return _list_voices(service, args.json)
    if args.audition:
        return _audition(service, args.out, args.json)
    return _say(service, args.say, args.voice, args.output, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
