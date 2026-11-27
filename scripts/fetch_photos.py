"""Descarga las fotos sustitutas de la web desde Wikimedia Commons (spec 031, research R5).

Cada foto se baja una vez, se reduce a WebP de 1400 y 700 px y queda en ``web/public/media/fotos/``
junto con ``CREDITOS.md`` (autor, licencia y URL). Solo se aceptan CC0, dominio público, CC BY y
CC BY-SA. Uso::

    uv run python scripts/fetch_photos.py f75362180:cana f111139028:azucar ...
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "media" / "fotos"
UA = {"User-Agent": "valeria-academic-project/1.0 (photo credits)"}
ALLOWED = ("CC0", "Public domain", "CC BY ", "CC BY-SA ")
SIZES = (1400, 700)


def _plain(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def fetch(pairs: list[tuple[str, str]]) -> list[dict[str, str]]:
    ids = [pid.lstrip("f") for pid, _ in pairs]
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "pageids": "|".join(ids),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": SIZES[0],
            "format": "json",
        }
    )
    url = f"https://commons.wikimedia.org/w/api.php?{query}"
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA)))
    OUT.mkdir(parents=True, exist_ok=True)
    credits = []
    for (pid, slug), raw_id in zip(pairs, ids, strict=True):
        page = data["query"]["pages"][raw_id]
        info = page["imageinfo"][0]
        meta = info.get("extmetadata", {})
        license_name = _plain(meta.get("LicenseShortName", {}).get("value", ""))
        if not license_name.startswith(ALLOWED) and license_name != "CC0":
            raise SystemExit(f"{pid}: licencia no permitida ({license_name})")
        raw = urllib.request.urlopen(urllib.request.Request(info["thumburl"], headers=UA)).read()
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        for width in SIZES:
            copy = image.copy()
            copy.thumbnail((width, width * 2))
            copy.save(OUT / f"{slug}-{width}.webp", quality=58, method=6)
        credits.append(
            {
                "id": pid,
                "slug": slug,
                "title": page["title"].removeprefix("File:"),
                "author": _plain(meta.get("Artist", {}).get("value", "")) or "Autor desconocido",
                "license": license_name,
                "source": info["descriptionurl"],
                "width": image.width,
                "height": image.height,
            }
        )
    return credits


def write_credits(credits: list[dict[str, str]]) -> None:
    lines = [
        "# Créditos de las fotografías (spec 031)",
        "",
        "Fotos sustitutas de Wikimedia Commons: ilustran los cultivos y productos sobre los que",
        "responde Valer-IA. No son fotos de Manuelita. Se reducen a WebP de 1400 y 700 px; las",
        "CC BY-SA se comparten con la misma licencia.",
        "",
        "| Archivo | Tema | Autor | Licencia | Fuente |",
        "|---|---|---|---|---|",
    ]
    for item in credits:
        lines.append(
            f"| `{item['slug']}-1400.webp` | {item['title']} | {item['author']} | "
            f"{item['license']} | [{item['id']}]({item['source']}) |"
        )
    (OUT / "CREDITOS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "creditos.json").write_text(
        json.dumps(credits, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str]) -> int:
    pairs = [tuple(arg.split(":", 1)) for arg in argv]
    credits = fetch(pairs)  # type: ignore[arg-type]
    write_credits(credits)
    for item in credits:
        print(item["slug"], item["license"], item["author"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
