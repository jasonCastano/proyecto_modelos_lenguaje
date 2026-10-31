"""Configuración y cliente del proveedor LLM del Módulo 1 (DeepSeek por API).

La clave se lee exclusivamente de la variable de entorno indicada por ``api_key_env``; nunca se
escribe en archivos versionados, registros ni resultados. El módulo expone un ``BaseChatModel``
para que ``tasks.py`` y la app no conozcan al proveedor.

Ver `specs/011-deepseek-api-model/` (spec, plan, contrato y modelo de datos).
"""

from __future__ import annotations

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
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
VALID_PROVIDERS = {"deepseek"}
VALID_CONTEXT_PACKS = {"8000", "32000"}
VALID_LANGUAGES = {"es", "en"}
FORBIDDEN_KEYS = ("api_key", "apikey", "token", "secret", "password")
# `api_key_env` solo nombra la variable de entorno; no contiene el secreto.
ALLOWED_CONFIG_NAMES = {"api_key_env"}


class LLMError(RuntimeError):
    """Base class for provider errors with an actionable code."""

    code = "provider_unavailable"
    retryable = False


class LLMConfigError(LLMError, ValueError):
    """Raised when the provider configuration is missing or invalid."""

    code = "config_missing_key"


class LLMAuthError(LLMError):
    """Raised when the API rejects the key."""

    code = "auth_failed"


class LLMRateLimitError(LLMError):
    """Raised when the account has exhausted its quota."""

    code = "rate_limited"
    retryable = True


class LLMTimeoutError(LLMError):
    """Raised when the provider does not answer within the timeout."""

    code = "timeout"
    retryable = True


class LLMUnavailableError(LLMError):
    """Raised when the provider cannot be reached or fails with 5xx."""

    code = "provider_unavailable"
    retryable = True


class LLMModelMissingError(LLMError):
    """Raised when the configured model does not exist in the account."""

    code = "model_unavailable"


