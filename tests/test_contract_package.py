"""Regression tests for the dependency-free V1.4 contract package."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from researchforge.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_contract_validator_passes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validate_contracts.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "PASS: 5 active V1.5 productization" in completed.stdout
    assert "12 V1.4" in completed.stdout


def test_current_catalog_uses_v14_artifact_version() -> None:
    schema_paths = sorted((ROOT / "schemas" / "v1.4").glob("*.schema.json"))
    example_paths = sorted((ROOT / "examples" / "contracts" / "v1.4").glob("*.json"))

    assert len(schema_paths) == 19
    assert len(example_paths) == 12
    for path in example_paths:
        assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == "1.4.0"


def test_historical_scope_hashes_are_immutable() -> None:
    expected = {
        "researchforge-v1.3-scope.md": (
            "b7c1a17e705550122a97296ef255660879f060911a2c01d27d1793bb9ece68a7"
        ),
        "researchforge-v1.2-scope-freeze.md": (
            "513f4a9ae8eabab7a77cb34dedabf6b064a0f9a5710386856f93a7219250816e"
        ),
    }

    for name, expected_digest in expected.items():
        path = ROOT / "docs" / "product" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest


def test_cli_reports_the_bounded_product_runtime(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    main(["--artifact-root", str(tmp_path), "catalog"])
    output = capsys.readouterr().out

    assert '"implementation_level": "V1_5_REAL_DATA"' in output
    assert '"data_namespace": "product"' in output
    assert '"filing_analysis"' in output
    assert '"peer_comparison"' not in output
