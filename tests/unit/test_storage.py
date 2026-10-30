"""Unit tests for the raw storage guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.storage import (
    BronzeStorage,
    StorageError,
    StorageLimitExceeded,
    sha256_bytes,
    sha256_text,
)


def test_store_is_atomic_and_verifiable(tmp_path: Path) -> None:
    storage = BronzeStorage(tmp_path / "bronze", limit_bytes=100_000)
    data = b"<html>contenido</html>"
    stored = storage.store(
        data, media_type="text/html", source_id="official_site", campaign_id="c1"
    )
    assert stored.content_hash == sha256_bytes(data)
    assert storage.used_bytes == len(data)
    assert storage.verify(stored.storage_path, stored.content_hash)
    assert not storage.verify(stored.storage_path, "0" * 64)
    assert storage.read(stored.storage_path) == data


def test_storage_refuses_when_limit_would_be_exceeded(tmp_path: Path) -> None:
    storage = BronzeStorage(tmp_path / "bronze", limit_bytes=100_000)
    assert storage.can_store(10_000)
    assert not storage.can_store(90_000)
    with pytest.raises(StorageLimitExceeded):
        storage.store(
            b"x" * 90_000,
            media_type="text/plain",
            source_id="official_site",
            campaign_id="c1",
        )


def test_storage_rejects_path_traversal(tmp_path: Path) -> None:
    storage = BronzeStorage(tmp_path / "bronze", limit_bytes=100_000)
    with pytest.raises(StorageError):
        storage.resolve("../outside.txt")


def test_hashes_are_stable() -> None:
    assert sha256_text("hola") == sha256_text("hola")
    assert sha256_text("hola") != sha256_text("hola ")
    assert len(sha256_bytes(b"x")) == 64
