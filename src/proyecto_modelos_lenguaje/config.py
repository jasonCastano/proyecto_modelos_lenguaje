"""Configuration loading, validation and hashing."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import Authority, Category, CoverageItem

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_HARD_LIMIT = 10_000_000_000
STORAGE_MINIMUM = 1_048_576
DATA_PREFIX = "data"


class ConfigError(ValueError):
    """Raised when a configuration file is missing, malformed or unsafe."""


@dataclass(frozen=True, slots=True)
class Settings:
    data_root: Path
    storage_limit_bytes: int
    user_agent: str
    contact: str | None
    max_concurrency: int
    max_per_host: int
    default_delay_seconds: float
    max_depth: int
    request_timeout_seconds: int
    max_retries: int
    retry_backoff_seconds: float
    allowed_media_types: tuple[str, ...]

    @property
    def bronze_dir(self) -> Path:
        return self.data_root / "bronze"


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    robots: str
    tos_url: str | None
    requires_auth: bool
    allowed_paths: tuple[str, ...]
    excluded_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceConfig:
    source_id: str
    domain: str
    platform: str
    authority: str
    enabled: bool
    priority: int
    seeds: tuple[str, ...]
    sitemaps: tuple[str, ...]
    follow_links: bool
    max_depth: int
    policy: SourcePolicy
    delay_seconds: float
    max_concurrency: int
    category_hints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AppConfig:
    path: Path
    settings: Settings
    sources: tuple[SourceConfig, ...]
    exclusions_urls: tuple[str, ...]
    exclusions_domains: tuple[str, ...]
    config_hash: str


def _require(table: dict[str, Any], key: str, *, context: str) -> Any:
    if key not in table:
        raise ConfigError(f"{context}: missing required key '{key}'")
    return table[key]


def _as_int(value: Any, *, context: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ConfigError(f"{context} must be between {minimum} and {maximum}")
    return value


def _as_float(value: Any, *, context: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{context} must be a number")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ConfigError(f"{context} must be between {minimum} and {maximum}")
    return number


def _as_str(value: Any, *, context: str, minimum: int = 1, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{context} must be a string")
    text = value.strip()
    if not minimum <= len(text) <= maximum:
        raise ConfigError(f"{context} must have between {minimum} and {maximum} characters")
    return text


def _as_bool(value: Any, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be a boolean")
    return value


def _as_str_list(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _validate_urls(values: tuple[str, ...], *, context: str) -> tuple[str, ...]:
    for value in values:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError(f"{context}: invalid HTTP(S) URL '{value}'")
    return values


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"configuration file not found: {path}")
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc


def _resolve_data_root(raw: str, *, project_root: Path) -> Path:
    normalized = raw.replace("\\", "/").strip("/")
    if not normalized:
        raise ConfigError("settings.data_root must not be empty")
    first = normalized.split("/", 1)[0]
    if first != DATA_PREFIX:
        raise ConfigError("settings.data_root must live under the 'data' directory")
    if ".." in Path(normalized).parts:
        raise ConfigError("settings.data_root must not contain '..'")
    root = (project_root / normalized).resolve()
    try:
        root.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ConfigError("settings.data_root escapes the project root") from exc
    return root


def _parse_settings(table: dict[str, Any], *, project_root: Path) -> Settings:
    if not isinstance(table, dict):
        raise ConfigError("[settings] table is required")
    limit = _as_int(
        _require(table, "storage_limit_bytes", context="settings.storage_limit_bytes"),
        context="settings.storage_limit_bytes",
        minimum=STORAGE_MINIMUM,
        maximum=STORAGE_HARD_LIMIT,
    )
    allowed_media = _as_str_list(
        table.get("allowed_media_types", ["text/html", "application/pdf"]),
        context="settings.allowed_media_types",
    )
    return Settings(
        data_root=_resolve_data_root(
            _as_str(
                _require(table, "data_root", context="settings.data_root"),
                context="settings.data_root",
            ),
            project_root=project_root,
        ),
        storage_limit_bytes=limit,
        user_agent=_as_str(
            _require(table, "user_agent", context="settings.user_agent"),
            context="settings.user_agent",
            minimum=10,
            maximum=300,
        ),
        contact=(
            _as_str(table["contact"], context="settings.contact", maximum=200)
            if table.get("contact")
            else None
        ),
        max_concurrency=_as_int(
            table.get("max_concurrency", 8),
            context="settings.max_concurrency",
            minimum=1,
            maximum=16,
        ),
        max_per_host=_as_int(
            table.get("max_per_host", 2), context="settings.max_per_host", minimum=1, maximum=4
        ),
        default_delay_seconds=_as_float(
            table.get("default_delay_seconds", 1.0),
            context="settings.default_delay_seconds",
            minimum=0.5,
            maximum=60,
        ),
        max_depth=_as_int(
            table.get("max_depth", 3), context="settings.max_depth", minimum=0, maximum=3
        ),
        request_timeout_seconds=_as_int(
            table.get("request_timeout_seconds", 30),
            context="settings.request_timeout_seconds",
            minimum=5,
            maximum=120,
        ),
        max_retries=_as_int(
            table.get("max_retries", 3), context="settings.max_retries", minimum=0, maximum=5
        ),
        retry_backoff_seconds=_as_float(
            table.get("retry_backoff_seconds", 2.0),
            context="settings.retry_backoff_seconds",
            minimum=0.5,
            maximum=60,
        ),
        allowed_media_types=allowed_media,
    )


def _parse_policy(table: dict[str, Any], *, context: str) -> SourcePolicy:
    if not isinstance(table, dict):
        raise ConfigError(f"{context}.policy is required")
    robots = _as_str(
        _require(table, "robots", context=f"{context}.policy.robots"), context="robots"
    )
    if robots not in {"respect", "ignore_if_absent"}:
        raise ConfigError(f"{context}.policy.robots must be 'respect' or 'ignore_if_absent'")
    tos_url = table.get("tos_url")
    if tos_url is not None:
        _validate_urls((tos_url,), context=f"{context}.policy.tos_url")
    return SourcePolicy(
        robots=robots,
        tos_url=tos_url,
        requires_auth=_as_bool(
            _require(table, "requires_auth", context=f"{context}.policy.requires_auth"),
            context=f"{context}.policy.requires_auth",
        ),
        allowed_paths=_as_str_list(
            table.get("allowed_paths", []), context=f"{context}.allowed_paths"
        ),
        excluded_paths=_as_str_list(
            table.get("excluded_paths", []), context=f"{context}.excluded_paths"
        ),
    )


def _parse_source(raw: dict[str, Any], index: int) -> SourceConfig:
    context = f"sources[{index}]"
    if not isinstance(raw, dict):
        raise ConfigError(f"{context} must be a table")
    source_id = _as_str(
        _require(raw, "id", context=f"{context}.id"),
        context=f"{context}.id",
        minimum=2,
        maximum=40,
    )
    domain = _as_str(
        _require(raw, "domain", context=f"{context}.domain"),
        context=f"{context}.domain",
        minimum=4,
        maximum=253,
    ).lower()
    platform = _as_str(
        _require(raw, "platform", context=f"{context}.platform"), context=f"{context}.platform"
    )
    authority = _as_str(
        _require(raw, "authority", context=f"{context}.authority"), context=f"{context}.authority"
    )
    if authority not in {item.value for item in Authority}:
        raise ConfigError(f"{context}.authority is invalid")
    seeds = _validate_urls(
        _as_str_list(
            _require(raw, "seeds", context=f"{context}.seeds"), context=f"{context}.seeds"
        ),
        context=f"{context}.seeds",
    )
    if not seeds:
        raise ConfigError(f"{context}.seeds must contain at least one URL")
    sitemaps = _validate_urls(
        _as_str_list(raw.get("sitemaps", []), context=f"{context}.sitemaps"),
        context=f"{context}.sitemaps",
    )
    rate = raw.get("rate_limit", {})
    if not isinstance(rate, dict):
        raise ConfigError(f"{context}.rate_limit must be a table")
    hints = _as_str_list(raw.get("category_hints", []), context=f"{context}.category_hints")
    valid_categories = {item.value for item in Category}
    for hint in hints:
        if hint not in valid_categories:
            raise ConfigError(f"{context}.category_hints contains invalid category '{hint}'")
    return SourceConfig(
        source_id=source_id,
        domain=domain,
        platform=platform,
        authority=authority,
        enabled=_as_bool(raw.get("enabled", True), context=f"{context}.enabled"),
        priority=_as_int(
            raw.get("priority", 2), context=f"{context}.priority", minimum=0, maximum=3
        ),
        seeds=seeds,
        sitemaps=sitemaps,
        follow_links=_as_bool(raw.get("follow_links", True), context=f"{context}.follow_links"),
        max_depth=_as_int(
            raw.get("max_depth", 1), context=f"{context}.max_depth", minimum=0, maximum=3
        ),
        policy=_parse_policy(
            _require(raw, "policy", context=f"{context}.policy"), context=f"{context}.policy"
        ),
        delay_seconds=_as_float(
            rate.get("delay_seconds", 1.5),
            context=f"{context}.rate_limit.delay_seconds",
            minimum=0.5,
            maximum=60,
        ),
        max_concurrency=_as_int(
            rate.get("max_concurrency", 1),
            context=f"{context}.rate_limit.max_concurrency",
            minimum=1,
            maximum=4,
        ),
        category_hints=hints,
    )


def _load_exclusions(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not path.is_file():
        return (), ()
    table = _load_toml(path)
    exclusions = table.get("exclusions", {})
    if not isinstance(exclusions, dict):
        raise ConfigError("[exclusions] table is required")
    urls = _validate_urls(
        _as_str_list(exclusions.get("urls", []), context="exclusions.urls"),
        context="exclusions.urls",
    )
    domains = tuple(
        item.strip().lower().lstrip(".")
        for item in _as_str_list(exclusions.get("domains", []), context="exclusions.domains")
    )
    return urls, domains


def load_config(path: str | Path, *, project_root: Path | None = None) -> AppConfig:
    """Load and validate ``sources.toml`` plus the sibling ``exclusions.toml``."""
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = (project_root or PROJECT_ROOT) / config_path
    config_path = config_path.resolve()
    table = _load_toml(config_path)

    settings = _parse_settings(
        _require(table, "settings", context="settings"), project_root=project_root or PROJECT_ROOT
    )
    raw_sources = _require(table, "sources", context="sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ConfigError("[[sources]] must contain at least one source")
    sources = tuple(_parse_source(raw, index) for index, raw in enumerate(raw_sources))
    ids = [source.source_id for source in sources]
    if len(set(ids)) != len(ids):
        raise ConfigError("source ids must be unique")
    domains = [source.domain for source in sources]
    if len(set(domains)) != len(domains):
        raise ConfigError("source domains must be unique")

    exclusions_urls, exclusions_domains = _load_exclusions(config_path.parent / "exclusions.toml")
    digest = hashlib.sha256()
    digest.update(config_path.read_bytes())
    exclusions_path = config_path.parent / "exclusions.toml"
    if exclusions_path.is_file():
        digest.update(exclusions_path.read_bytes())
    return AppConfig(
        path=config_path,
        settings=settings,
        sources=sources,
        exclusions_urls=exclusions_urls,
        exclusions_domains=exclusions_domains,
        config_hash=digest.hexdigest(),
    )


def load_coverage_items(
    path: str | Path, *, project_root: Path | None = None
) -> tuple[CoverageItem, ...]:
    """Load and validate the 24 required information items."""
    items_path = Path(path)
    if not items_path.is_absolute():
        items_path = (project_root or PROJECT_ROOT) / items_path
    table = _load_toml(items_path.resolve())
    raw_items = table.get("items")
    if not isinstance(raw_items, list):
        raise ConfigError("coverage-items.toml must contain [[items]] entries")
    items: list[CoverageItem] = []
    for index, raw in enumerate(raw_items):
        context = f"items[{index}]"
        if not isinstance(raw, dict):
            raise ConfigError(f"{context} must be a table")
        item_id = _as_str(_require(raw, "id", context=context), context=f"{context}.id", maximum=10)
        if len(item_id) != 4 or item_id[1] != "-" or item_id[0] not in "IODH":
            raise ConfigError(f"{context}.id must follow the pattern I-01, O-01, D-01 or H-01")
        category = _as_str(
            _require(raw, "category", context=context), context=f"{context}.category"
        )
        if category not in {item.value for item in Category}:
            raise ConfigError(f"{context}.category is invalid")
        keywords = _as_str_list(
            _require(raw, "keywords", context=context), context=f"{context}.keywords"
        )
        if not keywords:
            raise ConfigError(f"{context}.keywords must not be empty")
        items.append(
            CoverageItem(
                item_id=item_id,
                category=category,
                name=_as_str(
                    _require(raw, "name", context=context), context=f"{context}.name", maximum=200
                ),
                keywords=keywords,
                required=_as_bool(raw.get("required", True), context=f"{context}.required"),
            )
        )
    ids = [item.item_id for item in items]
    if len(ids) != 24 or len(set(ids)) != 24:
        raise ConfigError("coverage-items.toml must define exactly 24 unique items")
    return tuple(items)


def default_coverage_path(config_path: str | Path) -> Path:
    return Path(config_path).resolve().parent / "coverage-items.toml"


@dataclass(frozen=True, slots=True)
class RelevanceSettings:
    keep_threshold: int
    review_threshold: int
    retention_days: int
    max_scan_bytes: int
    batch_size: int
    title_weight: int


@dataclass(frozen=True, slots=True)
class RelevanceConfig:
    path: Path
    settings: RelevanceSettings
    strong_aliases: tuple[str, ...]
    company_terms: tuple[str, ...]
    context_terms: tuple[str, ...]
    negative_patterns: tuple[str, ...]
    incidental_patterns: tuple[str, ...]
    source_weights: dict[str, int]
    protected_domains: tuple[str, ...]
    config_hash: str


def load_relevance_config(
    path: str | Path = "config/relevance.toml",
    *,
    project_root: Path | None = None,
) -> RelevanceConfig:
    """Load and validate the curation rules used by the relevance filter."""
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = (project_root or PROJECT_ROOT) / config_path
    config_path = config_path.resolve()
    table = _load_toml(config_path)

    settings_table = _require(table, "settings", context="relevance.settings")
    if not isinstance(settings_table, dict):
        raise ConfigError("relevance [settings] table is required")
    keep = _as_int(
        settings_table.get("keep_threshold", 60),
        context="relevance.settings.keep_threshold",
        minimum=1,
        maximum=100,
    )
    review = _as_int(
        settings_table.get("review_threshold", 25),
        context="relevance.settings.review_threshold",
        minimum=0,
        maximum=99,
    )
    if review >= keep:
        raise ConfigError("relevance.settings.review_threshold must be lower than keep_threshold")
    settings = RelevanceSettings(
        keep_threshold=keep,
        review_threshold=review,
        retention_days=_as_int(
            settings_table.get("retention_days", 30),
            context="relevance.settings.retention_days",
            minimum=0,
            maximum=365,
        ),
        max_scan_bytes=_as_int(
            settings_table.get("max_scan_bytes", 8_388_608),
            context="relevance.settings.max_scan_bytes",
            minimum=1_048_576,
            maximum=67_108_864,
        ),
        batch_size=_as_int(
            settings_table.get("batch_size", 500),
            context="relevance.settings.batch_size",
            minimum=1,
            maximum=5000,
        ),
        title_weight=_as_int(
            settings_table.get("title_weight", 10),
            context="relevance.settings.title_weight",
            minimum=0,
            maximum=50,
        ),
    )

    terms_table = _require(table, "terms", context="relevance.terms")
    if not isinstance(terms_table, dict):
        raise ConfigError("relevance [terms] table is required")
    strong_aliases = _as_str_list(
        _require(terms_table, "strong_aliases", context="relevance.terms.strong_aliases"),
        context="relevance.terms.strong_aliases",
    )
    company_terms = _as_str_list(
        _require(terms_table, "company_terms", context="relevance.terms.company_terms"),
        context="relevance.terms.company_terms",
    )
    if not strong_aliases or not company_terms:
        raise ConfigError("relevance terms must include strong_aliases and company_terms")

    raw_weights = table.get("source_weights", {})
    if not isinstance(raw_weights, dict):
        raise ConfigError("relevance [source_weights] must be a table")
    source_weights: dict[str, int] = {}
    for key, value in raw_weights.items():
        source_weights[str(key)] = _as_int(
            value,
            context=f"relevance.source_weights.{key}",
            minimum=-50,
            maximum=50,
        )

    protected = tuple(
        domain.lower().lstrip(".")
        for domain in _as_str_list(
            _require(table, "protected_domains", context="relevance.protected_domains"),
            context="relevance.protected_domains",
        )
    )
    if "manuelita.com" not in protected:
        raise ConfigError("relevance.protected_domains must include 'manuelita.com'")

    return RelevanceConfig(
        path=config_path,
        settings=settings,
        strong_aliases=strong_aliases,
        company_terms=company_terms,
        context_terms=_as_str_list(
            terms_table.get("context_terms", []), context="relevance.terms.context_terms"
        ),
        negative_patterns=_as_str_list(
            terms_table.get("negative_patterns", []),
            context="relevance.terms.negative_patterns",
        ),
        incidental_patterns=_as_str_list(
            terms_table.get("incidental_patterns", []),
            context="relevance.terms.incidental_patterns",
        ),
        source_weights=source_weights,
        protected_domains=protected,
        config_hash=hashlib.sha256(config_path.read_bytes()).hexdigest(),
    )
