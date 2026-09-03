"""Contract checks for the integration envelope, not an alternate research implementation."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from scripts.n8n_smoke import validate_output
from scripts.validate_contracts import ROOT, ContractError, load_json


@pytest.mark.parametrize("case", ["cn_300750-2024H1", "cn_300750-2024FY", "cn_002594-2024H1"])
def test_real_n8n_output_validates(case: str) -> None:
    validate_output(load_json(ROOT / f"docs/evidence/v1.5-n8n/{case}.json"))


@pytest.mark.parametrize(
    "patch",
    [
        {"conclusion": "unsupported prose"},
        {"research_result": {}},
        {"calculations": []},
    ],
)
def test_failure_envelope_cannot_impersonate_a_report(patch: dict[str, Any]) -> None:
    failure = load_json(ROOT / "examples/contracts/v1.5/n8n-research-output.error.example.json")
    failure.update(patch)
    with pytest.raises(ContractError):
        validate_output(failure)


def test_success_requires_backend_artifacts_and_cannot_silently_change_versions() -> None:
    output = load_json(ROOT / "docs/evidence/v1.5-n8n/cn_300750-2024H1.json")
    for field in ["research_result", "research_trace", "supporting_evidence", "calculations"]:
        changed = copy.deepcopy(output)
        del changed[field]
        with pytest.raises(ContractError):
            validate_output(changed)
    output["research_result"]["schema_version"] = "1.5.0"
    with pytest.raises(ContractError):
        validate_output(output)
