"""Visual audit for the Metrics tab.

The script opens the running Streamlit app in a real browser, walks the viewport
matrix, measures bounding boxes and writes a JSON report plus screenshots.

The browser is a development dependency: ``uv run playwright install chromium``
or a locally installed Chrome/Edge/Firefox is required.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from playwright.sync_api import Browser, Page, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from proyecto_modelos_lenguaje.metrics_layout import VIEWPORTS, ViewportProfile, profile_by_name

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "specs" / "010-metrics-panel-layout" / "contracts" / "layout-audit.schema.json"
METRIC_SELECTOR = '.st-key-metrics-kpis [data-testid="stMetric"]'
LABEL_SELECTOR = '.st-key-metrics-kpis [data-testid="stMetricLabel"]'
VALUE_SELECTOR = '.st-key-metrics-kpis [data-testid="stMetricValue"]'
CHART_SELECTOR = (
    '.st-key-metrics-view [data-testid="stVegaLiteChart"], '
    '.st-key-metrics-view [data-testid="stArrowVegaLiteChart"]'
)
EXPANDER_SELECTOR = '.st-key-metrics-view [data-testid="stExpander"]'
CAPTION_SELECTOR = '.st-key-metrics-view [data-testid="stCaptionContainer"]'
HEADING_SELECTOR = ".st-key-metrics-view h4"
WARNING_TEXT = "Los datos de oro no están completos"
VIEWPORT_MARGIN = 1.0
MIN_CHART_HEIGHT = 260


@dataclass(frozen=True, slots=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def intersection_area(self, other: Box) -> float:
        left = max(self.x, other.x)
        right = min(self.right, other.right)
        top = max(self.y, other.y)
        bottom = min(self.bottom, other.bottom)
        if right <= left or bottom <= top:
            return 0.0
        return (right - left) * (bottom - top)


def _box(locator: Any) -> Box | None:
    try:
        raw = locator.bounding_box()
    except PlaywrightError:
        return None
    if raw is None:
        return None
    return Box(
        x=float(raw["x"]),
        y=float(raw["y"]),
        width=float(raw["width"]),
        height=float(raw["height"]),
    )


def _contains(first: Any, second: Any) -> bool:
    try:
        return bool(
            first.evaluate(
                "(el, other) => el === other || el.contains(other) || other.contains(el)",
                second.element_handle(),
            )
        )
    except PlaywrightError:
        return False


def _intersection(a: Box, b: Box) -> float:
    return a.intersection_area(b)


def _find_overlaps(
    blocks: list[tuple[str, Any]],
    viewport: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, (first_name, first) in enumerate(blocks):
        first_box = _box(first)
        if first_box is None:
            continue
        for second_name, second in blocks[index + 1 :]:
            if _contains(first, second):
                continue
            second_box = _box(second)
            if second_box is None:
                continue
            area = _intersection(first_box, second_box)
            if area > 0.5:
                findings.append(
                    {
                        "viewport": viewport,
                        "kind": "overlap",
                        "element_a": first_name,
                        "element_b": second_name,
                        "area": round(area, 3),
                        "detail": f"{first_name} y {second_name} se superponen en {area:.1f} px².",
                        "severity": "error",
                    }
                )
    return findings


def _columns_from_cards(cards: list[Any]) -> int:
    """Infer columns from distinct x positions of cards in the first row."""
    boxes = [box for card in cards if (box := _box(card)) is not None]
    if not boxes:
        return 0
    first_y = min(box.y for box in boxes)
    first_row = [round(box.x / 10) * 10 for box in boxes if abs(box.y - first_y) <= 4]
    return max(1, len(set(first_row)))


def _clipping_findings(page: Page, viewport: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for selector, kind in ((LABEL_SELECTOR, "label"), (VALUE_SELECTOR, "valor")):
        locator = page.locator(selector)
        for index in range(locator.count()):
            item = locator.nth(index)
            try:
                metrics = item.evaluate(
                    """(el) => {
                        const style = getComputedStyle(el);
                        return {
                            scrollWidth: el.scrollWidth,
                            clientWidth: el.clientWidth,
                            scrollHeight: el.scrollHeight,
                            clientHeight: el.clientHeight,
                            textOverflow: style.textOverflow,
                            text: el.innerText || '',
                        };
                    }"""
                )
            except PlaywrightError:
                continue
            clipped = (
                metrics["scrollWidth"] > metrics["clientWidth"] + 1
                or metrics["scrollHeight"] > metrics["clientHeight"] + 1
                or metrics["textOverflow"] == "ellipsis"
            )
            if clipped:
                findings.append(
                    {
                        "viewport": viewport,
                        "kind": "clipping",
                        "element_a": f"{selector}[{index}]",
                        "detail": (
                            f"El {kind} '{metrics['text']}' se recorta "
                            f"(scroll {metrics['scrollWidth']}x{metrics['scrollHeight']}, "
                            f"cliente {metrics['clientWidth']}x{metrics['clientHeight']}, "
                            f"text-overflow={metrics['textOverflow']})."
                        ),
                        "severity": "error" if kind == "valor" else "warning",
                    }
                )
    return findings


def _open_metrics(page: Page, timeout_ms: int) -> None:
    with contextlib.suppress(PlaywrightError):
        page.wait_for_selector(
            '[role="tab"], .st-key-metrics-kpis',
            state="attached",
            timeout=timeout_ms,
        )
    tabs = page.locator('[role="tab"]')
    if tabs.count() > 0:
        tab = page.get_by_role("tab", name="Métricas")
        if tab.count() == 0:
            tab = page.get_by_text("Métricas", exact=True)
        if tab.count() > 0:
            tab.first.click()
            with contextlib.suppress(PlaywrightError):
                page.wait_for_function(
                    """() => {
                        const tabs = [...document.querySelectorAll('[role="tab"]')];
                        const target = tabs.find((item) =>
                            (item.textContent || '').trim() === 'Métricas'
                        );
                        return target?.getAttribute('aria-selected') === 'true';
                    }""",
                    timeout=timeout_ms,
                )
    page.wait_for_timeout(800)


def _close_sidebar(page: Page) -> None:
    selectors = (
        '[data-testid="stSidebarCollapseButton"]',
        'button[aria-label="Close sidebar"]',
        'button[aria-label="Cerrar barra lateral"]',
    )
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() == 0:
            continue
        try:
            locator.first.click()
            page.wait_for_timeout(300)
            return
        except PlaywrightError:
            continue


def _warning_box(page: Page) -> Box | None:
    warning = page.get_by_text(WARNING_TEXT, exact=False)
    if warning.count() == 0:
        return None
    return _box(warning.first)


def _data_state_result(
    page: Page,
    state: str,
    cards: list[Any],
) -> dict[str, Any]:
    warning = page.get_by_text(WARNING_TEXT, exact=False)
    visible = warning.count() > 0
    warning_box = _warning_box(page)
    separate = True
    if warning_box is not None:
        for card in cards:
            card_box = _box(card)
            if card_box is not None and warning_box.intersection_area(card_box) > 0.5:
                separate = False
                break
    expected_visible = state in {"incomplete", "unknown"}
    passed = visible == expected_visible and separate
    return {
        "state": state,
        "warning_visible": visible,
        "warning_separate": separate,
        "passed": passed,
    }


def _audit_viewport(
    page: Page,
    profile: ViewportProfile,
    output: Path,
    *,
    screenshot: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _open_metrics(page, 30_000)
    if not profile.sidebar_open:
        _close_sidebar(page)
    page.wait_for_selector(".st-key-metrics-kpis", timeout=30_000)
    page.wait_for_selector(METRIC_SELECTOR, timeout=30_000)
    page.wait_for_timeout(800)

    cards = page.locator(METRIC_SELECTOR).all()
    findings: list[dict[str, Any]] = []
    columns = _columns_from_cards(cards)
    if columns != profile.expected_columns:
        findings.append(
            {
                "viewport": profile.name,
                "kind": "wrong_columns",
                "element_a": METRIC_SELECTOR,
                "detail": (
                    f"Se detectaron {columns} columnas; se esperaban {profile.expected_columns}."
                ),
                "severity": "error",
            }
        )
    if len(cards) != 8:
        findings.append(
            {
                "viewport": profile.name,
                "kind": "missing_element",
                "element_a": METRIC_SELECTOR,
                "detail": f"Se encontraron {len(cards)} tarjetas; se esperaban 8.",
                "severity": "error",
            }
        )

    charts = page.locator(CHART_SELECTOR).all()
    if len(charts) != 2:
        findings.append(
            {
                "viewport": profile.name,
                "kind": "missing_element",
                "element_a": CHART_SELECTOR,
                "detail": f"Se encontraron {len(charts)} gráficos; se esperaban 2.",
                "severity": "error",
            }
        )
    expanders = page.locator(EXPANDER_SELECTOR).all()
    if len(expanders) != 3:
        findings.append(
            {
                "viewport": profile.name,
                "kind": "missing_element",
                "element_a": EXPANDER_SELECTOR,
                "detail": f"Se encontraron {len(expanders)} expanders; se esperaban 3.",
                "severity": "error",
            }
        )

    blocks: list[tuple[str, Any]] = []
    blocks.extend((f"tarjeta-{index}", card) for index, card in enumerate(cards, start=1))
    blocks.extend(
        (f"titulo-{index}", heading)
        for index, heading in enumerate(page.locator(HEADING_SELECTOR).all(), start=1)
    )
    blocks.extend((f"grafico-{index}", chart) for index, chart in enumerate(charts, start=1))
    blocks.extend(
        (f"caption-{index}", caption)
        for index, caption in enumerate(page.locator(CAPTION_SELECTOR).all(), start=1)
    )
    blocks.extend(
        (f"expander-{index}", expander) for index, expander in enumerate(expanders, start=1)
    )
    findings.extend(_find_overlaps(blocks, profile.name))
    findings.extend(_clipping_findings(page, profile.name))

    horizontal_scroll = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    )
    if horizontal_scroll:
        findings.append(
            {
                "viewport": profile.name,
                "kind": "horizontal_scroll",
                "element_a": "document.documentElement",
                "detail": "La página presenta desplazamiento horizontal.",
                "severity": "error",
            }
        )

    screenshots: list[str] = []
    if screenshot:
        path = output / f"{profile.name}.png"
        page.screenshot(path=str(path), full_page=True)
        screenshots.append(path.name)

    viewport_passed = (
        not any(finding["severity"] == "error" for finding in findings) and not horizontal_scroll
    )
    return (
        {
            "name": profile.name,
            "width": profile.width,
            "height": profile.height,
            "zoom": profile.zoom,
            "columns": columns,
            "horizontal_scroll": bool(horizontal_scroll),
            "screenshots": screenshots,
            "passed": viewport_passed,
        },
        findings,
    )


def _launch_browser(playwright: Any, name: str, headless: bool) -> tuple[Browser, str]:
    attempts: list[tuple[str, Any]] = []
    if name in {"auto", "chromium"}:
        attempts.append(("chromium", lambda: playwright.chromium.launch(headless=headless)))
    if name in {"auto", "chrome"}:
        attempts.append(
            ("chrome", lambda: playwright.chromium.launch(headless=headless, channel="chrome"))
        )
    if name in {"auto", "msedge"}:
        attempts.append(
            ("msedge", lambda: playwright.chromium.launch(headless=headless, channel="msedge"))
        )
    if name in {"auto", "firefox"}:
        attempts.append(("firefox", lambda: playwright.firefox.launch(headless=headless)))

    errors: list[str] = []
    for browser_name, factory in attempts:
        try:
            return factory(), browser_name
        except PlaywrightError as exc:
            errors.append(f"{browser_name}: {exc}")
    raise RuntimeError(
        "No se pudo iniciar un navegador. Instala Chromium con "
        "`uv run playwright install chromium` o usa `--browser chrome`. " + " | ".join(errors)
    )


def _state_from_page(page: Page, requested: str) -> str:
    if requested != "auto":
        return requested
    return "incomplete" if page.get_by_text(WARNING_TEXT, exact=False).count() else "complete"


def _validate_report(report: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)


def run(args: argparse.Namespace) -> int:
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    profiles = [profile_by_name(name) for name in args.profile] if args.profile else list(VIEWPORTS)
    findings: list[dict[str, Any]] = []
    viewports: list[dict[str, Any]] = []
    data_states: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser, browser_name = _launch_browser(playwright, args.browser, not args.headed)
        try:
            for profile in profiles:
                context = browser.new_context(
                    viewport={"width": profile.width, "height": profile.height},
                    device_scale_factor=profile.device_scale_factor,
                    reduced_motion="reduce",
                )
                page = context.new_page()
                page.set_default_timeout(args.timeout * 1000)
                page.goto(args.url, wait_until="domcontentloaded", timeout=args.timeout * 1000)
                page.wait_for_timeout(2_500)
                with contextlib.suppress(PlaywrightError):
                    page.wait_for_selector('[role="tab"]', timeout=args.timeout * 1000)
                result, viewport_findings = _audit_viewport(
                    page,
                    profile,
                    output,
                    screenshot=not args.no_screenshots,
                )
                viewports.append(result)
                findings.extend(viewport_findings)
                if profile is profiles[0]:
                    state = _state_from_page(page, args.state)
                    data_states.append(
                        _data_state_result(page, state, page.locator(METRIC_SELECTOR).all())
                    )
                context.close()
        finally:
            browser.close()

    passed = not any(finding["severity"] == "error" for finding in findings)
    passed = passed and all(item["passed"] for item in viewports)
    passed = passed and all(item["passed"] for item in data_states)
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "app_url": args.url,
        "browser": browser_name,
        "viewports": viewports,
        "data_states": data_states,
        "findings": findings,
        "passed": passed,
    }
    _validate_report(report)
    report_path = output / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(report_path),
                "passed": passed,
                "viewports": len(viewports),
                "findings": len(findings),
            },
            ensure_ascii=False,
        )
    )
    return 0 if passed else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita el layout de la pestaña Métricas.")
    parser.add_argument("--url", default="http://localhost:8501", help="URL de la app.")
    parser.add_argument(
        "--output",
        default="artifacts/metrics-layout",
        help="Directorio para report.json y capturas.",
    )
    parser.add_argument(
        "--browser",
        default="auto",
        choices=("auto", "chromium", "chrome", "msedge", "firefox"),
        help="Navegador a usar; auto intenta Chromium, Chrome y Edge.",
    )
    parser.add_argument("--headed", action="store_true", help="Muestra el navegador.")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout en segundos.")
    parser.add_argument(
        "--profile",
        action="append",
        choices=tuple(profile.name for profile in VIEWPORTS),
        help="Perfil a auditar; repetible. Por defecto, todos.",
    )
    parser.add_argument(
        "--state",
        default="auto",
        choices=("auto", "complete", "incomplete", "unknown"),
        help="Estado de datos esperado.",
    )
    parser.add_argument("--no-screenshots", action="store_true", help="No guarda capturas.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except (RuntimeError, PlaywrightError) as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