class LLMResponseError(LLMError):
    """Raised when the provider returns an unusable response."""

    code = "invalid_response"
    retryable = True


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Validated view of ``config/llm.toml``. Never stores the API key value."""

    provider: str
    model: str
    base_url: str
    api_key_env: str
    temperature: float
    top_p: float
    max_output_tokens: int
    context_window: int
    default_context_pack: str
    timeout_seconds: int
    max_retries: int
    retry_backoff_seconds: float
    cost_per_1k_input: float
    cost_per_1k_output: float
    language: str

    @property
    def api_key_present(self) -> bool:
        value = os.getenv(self.api_key_env, "")
        return bool(value.strip())

    @property
    def cost_configured(self) -> bool:
        return self.cost_per_1k_input > 0 or self.cost_per_1k_output > 0

    def api_key(self) -> str:
        """Return the key or raise an actionable configuration error."""
        value = os.getenv(self.api_key_env, "")
        if not value.strip():
            raise LLMConfigError(
                f"Falta la clave del proveedor. Define {self.api_key_env} en `.env` "
                "y recarga la aplicación."
            )
        return value.strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "api_key_present": self.api_key_present,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_output_tokens": self.max_output_tokens,
            "context_window": self.context_window,
            "default_context_pack": self.default_context_pack,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "language": self.language,
        }

    def format_cost(self, amount_usd: float) -> str:
        if not self.cost_configured:
            return "costo no configurado"
        return f"{amount_usd:.4f} USD"


LLMConfig = ProviderConfig


def _require_table(table: dict[str, Any], key: str) -> dict[str, Any]:
    value = table.get(key)
    if not isinstance(value, dict):
        raise LLMConfigError(f"Falta la tabla [{key}] en la configuración del modelo.")
    return value


def _reject_secret_fields(table: dict[str, Any]) -> None:
    for key in table:
        normalized = str(key).lower().replace("-", "_")
        if normalized in ALLOWED_CONFIG_NAMES:
            continue
        if any(
            normalized == forbidden or normalized.endswith(f"_{forbidden}")
            for forbidden in FORBIDDEN_KEYS
        ):
            raise LLMConfigError(
                f"El campo `{key}` no está permitido en la configuración: las claves solo se "
                "leen de variables de entorno."
            )


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


def _as_env_name(value: Any, *, field: str) -> str:
    text = _as_str(value, field=field, default=DEFAULT_API_KEY_ENV)
    if not text.isupper() or not text.replace("_", "").isalnum() or not text[0].isalpha():
        raise LLMConfigError(f"{field} debe ser un nombre de variable en mayúsculas (A-Z, 0-9, _).")
    return text


def load_llm_config(
    path: str | Path = DEFAULT_CONFIG,
    *,
    project_root: Path | None = None,
) -> ProviderConfig:
    """Load and validate ``config/llm.toml``."""
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
    _reject_secret_fields(table)
    load_dotenv(root / ".env", override=False)

    provider = _as_str(table.get("provider"), field="llm.provider", default="deepseek").lower()
    if provider not in VALID_PROVIDERS:
        raise LLMConfigError(
            f"llm.provider no soportado: {provider}. Valores válidos: {sorted(VALID_PROVIDERS)}."
        )
    model = _as_str(
        os.getenv("DEEPSEEK_MODEL", table.get("model")),
        field="llm.model",
        default=DEFAULT_MODEL,
    )
    if any(character.isspace() for character in model):
        raise LLMConfigError("llm.model no debe contener espacios.")
    base_url = _as_str(
        os.getenv("DEEPSEEK_BASE_URL", table.get("base_url")),
        field="llm.base_url",
        default=DEFAULT_BASE_URL,
    )
    if not base_url.startswith(("https://", "http://")):
        raise LLMConfigError("llm.base_url debe comenzar con https:// o http://.")
    api_key_env = _as_env_name(table.get("api_key_env"), field="llm.api_key_env")

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
        table.get("context_window", 32768),
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
        table.get("timeout_seconds", 60),
        field="llm.timeout_seconds",
        minimum=5,
        maximum=300,
    )
    max_retries = _as_int(
        table.get("max_retries", 1), field="llm.max_retries", minimum=0, maximum=3
    )
    retry_backoff_seconds = _as_float(
        table.get("retry_backoff_seconds", 2.0),
        field="llm.retry_backoff_seconds",
        minimum=0.0,
        maximum=30.0,
    )
    cost_per_1k_input = _as_float(
        table.get("cost_per_1k_input", 0.0),
        field="llm.cost_per_1k_input",
        minimum=0.0,
        maximum=1000.0,
    )
    cost_per_1k_output = _as_float(
        table.get("cost_per_1k_output", 0.0),
        field="llm.cost_per_1k_output",
        minimum=0.0,
        maximum=1000.0,
    )
    language = _as_str(table.get("language"), field="llm.language", default="es").lower()
    if language not in VALID_LANGUAGES:
        raise LLMConfigError("llm.language debe ser 'es' o 'en'.")

    return ProviderConfig(
        provider=provider,
        model=model,
        base_url=base_url.rstrip("/"),
        api_key_env=api_key_env,
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        context_window=context_window,
        default_context_pack=default_context_pack,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        cost_per_1k_input=cost_per_1k_input,
        cost_per_1k_output=cost_per_1k_output,
        language=language,
    )


def build_chat_model(config: ProviderConfig, *, api_key: str | None = None) -> BaseChatModel:
    """Build the DeepSeek chat model (OpenAI-compatible). Construction is offline."""
    if config.provider != "deepseek":
        raise LLMConfigError(f"Proveedor no soportado: {config.provider}.")
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise LLMConfigError("langchain-openai no está instalado; ejecuta `uv sync`.") from exc
    return ChatOpenAI(
        model=config.model,
        base_url=config.base_url,
        api_key=api_key or config.api_key(),
        temperature=config.temperature,
        top_p=config.top_p,
        max_tokens=config.max_output_tokens,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
    )


def build_fake_model(responses: list[str] | None = None) -> BaseChatModel:
    """Deterministic offline model for unit and contract tests."""
    canned = list(responses or ["Respuesta de prueba con cita: [U1]."])
    return FakeListChatModel(responses=canned)


def classify_error(exc: Exception) -> LLMError:
    """Translate a provider or network failure into a project error."""
    try:
        import openai
    except ImportError:  # pragma: no cover - dependency is declared
        return LLMUnavailableError(f"El proveedor falló: {exc}")

    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return LLMAuthError(
            "La clave del proveedor no es válida o fue revocada. Genera una nueva y actualiza "
            "DEEPSEEK_API_KEY."
        )
    if isinstance(exc, openai.NotFoundError):
        return LLMModelMissingError(
            "El modelo configurado no está disponible en la cuenta. Revisa llm.model."
        )
    if isinstance(exc, openai.RateLimitError):
        return LLMRateLimitError(
            "Se agotó la cuota del proveedor. Espera unos minutos o activa el modo demostración."
        )
    if isinstance(exc, (openai.APITimeoutError, TimeoutError)):
        return LLMTimeoutError(
            "El proveedor no respondió dentro del tiempo límite. Reintenta o usa el modo demo."
        )
    if isinstance(exc, openai.APIConnectionError):
        return LLMUnavailableError(
            "No se pudo conectar con el proveedor. Verifica la red o usa el modo demostración."
        )
    if isinstance(exc, openai.BadRequestError):
        return LLMResponseError(
            "El proveedor rechazó la petición. Revisa la configuración del modelo y reintenta."
        )
    if isinstance(exc, openai.APIStatusError):
        if exc.status_code >= 500:
            return LLMUnavailableError(
                "El proveedor no está disponible en este momento. Reintenta en unos minutos."
            )
        return LLMResponseError("El proveedor devolvió un error inesperado. Reintenta.")
    return LLMUnavailableError(f"El proveedor falló de forma inesperada: {type(exc).__name__}.")


def invoke_with_retries(
    model: Any,
    messages: Any,
    config: ProviderConfig,
) -> Any:
    """Invoke the model, retrying only transient provider failures."""
    attempt = 0
    while True:
        try:
            return model.invoke(messages)
        except Exception as exc:
            error = exc if isinstance(exc, LLMError) else classify_error(exc)
            if not error.retryable or attempt >= config.max_retries:
                raise error from exc
            attempt += 1
            if config.retry_backoff_seconds:
                time.sleep(config.retry_backoff_seconds * attempt)


def usage_tokens(message: Any) -> tuple[int, int] | None:
    """Return ``(input_tokens, output_tokens)`` reported by the provider, if any."""
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            return input_tokens, output_tokens
    metadata = getattr(message, "response_metadata", None) or {}
    token_usage = metadata.get("token_usage") if isinstance(metadata, dict) else None
    if isinstance(token_usage, dict):
        prompt = token_usage.get("prompt_tokens")
        completion = token_usage.get("completion_tokens")
        if isinstance(prompt, int) and isinstance(completion, int):
            return prompt, completion
    return None


def estimate_cost(input_tokens: int, output_tokens: int, config: ProviderConfig) -> float:
    """Estimated USD cost for one call, using the configured rates."""
    cost = (
        input_tokens / 1000 * config.cost_per_1k_input
        + output_tokens / 1000 * config.cost_per_1k_output
    )
    return round(cost, 6)


def actionable_message(exc: Exception) -> str:
    """Human, actionable message for a provider error (never includes the key)."""
    if isinstance(exc, LLMConfigError):
        return str(exc)
    if isinstance(exc, LLMAuthError):
        return str(exc)
    if isinstance(exc, LLMModelMissingError):
        return str(exc)
    if isinstance(exc, LLMRateLimitError):
        return str(exc)
    if isinstance(exc, LLMTimeoutError):
        return str(exc)
    if isinstance(exc, LLMUnavailableError):
        return str(exc)
    if isinstance(exc, LLMResponseError):
        return str(exc)
    return "Ocurrió un error controlado con el proveedor. Reintenta o usa el modo demostración."


def _fetch_models(config: ProviderConfig) -> list[str]:
    url = f"{config.base_url}/models"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.api_key()}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=min(config.timeout_seconds, 15)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise LLMAuthError(
                "La clave del proveedor no es válida o fue revocada. Genera una nueva y actualiza "
                "DEEPSEEK_API_KEY."
            ) from exc
        if exc.code == 429:
            raise LLMRateLimitError(
                "Se agotó la cuota del proveedor. Espera unos minutos o activa el "
                "modo demostración."
            ) from exc
        if exc.code >= 500:
            raise LLMUnavailableError(
                "El proveedor no está disponible en este momento. Reintenta en unos minutos."
            ) from exc
        raise LLMResponseError(
            "El proveedor rechazó la verificación. Revisa llm.base_url."
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LLMUnavailableError(
            "No se pudo conectar con el proveedor. Verifica la red o usa el modo demostración."
        ) from exc
    except json.JSONDecodeError as exc:
        raise LLMResponseError(
            "El proveedor devolvió una respuesta que no es JSON válido."
        ) from exc
    data = payload.get("data", []) if isinstance(payload, dict) else []
    names: list[str] = []
    for item in data:
        if isinstance(item, dict):
            name = item.get("id") or item.get("name")
            if name:
                names.append(str(name))
    return names


def health_check(config: ProviderConfig) -> dict[str, Any]:
    started = time.perf_counter()
    names = _fetch_models(config)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    if names and config.model not in names:
        raise LLMModelMissingError(
            f"El modelo {config.model} no está disponible en la cuenta. "
            "Ajusta llm.model en config/llm.toml."
        )
    return {
        "ok": True,
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "api_key_present": True,
        "latency_ms": latency_ms,
        "detail": "modelo disponible",
    }


def build_parser() -> Any:
    import argparse

    parser = argparse.ArgumentParser(
        prog="proyecto_modelos_lenguaje.llm",
        description="Configuración y verificación del proveedor LLM del Módulo 1.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Ruta de config/llm.toml.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica que el proveedor responda y que el modelo esté disponible.",
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
    except LLMError as exc:
        payload = {
            "ok": False,
            "error": type(exc).__name__,
            "code": exc.code,
            "detail": actionable_message(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
