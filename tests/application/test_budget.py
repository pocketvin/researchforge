"""Aggregate budget guard tests."""

from __future__ import annotations

from decimal import Decimal

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
