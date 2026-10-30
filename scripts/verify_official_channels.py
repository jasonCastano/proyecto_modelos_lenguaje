"""Audit the official-channel corpus: sources, policy exclusions and transcript coverage.

Usage:
    uv run python scripts/verify_official_channels.py [--json]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from proyecto_modelos_lenguaje.config import load_config

LINKTREE_TARGETS = {
    "https://www.manuelita.com/": "portal",
    "https://www.manuelita.com/sostenibilidad": "sostenibilidad",
    "https://www.manuelita.com/talento": "talento",
    "https://fundacionmanuelita.org/": "fundacion",
}

SOURCE_LABELS = {
    "youtube": "YouTube",
    "instagram": "Instagram",
    "linktree": "Linktree",
    "fundacion_manuelita": "Fundación Manuelita",
    "official_site": "Sitio oficial",
}


def _distinct_transcripts(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT COUNT(DISTINCT CASE "
        "WHEN url_canonical LIKE '%?sub=%' THEN "
        "replace(replace(url_canonical,'?sub=es',''),'?sub=en','') "
        "WHEN url_canonical LIKE '%transcript=asr' THEN "
        "replace(url_canonical,'?transcript=asr','') "
        "END) FROM v_active_artifacts "
        "WHERE source_id='youtube' AND media_type='text/vtt'"
    ).fetchone()
    return int(row[0] or 0)


def _linktree_coverage(connection: sqlite3.Connection) -> list[dict[str, object]]:
    results = []
    for url, label in LINKTREE_TARGETS.items():
        prefix = url.rstrip("/")
        row = connection.execute(
            "SELECT COUNT(*) FROM v_active_artifacts WHERE url_canonical LIKE ?",
            (f"{prefix}%",),
        ).fetchone()
        results.append({"target": url, "label": label, "artifacts": int(row[0])})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/official_channels.toml")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    database = config.settings.bronze_dir / "_meta" / "bronze.sqlite3"
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    sources = [
        "official_site",
        "youtube",
        "fundacion_manuelita",
        "instagram",
        "linktree",
    ]
    counts = {}
    for source in sources:
        row = connection.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(byte_size),0) AS b "
            "FROM v_active_artifacts WHERE source_id = ?",
            (source,),
        ).fetchone()
        counts[source] = {"artifacts": int(row["n"]), "bytes": int(row["b"])}
    policies = []
    for row in connection.execute(
        "SELECT source_id, decision, reason, COUNT(*) AS n FROM policy_checks "
        "WHERE source_id IN ('instagram','linktree') GROUP BY source_id, decision, reason"
    ):
        policies.append(dict(row))
    payload = {
        "sources": counts,
        "youtube_transcripts": _distinct_transcripts(connection),
        "linktree_targets": _linktree_coverage(connection),
        "policy_checks": policies,
        "active_total": connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(byte_size),0) FROM v_active_artifacts"
        ).fetchone()[0:2],
        "database": Path(database).as_posix(),
    }
    connection.close()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("Fuente                Artefactos        Bytes")
    print("-" * 46)
    for source, data in counts.items():
        label = SOURCE_LABELS.get(source, source)
        print(f"{label:<21} {data['artifacts']:>8} {data['bytes']:>12,}")
    print()
    print(f"YouTube: {payload['youtube_transcripts']} videos con transcripción")
    print()
    print("Destinos del Linktree:")
    for item in payload["linktree_targets"]:
        status = "cubierto" if item["artifacts"] else "sin artefactos"
        print(f"  - {item['label']:<14} {status:<15} {item['target']}")
    print()
    print("Política de acceso:")
    for item in policies:
        print(f"  - {item['source_id']}: {item['decision']} ({item['reason']}) x{item['n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
