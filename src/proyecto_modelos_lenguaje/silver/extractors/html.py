"""HTML main-content extraction with trafilatura and an lxml fallback."""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

import trafilatura
from lxml import html as lxml_html

from ..models import ExtractedBlock, ExtractedDocument


def _xml_blocks(root: ElementTree.Element) -> list[ExtractedBlock]:
    blocks: list[ExtractedBlock] = []

    def visit(node: ElementTree.Element) -> None:
        tag = node.tag.lower()
        text = " ".join("".join(node.itertext()).split())
        if tag == "head" and text:
            raw_level = node.attrib.get("rend", "h2")
            match = re.search(r"([1-6])", raw_level)
            blocks.append(ExtractedBlock(text=text, level=int(match.group(1)) if match else 2))
            return
        if tag in {"p", "quote", "item", "list"} and text:
            blocks.append(ExtractedBlock(text=text))
            return
        if tag == "table":
            rows = []
            for row in node.iter():
                if row.tag.lower() in {"row", "tr"}:
                    cells = [
                        " ".join("".join(cell.itertext()).split())
                        for cell in row
                        if cell.tag.lower() in {"cell", "td", "th"}
                    ]
                    if any(cells):
                        rows.append(" | ".join(cells))
            if rows:
                blocks.append(ExtractedBlock(text="\n".join(rows)))
            return
        for child in node:
            visit(child)

    visit(root)
    return blocks


def _fallback_blocks(raw: str) -> tuple[list[ExtractedBlock], str | None]:
    try:
        tree = lxml_html.fromstring(raw)
    except ValueError, TypeError:
        return [], None
    for bad in tree.xpath("//script|//style|//nav|//header|//footer|//aside|//form|//noscript"):
        parent = bad.getparent()
        if parent is not None:
            parent.remove(bad)
    containers = tree.xpath("//main|//article")
    container = max(containers, key=lambda node: len(node.text_content()), default=tree)
    blocks: list[ExtractedBlock] = []
    title: str | None = None
    for node in container.iter():
        tag = node.tag.lower() if isinstance(node.tag, str) else ""
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            text = " ".join(node.text_content().split())
            if text:
                level = int(tag[1])
                if title is None and level == 1:
                    title = text
                blocks.append(ExtractedBlock(text=text, level=level))
        elif tag in {"p", "li"}:
            text = " ".join(node.text_content().split())
            if text and len(text) > 20:
                blocks.append(ExtractedBlock(text=text))
    return blocks, title


def extract_html(data: bytes, *, url: str | None = None) -> ExtractedDocument:
    raw = data.decode("utf-8", errors="replace")
    metadata: dict[str, Any] = {}
    blocks: list[ExtractedBlock] = []
    title: str | None = None
    try:
        extracted = trafilatura.extract(
            raw,
            url=url,
            output_format="xml",
            include_formatting=True,
            include_tables=True,
            favor_precision=True,
            with_metadata=True,
            deduplicate=False,
        )
    except Exception:
        extracted = None
    if extracted:
        try:
            root = ElementTree.fromstring(extracted)
        except ElementTree.ParseError:
            root = None
        if root is not None:
            metadata = dict(root.attrib)
            title = metadata.get("title")
            blocks = _xml_blocks(root)
    if not blocks:
        blocks, fallback_title = _fallback_blocks(raw)
        title = title or fallback_title
    if not title:
        for block in blocks:
            if block.level:
                title = block.text
                break
    return ExtractedDocument(
        title=title,
        blocks=blocks,
        metadata=metadata,
        skip_reason=None if blocks else "no_text",
    )
