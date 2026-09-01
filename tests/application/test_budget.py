"""Aggregate budget guard tests."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from researchforge.application.budget import BudgetExceededError, BudgetLedger


def test_budget_reserves_completes_and_releases() -> None:
    ledger = BudgetLedger(Decimal("1.00"))
    first = ledger.reserve(Decimal("0.60"))

    with pytest.raises(BudgetExceededError):
        ledger.reserve(Decimal("0.41"))

    ledger.complete(first, Decimal("0.40"))
    second = ledger.reserve(Decimal("0.60"))
    ledger.release(second)

    snapshot = ledger.snapshot()
    assert snapshot.spent == Decimal("0.40")
    assert snapshot.reserved == Decimal(0)


def test_budget_state_survives_restart_and_keeps_open_reservations(tmp_path: Path) -> None:
    state_path = tmp_path / "budget" / "project-openai.json"
    ledger = BudgetLedger(Decimal("1.00"), state_path=state_path)
    first = ledger.reserve(Decimal("0.25"))
    ledger.complete(first, Decimal("0.10"))
    ledger.reserve(Decimal("0.30"))

    restored = BudgetLedger(Decimal("1.00"), state_path=state_path)

    assert restored.snapshot().spent == Decimal("0.10")
    assert restored.snapshot().reserved == Decimal("0.30")
    with pytest.raises(BudgetExceededError):
        restored.reserve(Decimal("0.61"))
