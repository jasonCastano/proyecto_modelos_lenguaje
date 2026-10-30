"""Contract tests for the gold schemas."""

from __future__ import annotations

from jsonschema import Draft202012Validator

from tests.contract.gold.conftest import load_schema
from tests.contract.gold.samples import samples


def test_every_gold_schema_is_valid() -> None:
    for name, record in samples().items():
        schema = load_schema(name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(record)
