"""Formal G1 exact-denominator reliability check."""

from __future__ import annotations

from pathlib import Path

from researchforge.application.reliability import run_reliability_batch
from tests.runtime_helpers import build_service


def test_fixed_twenty_run_batch_exceeds_ninety_percent(tmp_path: Path) -> None:
    report = run_reliability_batch(build_service(tmp_path))

    assert report["total_runs"] == 20
    assert report["succeeded_runs"] == 20
    assert report["success_rate"] >= 0.9
    assert report["mode_denominators"] == {
        "company_research": 4,
        "filing_analysis": 4,
        "peer_comparison": 4,
        "thesis_investigation": 4,
        "risk_detection": 4,
    }
