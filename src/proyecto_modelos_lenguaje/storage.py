"""Immutable raw storage with hashing and the 10 GB guard."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .extractors.metadata import extension_for

_HASH_RE = re.compile(r"^[a-f0-9]{64}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")


class StorageError(RuntimeError):
    """Raised for unsafe paths or corrupt artifacts."""


class StorageLimitExceeded(StorageError):
    """Raised when storing a new artifact would exceed the configured ceiling."""


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    content_hash: str
    byte_size: int
    storage_path: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class BronzeStorage:
    """Writes raw artifacts atomically under ``<bronze>/raw`` and enforces the cap."""

    def __init__(self, bronze_dir: str | Path, *, limit_bytes: int) -> None:
        self.root = Path(bronze_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.limit_bytes = limit_bytes
        self._reserve = min(64 * 1024 * 1024, max(64 * 1024, limit_bytes // 100))
        self._used = self._scan()

    @property
    def used_bytes(self) -> int:
        return self._used

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    def _scan(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            if path.is_file() and not path.name.startswith(".tmp-"):
                total += path.stat().st_size
        return total

    def can_store(self, size: int) -> bool:
        if size <= 0:
            return False
        return self._used + self._reserve + size <= self.limit_bytes

    def store(
        self,
        data: bytes,
        *,
        media_type: str,
        source_id: str,
        campaign_id: str,
    ) -> StoredArtifact:
        if not _SLUG_RE.match(source_id):
            raise StorageError(f"invalid source id for storage: {source_id!r}")
        if not _SLUG_RE.match(campaign_id):
            raise StorageError(f"invalid campaign id for storage: {campaign_id!r}")
        size = len(data)
        if size == 0:
            raise StorageError("refusing to store an empty artifact")
        if not self.can_store(size):
            raise StorageLimitExceeded(
                f"storing {size} bytes would exceed the limit "
                f"({self._used} used of {self.limit_bytes})"
            )
        content_hash = sha256_bytes(data)
        extension = extension_for(media_type)
        directory = self.raw_dir / source_id / campaign_id
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{content_hash}{extension}"
        if destination.exists():
            return StoredArtifact(content_hash, size, destination.relative_to(self.root).as_posix())
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=directory, prefix=".tmp-", suffix=".part", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except BaseException:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
        self._used += size
        return StoredArtifact(content_hash, size, destination.relative_to(self.root).as_posix())

    def resolve(self, storage_path: str) -> Path:
        candidate = (self.root / storage_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise StorageError(
                f"storage path escapes the bronze directory: {storage_path}"
            ) from exc
        if not candidate.is_file():
            raise StorageError(f"artifact file not found: {storage_path}")
        return candidate

    def read(self, storage_path: str) -> bytes:
        return self.resolve(storage_path).read_bytes()

    def verify(self, storage_path: str, expected_hash: str) -> bool:
        if not _HASH_RE.match(expected_hash):
            return False
        return sha256_bytes(self.read(storage_path)) == expected_hash

    def refresh_usage(self) -> int:
        self._used = self._scan()
        return self._used
