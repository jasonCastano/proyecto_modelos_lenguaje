"""LLM configuration and Ollama adapter for the Module 1 tasks."""

from __future__ import annotations

import argparse
import json
import os
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from .config import PROJECT_ROOT

DEFAULT_CONFIG = "config/llm.toml"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_BASE_URL = "http://localhost:11434"
VALID_PROVIDERS = {"ollama"}
VALID_CONTEXT_PACKS = {"8000", "32000"}


class LLMConfigError(ValueError):
    """Raised when the LLM configuration is missing or invalid."""


class LLMUnavailableError(RuntimeError):
    """Raised when the local Ollama server cannot be reached."""


class LLMModelMissingError(RuntimeError):
    """Raised when Ollama is reachable but the model is not installed."""


class LLMResponseError(RuntimeError):
    """Raised when the model fails or returns an unusable response."""


@dataclass(frozen=True, slots=True)
class LLMConfig:
    provider: str
    model: str
    base_url: str
    temperature: float
    top_p: float
    max_output_tokens: int
    context_window: int
    default_context_pack: str
    timeout_seconds: int
    max_retries: int
    retry_backoff_seconds: float
    keep_alive: str
    seed: int | None
    language: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_output_tokens": self.max_output_tokens,
            "context_window": self.context_window,
            "default_context_pack": self.default_context_pack,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "keep_alive": self.keep_alive,
            "seed": self.seed,
            "language": self.language,
        }


def _require_table(table: dict[str, Any], key: str) -> dict[str, Any]:
    value = table.get(key)
    if not isinstance(value, dict):
        raise LLMConfigError(f"Falta la tabla [{key}] en la configuración del modelo.")
    return value


