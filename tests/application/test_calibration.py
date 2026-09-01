"""No-network calibration and formal-gate tests."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from researchforge.application.budget import BudgetLedger
from researchforge.application.calibration import (
    CALIBRATION_CONTEXT_HASH,
    CalibrationBlocked,
    OpenAICalibrationRunner,
    calibration_artifact_passed,
)
from researchforge.application.research import ConclusionDraft


class FakeCalibrationGenerator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._usage: dict[str, int | float | str] = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "latency_ms": 1,
            "tool_calls": 0,
            "estimated_cost": 0.00008,
            "cost_currency": "USD",
        }

    @property
    def prompt_hashes(self) -> dict[str, str]:
        return {"resolved_instructions": hashlib.sha256(b"calibration").hexdigest()}

    @property
    def worst_case_cost(self) -> Decimal:
        return Decimal("0.0064")

    @property
    def usage(self) -> dict[str, int | float | str]:
        return dict(self._usage)

    def begin_run(self) -> None:
        return None

    def generate(self, context: dict[str, Any]) -> ConclusionDraft:
        self.calls.append(context)
        return ConclusionDraft(
            executive_summary="Synthetic calibration only.",
            earnings_quality_text="All supplied checks were addressed.",
            gross_margin_text="No gross-margin input was supplied.",
            limitations=["Not research evidence."],
            reported_check_codes=[
                "operating_cash_flow",
                "accounts_receivable",
                "inventory",
                "cash_conversion",
                "profit_cash_divergence",
                "one_off_contribution",
                "counter_evidence",
            ],
        )


def build_runner(
    tmp_path: Path,
    generator: FakeCalibrationGenerator,
    *,
    key_ready: bool,
) -> OpenAICalibrationRunner:
    return OpenAICalibrationRunner(
        artifact_root=tmp_path / "artifacts",
        ledger=BudgetLedger(state_path=tmp_path / "budget.json"),
        rotated_key_ready=key_ready,
        generator_factory=(lambda _ledger: generator) if key_ready else None,
        worst_case_cost=Decimal("0.0064"),
        clock=lambda: datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
    )


def test_calibration_preflight_blocks_without_provider_contact(tmp_path: Path) -> None:
    generator = FakeCalibrationGenerator()
    runner = build_runner(tmp_path, generator, key_ready=False)

    report = runner.preflight()

    assert report["status"] == "BLOCKED"
    assert report["provider_contacted"] is False
    with pytest.raises(CalibrationBlocked):
        runner.run()
    assert generator.calls == []


def test_calibration_is_synthetic_bounded_and_idempotent(tmp_path: Path) -> None:
    generator = FakeCalibrationGenerator()
    runner = build_runner(tmp_path, generator, key_ready=True)

    artifact = runner.run()
    repeated = runner.run()

    assert artifact == repeated
    assert artifact["status"] == "PASS"
    assert artifact["context_hash"] == CALIBRATION_CONTEXT_HASH
    assert artifact["research_hypothesis_supported"] is False
    assert artifact["evidence_class"] == "SYNTHETIC_CALIBRATION_ONLY_NOT_RESEARCH_EVIDENCE"
    assert calibration_artifact_passed(tmp_path / "artifacts")
    assert len(generator.calls) == 1
