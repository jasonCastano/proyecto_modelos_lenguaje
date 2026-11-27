"""Cliente de la API de Higgsfield para generar las escenas del pitch con MAGI-2 (spec 028).

Research R11–R14:

- autenticación ``Authorization: Key <id>:<secreto>``; la clave vive solo en ``.env``
  (``HIGGSFIELD_API_KEY``) y se borra de todo mensaje de error (FR-026, SC-009);
- la imagen se sube con ``POST /files/generate-upload-url`` y un ``PUT`` sin credenciales;
- cada trabajo se envía con ``Idempotency-Key`` y se consulta su ``status_url`` hasta terminar;
- 429 y 503 se reintentan con espera; 401, 403, 404 y 4xx de validación detienen.

Solo lo usa ``pml pitch generate``: ni la aplicación web ni la CI llaman a Higgsfield (FR-028).
"""

from __future__ import annotations

import logging
import os
import time
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config" / "pitch.toml"
TERMINAL = ("completed", "failed", "nsfw", "canceled")
RETRYABLE = (429, 503)
MAX_RETRIES = 6

log = logging.getLogger(__name__)


class HiggsfieldError(RuntimeError):
    """Error de la API de Higgsfield, con la clave ya borrada del mensaje."""


class CredentialsError(HiggsfieldError):
    """Falta la clave, no tiene la forma id:secreto o la API la rechaza (401)."""


class BalanceError(HiggsfieldError):
    """Saldo insuficiente en la cuenta (403)."""


class ModelUnavailable(HiggsfieldError):
    """El modelo no está disponible para la cuenta (404, 423 o 503 tras reintentos)."""


class ValidationFailed(HiggsfieldError):
    """La API rechazó el cuerpo de la solicitud (400 o 422)."""


