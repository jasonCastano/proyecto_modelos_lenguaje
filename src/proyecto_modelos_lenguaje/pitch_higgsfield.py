"""Cliente de la API de Higgsfield para generar los planos del pitch (specs 028 y 029).

Research R11–R14:

- autenticación ``Authorization: Key <id>:<secreto>``; la clave vive solo en ``.env``
  (``HIGGSFIELD_API_KEY``) y se borra de todo mensaje de error (FR-026, SC-009);
- la imagen se sube con ``POST /files/generate-upload-url`` y un ``PUT`` sin credenciales;
- cada trabajo se envía con ``Idempotency-Key`` y se consulta su ``status_url`` hasta terminar;
- 429 y 503 se reintentan con espera; 401, 403, 404 y 4xx de validación detienen.

El modelo se elige en ``config/pitch.toml`` (spec 029, research R1): MAGI-2 si responde y, si
no, Kling 4.0. Cada modelo declara sus slugs por modo (image, reference, text) y sus campos.

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


MODES = ("image", "reference", "text")


@dataclass(frozen=True)
class ModelSpec:
    """Un modelo de video en Higgsfield: precio, límites, slug y nombres de campo por modo."""

    id: str
    title: str = ""
    usd_per_second: float = 0.08
    resolution: str = "1080p"
    aspect_ratio: str | None = "9:16"
    aspect_modes: tuple[str, ...] = MODES
    audio: bool = True
    min_seconds: int = 4
    max_seconds: int = 30
    reference_tag: str = ""
    slugs: Mapping[str, str] = field(default_factory=dict)
    fields: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def from_toml(cls, model_id: str, data: Mapping[str, Any]) -> ModelSpec:
        data = dict(data)
        return cls(
            id=model_id,
            title=str(data.pop("title", model_id)),
            aspect_modes=tuple(data.pop("aspect_modes", MODES)),
            slugs=dict(data.pop("slugs", {})),
            fields=dict(data.pop("fields", {})),
            **data,
        )

    def slug(self, mode: str) -> str:
        if mode not in self.slugs:
            raise HiggsfieldError(
                f"El modelo {self.id} no tiene modo {mode!r} en config/pitch.toml."
            )
        return self.slugs[mode]

    def cost(self, seconds: float) -> float:
        return round(seconds * self.usd_per_second, 2)

    def body(
        self,
        mode: str,
        *,
        prompt: str,
        seconds: int,
        seed: int | None = None,
        image_url: str | None = None,
    ) -> dict[str, Any]:
        """Cuerpo de la solicitud según el modelo y el modo (research R1 y R2)."""
        f = self.fields
        body: dict[str, Any] = {"prompt": prompt, "resolution": self.resolution}
        if mode == "image":
            body[f.get("image", "image_url")] = image_url
        elif mode == "reference":
            body[f.get("references", "image_urls")] = [image_url]
            if self.reference_tag:
                body["prompt"] = f"{self.reference_tag} is the presenter. {prompt}"
        body[f.get("duration", "duration")] = int(seconds)
        if f.get("audio"):
            body[f["audio"]] = bool(self.audio)
        if f.get("seed") and seed is not None:
            body[f["seed"]] = int(seed)
        if self.aspect_ratio and mode in self.aspect_modes and f.get("aspect_ratio"):
            body[f["aspect_ratio"]] = self.aspect_ratio
        return body


DEFAULT_MODELS: dict[str, ModelSpec] = {
    "magi2": ModelSpec(
        id="magi2",
        title="MAGI-2 (Sand.ai)",
        usd_per_second=0.08,
        slugs={
            "image": "sand/magi-2/image-to-video",
            "reference": "sand/magi-2/reference-to-video",
            "text": "sand/magi-2/text-to-video",
        },
        fields={
            "duration": "duration",
            "audio": "generate_audio",
            "seed": "seed",
            "aspect_ratio": "aspect_ratio",
            "image": "image_url",
            "references": "image_urls",
        },
    ),
    "kling4": ModelSpec(
        id="kling4",
        title="Kling 4.0",
        usd_per_second=0.19,
        aspect_modes=("reference", "text"),
        audio=False,
        min_seconds=3,
        reference_tag="@image_1",
        slugs={
            "image": "kling-video/v4.0/image-to-video",
            "reference": "kling-video/v4.0/reference-to-video",
            "text": "kling-video/v4.0/text-to-video",
        },
        fields={
            "duration": "duration",
            "aspect_ratio": "aspect_ratio",
            "image": "image_url",
            "references": "image_urls",
        },
    ),
}


@dataclass(frozen=True)
class HiggsfieldConfig:
    base_url: str = "https://api.higgsfield.ai"
    api_key_env: str = "HIGGSFIELD_API_KEY"
    poll_s: float = 10
    timeout_s: float = 3600
    preference: tuple[str, ...] = ("magi2", "kling4")
    models: Mapping[str, ModelSpec] = field(default_factory=lambda: dict(DEFAULT_MODELS))
    retime_min: float = 0.7
    retime_max: float = 1.25
    max_usd: float = 20

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> HiggsfieldConfig:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        api = dict(data.get("higgsfield", {}))
        pitch = dict(data.get("pitch", {}))
        preference = tuple(pitch.pop("models", ("magi2", "kling4")))
        models = {
            key: ModelSpec.from_toml(key, value) for key, value in data.get("models", {}).items()
        } or dict(DEFAULT_MODELS)
        unknown = [m for m in preference if m not in models]
        if unknown:
            raise HiggsfieldError(
                f"[pitch].models nombra modelos sin sección: {', '.join(unknown)}."
            )
        return cls(
            **api,
            preference=preference,
            models=models,
            **pitch,
            max_usd=float(data.get("budget", {}).get("max_usd", 20)),
        )

    def spec(self, model_id: str) -> ModelSpec:
        try:
            return self.models[model_id]
        except KeyError:
            raise HiggsfieldError(
                f"Modelo desconocido {model_id!r}; los de config/pitch.toml son: "
                + ", ".join(self.models)
                + "."
            ) from None


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

    def probe(self, slug: str) -> tuple[int, str]:
        """Envía ``{"prompt": 1}``, que siempre es inválido: no crea trabajos ni cobra (R1).

        Devuelve el código y el detalle sin lanzar errores. 400/422 = el modelo responde;
        403 ``model_unavailable``, 404 o 423 = no disponible para la cuenta.
        """
        try:
            response = self._api.request("POST", "/" + slug.strip("/"), json={"prompt": 1})
        except httpx.HTTPError as exc:
            return 0, self._credentials.redact(str(exc))[:200]
        return response.status_code, self._detail(response)

    def submit(self, body: Mapping[str, Any], idempotency_key: str, slug: str) -> dict[str, str]:
        data = self._request(
            "POST",
            "/" + slug.strip("/"),
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
