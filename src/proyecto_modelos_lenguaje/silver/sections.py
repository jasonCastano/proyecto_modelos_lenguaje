"""Build hierarchical sections from extracted blocks."""

from __future__ import annotations

from .models import ExtractedBlock, Section, make_section_id

NO_SECTION = "sin sección"
UNTITLED = "Documento sin título"


def assign_offsets(blocks: list[ExtractedBlock]) -> int:
    cursor = 0
    for block in blocks:
        block.char_start = cursor
        block.char_end = cursor + len(block.text)
        cursor = block.char_end + 2
    return max(0, cursor - 2)


def _span(
    blocks: list[ExtractedBlock],
) -> tuple[int | None, int | None, float | None, float | None]:
    pages = [block.page for block in blocks if block.page is not None]
    starts = [block.time_start for block in blocks if block.time_start is not None]
    ends = [block.time_end for block in blocks if block.time_end is not None]
    return (
        min(pages) if pages else None,
        max(pages) if pages else None,
        min(starts) if starts else None,
        max(ends) if ends else None,
    )


def _section(
    doc_id: str,
    order: int,
    title: str,
    path: list[str],
    level: int,
    blocks: list[ExtractedBlock],
    char_start: int,
    char_end: int,
) -> Section:
    page_start, page_end, time_start, time_end = _span(blocks)
    return Section(
        section_id=make_section_id(doc_id, order),
        title=title,
        path=path,
        level=level,
        order=order,
        char_start=char_start,
        char_end=max(char_start + 1, char_end),
        page_start=page_start,
        page_end=page_end,
        time_start=time_start,
        time_end=time_end,
    )


def _heading_sections(
    doc_id: str,
    blocks: list[ExtractedBlock],
    *,
    default_title: str,
) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    current: dict[str, object] | None = None

    def close(end: int) -> None:
        nonlocal current
        if current is None:
            return
        section = _section(
            doc_id,
            len(sections),
            str(current["title"]),
            list(current["path"]),  # type: ignore[arg-type]
            int(current["level"]),
            list(current["blocks"]),  # type: ignore[arg-type]
            int(current["start"]),
            end,
        )
        sections.append(section)
        current = None

    for block in blocks:
        if block.level:
            close(block.char_start)
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            current = {
                "title": block.text,
                "path": [title for _, title in stack],
                "level": block.level,
                "blocks": [block],
                "start": block.char_start,
            }
        else:
            if current is None:
                current = {
                    "title": default_title,
                    "path": [default_title],
                    "level": 0,
                    "blocks": [],
                    "start": block.char_start,
                }
            current["blocks"].append(block)
    if current is not None:
        last_end = max(block.char_end for block in current["blocks"])
        close(last_end)
    return sections


def _pdf_sections(
    doc_id: str,
    blocks: list[ExtractedBlock],
    *,
    outline: list[dict[str, object]],
    default_title: str,
) -> list[Section]:
    by_page: dict[int, dict[str, object]] = {}
    for entry in outline:
        page = entry.get("page")
        if isinstance(page, int) and page not in by_page:
            by_page[page] = entry
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    current: dict[str, object] | None = None

    def close(end: int) -> None:
        nonlocal current
        if current is None:
            return
        sections.append(
            _section(
                doc_id,
                len(sections),
                str(current["title"]),
                list(current["path"]),  # type: ignore[arg-type]
                int(current["level"]),
                list(current["blocks"]),  # type: ignore[arg-type]
                int(current["start"]),
                end,
            )
        )
        current = None

    for block in blocks:
        entry = by_page.get(block.page) if block.page is not None else None
        if entry is not None:
            level = int(entry.get("level", 1))
            title = str(entry.get("title") or default_title)
            if current is None or current["title"] != title:
                close(block.char_start)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                current = {
                    "title": title,
                    "path": [item for _, item in stack],
                    "level": level,
                    "blocks": [],
                    "start": block.char_start,
                }
        if current is None:
            current = {
                "title": default_title,
                "path": [default_title],
                "level": 0,
                "blocks": [],
                "start": block.char_start,
            }
        current["blocks"].append(block)
    if current is not None:
        last_end = max(block.char_end for block in current["blocks"])
        close(last_end)
    return sections


def build_sections(
    *,
    doc_id: str,
    blocks: list[ExtractedBlock],
    document_title: str | None,
    outline: list[dict[str, object]] | None = None,
) -> tuple[list[Section], bool]:
    """Return sections and whether the document lacked detectable headings."""
    assign_offsets(blocks)
    default_title = document_title if document_title and document_title != UNTITLED else NO_SECTION
    has_headings = any(block.level for block in blocks)
    if outline and any(block.page is not None for block in blocks):
        sections = _pdf_sections(
            doc_id, blocks, outline=outline, default_title=default_title or NO_SECTION
        )
        has_headings = True
    else:
        sections = _heading_sections(doc_id, blocks, default_title=default_title or NO_SECTION)
    return sections, has_headings