class JobFailed(HiggsfieldError):
    """El trabajo terminó sin video: failed, nsfw, canceled o tiempo agotado."""

    def __init__(self, message: str, status: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.request_id = request_id


@dataclass(frozen=True)
class HiggsfieldConfig:
    base_url: str = "https://api.higgsfield.ai"
    model: str = "sand/magi-2/image-to-video"
    api_key_env: str = "HIGGSFIELD_API_KEY"
    resolution: str = "1080p"
    aspect_ratio: str | None = "9:16"
    seconds: int = 10
    audio: bool = True
    poll_s: float = 10
    timeout_s: float = 900
    fields: Mapping[str, str] = field(
        default_factory=lambda: {
            "duration": "duration",
            "audio": "generate_audio",
            "aspect_ratio": "aspect_ratio",
        }
    )
    usd_per_second: float = 0.08
    max_usd: float = 20

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> HiggsfieldConfig:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        api = dict(data.get("higgsfield", {}))
        fields = {**cls().fields, **api.pop("fields", {})}
        budget = data.get("budget", {})
        return cls(**api, fields=fields, **budget)

    def cost(self, seconds: float) -> float:
        return round(seconds * self.usd_per_second, 2)

    def body(self, *, image_url: str, prompt: str, seed: int, seconds: int) -> dict[str, Any]:
        body: dict[str, Any] = {
            "image_url": image_url,
            "prompt": prompt,
            "resolution": self.resolution,
            "seed": int(seed),
            self.fields["duration"]: int(seconds),
            self.fields["audio"]: bool(self.audio),
        }
        if self.aspect_ratio:
            body[self.fields.get("aspect_ratio", "aspect_ratio")] = self.aspect_ratio
        return body


@dataclass(frozen=True)
class Credentials:
    key_id: str
    secret: str = field(repr=False)

    @property
    def header(self) -> str:
        return f"Key {self.key_id}:{self.secret}"

    def redact(self, text: str) -> str:
        for value in (f"{self.key_id}:{self.secret}", self.secret, self.key_id):
            if value:
                text = text.replace(value, "***")
        return text

    def __repr__(self) -> str:
        return "Credentials(***)"


def load_credentials(
    env_name: str = "HIGGSFIELD_API_KEY", env: Mapping[str, str] | None = None
) -> Credentials:
    """Lee la clave de ``env`` o, si no se pasa, de ``.env`` y del entorno del proceso."""
    if env is None:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env", override=False)
        env = os.environ
    raw = (env.get(env_name) or "").strip().strip('"').strip("'")
    if not raw:
        raise CredentialsError(
            f"Falta {env_name} en .env. Créala en la consola de Higgsfield y agrégala como "
            f"{env_name}=<id>:<secreto>."
        )
    key_id, sep, secret = raw.partition(":")
    if not sep or not key_id or not secret:
        raise CredentialsError(
            f"{env_name} debe tener la forma <id>:<secreto> (consola de Higgsfield)."
        )
    return Credentials(key_id=key_id, secret=secret)


class HiggsfieldClient:
    """Cliente mínimo sobre ``httpx`` para catálogo, subida, envío, estado y descarga."""

    def __init__(
        self,
        config: HiggsfieldConfig,
        credentials: Credentials,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self._credentials = credentials
        self._sleep = sleep
        self._clock = clock
        self._api = httpx.Client(
            base_url=config.base_url,
            headers={"Authorization": credentials.header, "Accept": "application/json"},
            timeout=httpx.Timeout(60.0),
            transport=transport,
        )
        # Sin credenciales: la subida firmada y la descarga del video van a otro dominio.
        self._plain = httpx.Client(
            timeout=httpx.Timeout(300.0), transport=transport, follow_redirects=True
        )

    @classmethod
    def from_env(
        cls, config: HiggsfieldConfig, env: Mapping[str, str] | None = None
    ) -> HiggsfieldClient:
        return cls(config, load_credentials(config.api_key_env, env))

    def close(self) -> None:
        self._api.close()
        self._plain.close()

    def __enter__(self) -> HiggsfieldClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ solicitudes

    def _detail(self, response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return self._credentials.redact(str(detail))[:400]

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._api.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                if attempt == MAX_RETRIES:
                    raise HiggsfieldError(
                        "No se pudo conectar con Higgsfield: " + self._credentials.redact(str(exc))
                    ) from None
                self._sleep(min(2**attempt, 30))
                continue
            if response.status_code in RETRYABLE and attempt < MAX_RETRIES:
                wait = response.headers.get("Retry-After")
                self._sleep(float(wait) if wait else min(2**attempt, 30))
                continue
            self._raise_for(response)
            return response
        raise HiggsfieldError("Higgsfield no respondió tras varios intentos.")

    def _raise_for(self, response: httpx.Response) -> None:
        code = response.status_code
        if code < 400:
            return
        detail = self._detail(response)
        if code == 401:
            raise CredentialsError(
                "Higgsfield rechazó la clave (401). Revisa HIGGSFIELD_API_KEY en .env."
            )
        if code == 403:
            raise BalanceError(
                f"Saldo insuficiente en Higgsfield (403): {detail}. Recarga y repite."
            )
        if code in (404, 423, 503):
            raise ModelUnavailable(f"Modelo no disponible para la cuenta ({code}): {detail}")
        if code in (400, 422):
            raise ValidationFailed(f"Higgsfield rechazó la solicitud ({code}): {detail}")
        raise HiggsfieldError(f"Higgsfield respondió {code}: {detail}")

    # ------------------------------------------------------------------ operaciones

    def list_models(self) -> list[str]:
        data = self._request("GET", "/models", params={"limit": 200}).json()
        return [str(item.get("slug")) for item in data.get("items", [])]

    def upload_image(self, path: Path, content_type: str = "image/png") -> str:
        data = self._request(
            "POST", "/files/generate-upload-url", json={"content_type": content_type}
        ).json()
        headers = dict(data.get("upload_headers") or {"Content-Type": content_type})
        put = self._plain.put(data["upload_url"], content=path.read_bytes(), headers=headers)
        if put.status_code >= 400:
            raise HiggsfieldError(f"La subida de la imagen falló ({put.status_code}).")
        return str(data["public_url"])

    def submit(self, body: Mapping[str, Any], idempotency_key: str) -> dict[str, str]:
        data = self._request(
            "POST",
            "/" + self.config.model.strip("/"),
            json=dict(body),
            headers={"Idempotency-Key": idempotency_key},
        ).json()
        request_id = str(data["request_id"])
        status_url = data.get("status_url") or f"/requests/{request_id}/status"
        log.info("Higgsfield: trabajo %s en cola", request_id)
        return {"request_id": request_id, "status_url": str(status_url)}

    def wait(self, request_id: str, status_url: str) -> dict[str, Any]:
        deadline = self._clock() + self.config.timeout_s
        while True:
            data = self._request("GET", status_url).json()
            status = str(data.get("status"))
            if status in TERMINAL:
                if status != "completed":
                    error = self._credentials.redact(str(data.get("error") or status))
                    raise JobFailed(
                        f"El trabajo {request_id} terminó en {status}: {error}", status, request_id
                    )
                return data
            if self._clock() >= deadline:
                raise JobFailed(
                    f"El trabajo {request_id} superó {self.config.timeout_s:.0f} s de espera.",
                    "timeout",
                    request_id,
                )
            self._sleep(self.config.poll_s)

    def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._plain.stream("GET", url) as response:
            if response.status_code >= 400:
                raise HiggsfieldError(f"La descarga del video falló ({response.status_code}).")
            with dest.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        return dest


def video_url(result: Mapping[str, Any]) -> str:
    """URL del video en la respuesta ``completed`` (``video.url`` o ``payload.video.url``)."""
    for holder in (result, result.get("payload") or {}):
        video = holder.get("video") if isinstance(holder, Mapping) else None
        if isinstance(video, Mapping) and video.get("url"):
            return str(video["url"])
        videos = holder.get("videos") if isinstance(holder, Mapping) else None
        if isinstance(videos, list) and videos and videos[0].get("url"):
            return str(videos[0]["url"])
    raise HiggsfieldError("La respuesta de Higgsfield no trae la URL del video.")
