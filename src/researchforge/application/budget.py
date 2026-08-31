"""Thread-safe aggregate OpenAI budget reservation."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from decimal import Decimal


class BudgetExceededError(RuntimeError):
    """Raised before provider contact when the aggregate cap would be exceeded."""


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    """Current in-process budget state."""

    cap: Decimal
    spent: Decimal
    reserved: Decimal


class BudgetLedger:
    """Reserve worst-case cost atomically within one application process."""

    def __init__(self, cap: Decimal = Decimal("20.00")) -> None:
        if cap <= 0:
            raise ValueError("budget cap must be positive")
        self._cap = cap
        self._spent = Decimal(0)
        self._reservations: dict[str, Decimal] = {}
        self._lock = threading.Lock()

    def snapshot(self) -> BudgetSnapshot:
        with self._lock:
            return BudgetSnapshot(
                self._cap,
                self._spent,
                sum(self._reservations.values(), start=Decimal(0)),
            )

    def reserve(self, worst_case_cost: Decimal) -> str:
        if worst_case_cost < 0:
            raise ValueError("worst-case cost cannot be negative")
        with self._lock:
            reserved = sum(self._reservations.values(), start=Decimal(0))
            if self._spent + reserved + worst_case_cost > self._cap:
                raise BudgetExceededError("OpenAI aggregate project budget would be exceeded")
            reservation_id = f"reservation_{uuid.uuid4().hex}"
            self._reservations[reservation_id] = worst_case_cost
            return reservation_id

    def complete(self, reservation_id: str, actual_cost: Decimal) -> None:
        if actual_cost < 0:
            raise ValueError("actual cost cannot be negative")
        with self._lock:
            reserved = self._reservations.pop(reservation_id)
            if actual_cost > reserved:
                raise ValueError("actual cost exceeds its worst-case reservation")
            self._spent += actual_cost

    def release(self, reservation_id: str) -> None:
        with self._lock:
            self._reservations.pop(reservation_id, None)