def _as_str(value: Any, *, field: str, default: str | None = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or not value.strip():
        raise LLMConfigError(f"{field} debe ser un texto no vacío.")
    return value.strip()


def _as_float(value: Any, *, field: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMConfigError(f"{field} debe ser un número.")
    number = float(value)
    if not minimum <= number <= maximum:
        raise LLMConfigError(f"{field} debe estar entre {minimum} y {maximum}.")
    return number


def _as_int(value: Any, *, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LLMConfigError(f"{field} debe ser un entero.")
    if not minimum <= value <= maximum:
        raise LLMConfigError(f"{field} debe estar entre {minimum} y {maximum}.")
    return value


def load_llm_config(
    path: str | Path = DEFAULT_CONFIG,
    *,
    project_root: Path | None = None,
) -> LLMConfig:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.is_file():
        raise LLMConfigError(f"No existe la configuración del modelo: {path}.")
    try:
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise LLMConfigError(f"TOML inválido en {path}: {exc}") from exc

    table = _require_table(document, "llm")
    load_dotenv(root / ".env", override=False)

    provider = _as_str(table.get("provider"), field="llm.provider", default="ollama").lower()
    if provider not in VALID_PROVIDERS:
        raise LLMConfigError(
            f"llm.provider no soportado: {provider}. Valores válidos: {sorted(VALID_PROVIDERS)}."
        )
    model = _as_str(
        os.getenv("OLLAMA_MODEL", table.get("model")),
        field="llm.model",
        default=DEFAULT_MODEL,
    )
    if any(character.isspace() for character in model):
        raise LLMConfigError("llm.model no debe contener espacios.")
    base_url = _as_str(
        os.getenv("OLLAMA_BASE_URL", table.get("base_url")),
        field="llm.base_url",
        default=DEFAULT_BASE_URL,
    )
    if not base_url.startswith(("http://", "https://")):
        raise LLMConfigError("llm.base_url debe comenzar con http:// o https://.")

    temperature = _as_float(
        table.get("temperature", 0.1), field="llm.temperature", minimum=0.0, maximum=1.0
    )
    top_p = _as_float(table.get("top_p", 0.9), field="llm.top_p", minimum=0.01, maximum=1.0)
    max_output_tokens = _as_int(
        table.get("max_output_tokens", 1024),
        field="llm.max_output_tokens",
        minimum=128,
        maximum=8192,
    )
    context_window = _as_int(
        table.get("context_window", 16384),
        field="llm.context_window",
        minimum=2048,
        maximum=131072,
    )
    default_context_pack = _as_str(
        table.get("default_context_pack"), field="llm.default_context_pack", default="8000"
    )
    if default_context_pack not in VALID_CONTEXT_PACKS:
        raise LLMConfigError("llm.default_context_pack debe ser '8000' o '32000'.")
    if int(default_context_pack) > context_window:
        raise LLMConfigError("llm.default_context_pack no puede superar llm.context_window.")
    timeout_seconds = _as_int(
        table.get("timeout_seconds", 120),
        field="llm.timeout_seconds",
        minimum=1,
        maximum=600,
    )
    max_retries = _as_int(
        table.get("max_retries", 1), field="llm.max_retries", minimum=0, maximum=5
    )
    retry_backoff_seconds = _as_float(
        table.get("retry_backoff_seconds", 2.0),
        field="llm.retry_backoff_seconds",
        minimum=0.0,
        maximum=60.0,
    )
    keep_alive = _as_str(table.get("keep_alive"), field="llm.keep_alive", default="5m")
    language = _as_str(table.get("language"), field="llm.language", default="es")
    raw_seed = table.get("seed")
    seed: int | None = None
    if raw_seed is not None:
        if isinstance(raw_seed, bool) or not isinstance(raw_seed, int) or raw_seed < 0:
            raise LLMConfigError("llm.seed debe ser un entero no negativo o nulo.")
        seed = raw_seed

    return LLMConfig(
        provider=provider,
        model=model,
        base_url=base_url.rstrip("/"),
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        context_window=context_window,
        default_context_pack=default_context_pack,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        keep_alive=keep_alive,
        seed=seed,
        language=language,
    )


def build_chat_model(config: LLMConfig) -> BaseChatModel:
    """Build the LangChain chat model. Construction is offline."""
    if config.provider != "ollama":
        raise LLMConfigError(f"Proveedor no soportado: {config.provider}.")
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise LLMConfigError("langchain-ollama no está instalado; ejecuta `uv sync`.") from exc
    return ChatOllama(
        model=config.model,
        base_url=config.base_url,
        temperature=config.temperature,
        top_p=config.top_p,
        num_predict=config.max_output_tokens,
        num_ctx=config.context_window,
        keep_alive=config.keep_alive,
        seed=config.seed,
        validate_model_on_init=False,
        client_kwargs={"timeout": config.timeout_seconds},
    )


def build_fake_model(responses: list[str] | None = None) -> BaseChatModel:
    """Deterministic offline model for unit and contract tests."""
    canned = list(responses or ["Respuesta de prueba con cita: [1]."])
    return FakeListChatModel(responses=canned)


def invoke_with_retries(
    model: BaseChatModel,
    messages: Any,
    config: LLMConfig,
) -> Any:
    """Invoke a chat model with the configured retry budget."""
    last: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            return model.invoke(messages)
        except Exception as exc:
            last = exc
            if attempt >= config.max_retries:
                break
            if config.retry_backoff_seconds:
                time.sleep(config.retry_backoff_seconds)
    raise LLMResponseError(
        f"El modelo falló tras {config.max_retries + 1} intento(s): {last}"
    ) from last


def _fetch_tags(config: LLMConfig) -> list[str]:
    url = f"{config.base_url}/api/tags"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=min(config.timeout_seconds, 10)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise LLMUnavailableError(
            f"Ollama no responde en {config.base_url}. "
            "Ejecuta `ollama serve` y verifica OLLAMA_BASE_URL."
        ) from exc
    except (TimeoutError, OSError) as exc:
        raise LLMUnavailableError(
            f"Ollama no responde en {config.base_url}. "
            "Ejecuta `ollama serve` y verifica OLLAMA_BASE_URL."
        ) from exc
    except json.JSONDecodeError as exc:
        raise LLMResponseError("Ollama devolvió una respuesta que no es JSON válido.") from exc
    models = payload.get("models", []) if isinstance(payload, dict) else []
    names: list[str] = []
    for item in models:
        if isinstance(item, dict):
            name = item.get("name") or item.get("model")
            if name:
                names.append(str(name))
    return names


def health_check(config: LLMConfig) -> dict[str, Any]:
    started = time.perf_counter()
    names = _fetch_tags(config)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    candidates = {config.model, f"{config.model}:latest"}
    if not candidates.intersection(names):
        raise LLMModelMissingError(
            f"El modelo {config.model} no está descargado. Ejecuta `ollama pull {config.model}`."
        )
    return {
        "ok": True,
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "latency_ms": latency_ms,
        "detail": "modelo disponible",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proyecto_modelos_lenguaje.llm",
        description="Configuración y verificación del modelo Ollama del Módulo 1.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Ruta de config/llm.toml.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica que Ollama responda y que el modelo esté descargado.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Imprime la configuración efectiva sin secretos.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    project_root: Path | None = None,
) -> int:
    parser = build_parser()
    arguments = list(argv) if argv is not None else None
    args = parser.parse_args(arguments)
    if not args.check and not args.print_config:
        parser.print_help()
        return 0
    try:
        config = load_llm_config(args.config, project_root=project_root)
        if args.print_config:
            print(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
            return 0
        result = health_check(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        LLMConfigError,
        LLMUnavailableError,
        LLMModelMissingError,
        LLMResponseError,
    ) as exc:
        payload = {"ok": False, "error": type(exc).__name__, "detail": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
