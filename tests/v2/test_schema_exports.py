"""Committed V2 schemas must match the live typed contracts exactly."""

from __future__ import annotations

import json
from pathlib import Path

from researchforge.v2.schema_exports import V2_SCHEMA_MODELS, export_schema

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_committed_v2_schemas_match_live_contracts() -> None:
    schema_root = PROJECT_ROOT / "schemas" / "v2"
    expected = set(V2_SCHEMA_MODELS)
    actual = {path.name for path in schema_root.glob("*.schema.json")}
    assert actual == expected
    for filename, model in V2_SCHEMA_MODELS.items():
        committed = json.loads((schema_root / filename).read_text(encoding="utf-8"))
        assert committed == export_schema(model, filename), filename
