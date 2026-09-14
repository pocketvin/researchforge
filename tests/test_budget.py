"""Aggregate budget guard tests."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from researchforge.budget import BudgetExceededError, BudgetLedger


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


def test_budget_state_survives_restart_while_reservation_lease_is_live(tmp_path: Path) -> None:
    state_path = tmp_path / "budget" / "project-openai.json"
    clock = [1000.0]
    ledger = BudgetLedger(
        Decimal("1.00"), state_path=state_path, reservation_ttl_seconds=300, clock=lambda: clock[0]
    )
    first = ledger.reserve(Decimal("0.25"))
    ledger.complete(first, Decimal("0.10"))
    ledger.reserve(Decimal("0.30"))

    restored = BudgetLedger(
        Decimal("1.00"), state_path=state_path, reservation_ttl_seconds=300, clock=lambda: clock[0]
    )

    assert restored.snapshot().spent == Decimal("0.10")
    assert restored.snapshot().reserved == Decimal("0.30")
    with pytest.raises(BudgetExceededError):
        restored.reserve(Decimal("0.61"))


def test_budget_reclaims_stale_reservation_after_crash_lease_expires(tmp_path: Path) -> None:
    state_path = tmp_path / "budget" / "project-openai.json"
    clock = [1000.0]
    ledger = BudgetLedger(
        Decimal("1.00"), state_path=state_path, reservation_ttl_seconds=300, clock=lambda: clock[0]
    )
    ledger.reserve(Decimal("0.70"))
    clock[0] += 301

    restored = BudgetLedger(
        Decimal("1.00"), state_path=state_path, reservation_ttl_seconds=300, clock=lambda: clock[0]
    )

    assert restored.snapshot().reserved == Decimal(0)
    replacement = restored.reserve(Decimal("0.90"))
    restored.release(replacement)


def test_budget_migrates_legacy_amount_only_reservations_as_stale(tmp_path: Path) -> None:
    state_path = tmp_path / "budget" / "project-openai.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        '{"currency":"USD","cap":"1.00","spent":"0.10","reservations":{"legacy":"0.70"}}',
        encoding="utf-8",
    )

    restored = BudgetLedger(Decimal("1.00"), state_path=state_path)

    snapshot = restored.snapshot()
    assert snapshot.spent == Decimal("0.10")
    assert snapshot.reserved == Decimal(0)
    assert '"reservations": {}' in state_path.read_text(encoding="utf-8")
