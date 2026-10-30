"""Structured JSON/XML extraction."""

from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree

from ..models import ExtractedBlock, ExtractedDocument


def _flatten(value: Any, prefix: str = "") -> list[str]:
    lines: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value, key=lambda item: str(item)):
            label = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten(value[key], label))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            label = f"{prefix}[{index}]"
            lines.extend(_flatten(item, label))
    else:
        if value is None or value == "":
            return lines
        lines.append(f"{prefix}: {value}")
    return lines


def extract_json(data: bytes, *, title: str | None = None) -> ExtractedDocument:
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return ExtractedDocument(
            title=title, blocks=[], metadata={}, skip_reason="invalid_json", flags=set()
        )
    lines = _flatten(payload)
    document_title = None
    if isinstance(payload, dict):
        document_title = payload.get("title") or payload.get("page_title")
    document_title = document_title or title
    blocks: list[ExtractedBlock] = []
    if document_title:
        blocks.append(ExtractedBlock(text=str(document_title), level=1))
    if lines:
        blocks.append(ExtractedBlock(text="\n".join(lines)))
    return ExtractedDocument(
        title=str(document_title) if document_title else None,
        blocks=blocks,
        metadata={"keys": len(lines)},
        skip_reason=None if lines else "no_text",
    )


def _xml_text(node: ElementTree.Element) -> str:
    return " ".join("".join(node.itertext()).split())


def extract_xml(data: bytes, *, url: str | None = None) -> ExtractedDocument:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return ExtractedDocument(title=None, blocks=[], metadata={}, skip_reason="invalid_xml")
    tag = root.tag.lower()
    if "urlset" in tag or "sitemapindex" in tag or (url and "sitemap" in url):
        return ExtractedDocument(
            title=None,
            blocks=[],
            metadata={"root": root.tag},
            skip_reason="navigation_artifact",
        )
    blocks: list[ExtractedBlock] = []
    for child in root:
        text = _xml_text(child)
        if text:
            blocks.append(ExtractedBlock(text=text))
    return ExtractedDocument(
        title=None,
        blocks=blocks,
        metadata={"root": root.tag},
        skip_reason=None if blocks else "no_text",
    )
