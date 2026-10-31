"""Contract tests for the brand tokens (T010)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from proyecto_modelos_lenguaje.brand import BrandPalette, BrandTokens

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "009-manuelita-visual-identity"
    / "contracts"
    / "brand-tokens.schema.json"
)


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_schema_file_is_valid_json_schema() -> None:
    Draft202012Validator.check_schema(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_tokens_validate_against_the_contract() -> None:
    _validator().validate(BrandTokens().to_dict())


def test_palette_declares_exactly_the_documented_colours() -> None:
    expected = {
        "forest",
        "orange",
        "lime",
        "yellow",
        "orange_light",
        "white",
        "surface",
        "ink",
        "ink_muted",
        "success",
        "warning",
        "info",
        "danger",
    }
    assert set(BrandPalette().to_dict()) == expected


def test_type_scale_is_descending() -> None:
    scale = BrandTokens().type_scale
    assert scale["display"] > scale["heading"] > scale["body"] > scale["caption"]


@pytest.mark.parametrize("pair", BrandTokens().contrast_pairs)
def test_contrast_pair_is_inside_the_schema_range(pair) -> None:
    assert 1 <= pair.minimum <= 21
    assert pair.text in BrandPalette().to_dict()
    assert pair.background in BrandPalette().to_dict()
