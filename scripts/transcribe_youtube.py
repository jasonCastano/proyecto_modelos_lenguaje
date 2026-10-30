"""Transcribe YouTube videos without captions and store the transcripts as bronze artifacts.

Usage:
    uv run --extra asr python scripts/transcribe_youtube.py --url URL [--url URL ...]

Audio is downloaded to a temporary directory and deleted after transcription;
only the WebVTT transcript and a provenance JSON are written to the bronze layer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.config import load_config
from proyecto_modelos_lenguaje.coverage import infer_evidence, normalize_text
from proyecto_modelos_lenguaje.models import TargetState
from proyecto_modelos_lenguaje.storage import BronzeStorage, sha256_text
from proyecto_modelos_lenguaje.transcription import (
    build_vtt,
    provenance_payload,
    transcribe_audio,
)
from proyecto_modelos_lenguaje.utils import utcnow


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _download_audio(url: str, directory: Path) -> tuple[Path, dict[str, Any]]:
    import yt_dlp

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio/best",
        "outtmpl": str(directory / "%(id)s.%(ext)s"),
        "socket_timeout": 60,
        "js_runtimes": {"node": {}},
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    if info is None:
        raise RuntimeError("empty yt-dlp response")
    if info.get("entries"):
        info = next(entry for entry in info["entries"] if entry)
    candidates = [path for path in directory.iterdir() if path.is_file()]
    if not candidates:
        raise RuntimeError("audio download produced no file")
    return candidates[0], info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", required=True, dest="urls")
    parser.add_argument("--config", default="config/official_channels.toml")
    parser.add_argument("--campaign", default="2026-10-youtube-asr-transcripts")
    parser.add_argument("--model", default="small")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    settings = config.settings
    database = settings.bronze_dir / "_meta" / "bronze.sqlite3"
    storage = BronzeStorage(settings.bronze_dir, limit_bytes=settings.storage_limit_bytes)
    results: list[dict[str, Any]] = []

    with Catalog(database) as catalog:
        catalog.create_campaign(
            campaign_id=args.campaign,
            config_hash=config.config_hash,
            tool_version="0.1.0",
            git_commit=_git_commit(),
        )
        catalog.set_campaign_status(args.campaign, "running")
        coverage_items = catalog.coverage_items()
        for url in args.urls:
            record: dict[str, Any] = {"url": url}
            try:
                with tempfile.TemporaryDirectory(prefix="bronze-asr-") as tmp:
                    audio, info = _download_audio(url, Path(tmp))
                    title = info.get("title")
                    published = info.get("upload_date")
                    published_at = (
                        f"{published[0:4]}-{published[4:6]}-{published[6:8]}T00:00:00Z"
                        if published and len(published) == 8
                        else None
                    )
                    segments, details = transcribe_audio(
                        audio,
                        model=args.model,
                        compute_type=args.compute_type,
                    )
                if not segments:
                    raise RuntimeError("no speech detected")
                note = f"Transcripción automática (faster-whisper {args.model}); audio eliminado."
                vtt_text = build_vtt(segments, note=note)
                vtt_bytes = vtt_text.encode("utf-8")
                provenance = provenance_payload(
                    video_url=url,
                    title=title,
                    published_at=published_at,
                    details=details,
                    segments=len(segments),
                ).encode("utf-8")
                canonical = f"{url}?transcript=asr" if "?" not in url else f"{url}&transcript=asr"
                stored = storage.store(
                    vtt_bytes,
                    media_type="text/vtt",
                    source_id="youtube",
                    campaign_id=args.campaign,
                )
                version = catalog.next_version(canonical)
                artifact, created = catalog.add_artifact(
                    content_hash=stored.content_hash,
                    text_hash=sha256_text(normalize_text(vtt_text)),
                    media_type="text/vtt",
                    byte_size=stored.byte_size,
                    storage_path=stored.storage_path,
                    retrieved_at=utcnow(),
                    http_status=200,
                    source_id="youtube",
                    campaign_id=args.campaign,
                    authority="first_party",
                    language="es",
                    language_method="heuristic",
                    title=title,
                    published_at=published_at,
                    version=version,
                    url_original=url,
                    url_canonical=canonical,
                    category="digital_presence",
                )
                catalog.add_url_version(
                    url_canonical=canonical,
                    artifact_id=artifact.artifact_id,
                    version=version,
                    change_reason="first_capture",
                )
                target, _ = catalog.add_target(
                    campaign_id=args.campaign,
                    source_id="youtube",
                    url_original=url,
                    url_canonical=canonical,
                    category="digital_presence",
                )
                catalog.link_artifact(
                    campaign_id=args.campaign,
                    artifact_id=artifact.artifact_id,
                    target_id=target.target_id,
                    captured_as="stored" if created else "deduped",
                )
                catalog.update_target_state(target.target_id, TargetState.STORED)
                for evidence in infer_evidence(
                    vtt_text, title=title, url=url, items=coverage_items
                ):
                    catalog.add_coverage_evidence(
                        item_id=evidence.item_id,
                        artifact_id=artifact.artifact_id,
                        confidence=evidence.confidence,
                        note=f"{evidence.note} (transcripción ASR)",
                    )
                provenance_path = storage.store(
                    provenance,
                    media_type="application/json",
                    source_id="youtube",
                    campaign_id=args.campaign,
                )
                catalog.add_artifact(
                    content_hash=provenance_path.content_hash,
                    text_hash=sha256_text(normalize_text(provenance.decode("utf-8"))),
                    media_type="application/json",
                    byte_size=provenance_path.byte_size,
                    storage_path=provenance_path.storage_path,
                    retrieved_at=utcnow(),
                    http_status=200,
                    source_id="youtube",
                    campaign_id=args.campaign,
                    authority="first_party",
                    language="es",
                    language_method="heuristic",
                    title=title,
                    published_at=published_at,
                    version=1,
                    url_original=url,
                    url_canonical=f"{canonical}&meta=1",
                    category="digital_presence",
                )
                record.update(
                    {
                        "status": "stored" if created else "deduped",
                        "title": title,
                        "segments": len(segments),
                        "characters": len(vtt_text),
                        "model": details.get("model"),
                    }
                )
            except Exception as exc:
                if args.debug:
                    import traceback

                    traceback.print_exc()
                record.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"[:400]})
            results.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)

        catalog.set_campaign_status(args.campaign, "completed")
        catalog.refresh_campaign_counters(args.campaign)

    print(json.dumps({"campaign": args.campaign, "results": results}, ensure_ascii=False, indent=2))
    return 0 if all(item.get("status") != "failed" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
