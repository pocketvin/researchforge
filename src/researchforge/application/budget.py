"""Thread-safe aggregate OpenAI budget reservation."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from researchforge.file_lock import exclusive_file_lock


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

    def __init__(
        self,
        cap: Decimal = Decimal("20.00"),
        *,
        spent: Decimal = Decimal(0),
        state_path: Path | None = None,
    ) -> None:
        if cap <= 0:
            raise ValueError("budget cap must be positive")
        if spent < 0 or spent > cap:
            raise ValueError("initial spend must be within the budget cap")
        self._cap = cap
        self._spent = spent
        self._reservations: dict[str, Decimal] = {}
        self._state_path = state_path.resolve() if state_path is not None else None
        self._lock = threading.RLock()
        if self._state_path is not None:
            with self._guard():
                if self._state_path.exists():
                    self._reload_locked()
                else:
                    self._persist_locked()

    def _reload_locked(self) -> None:
        if self._state_path is None or not self._state_path.exists():
            return
        state = json.loads(self._state_path.read_text(encoding="utf-8"))
        persisted_cap = Decimal(str(state["cap"]))
        if persisted_cap != self._cap:
            raise ValueError("persisted budget cap differs from configured cap")
        self._spent = Decimal(str(state["spent"]))
        self._reservations = {
            str(key): Decimal(str(value)) for key, value in state["reservations"].items()
        }
        if self._spent < 0 or self._spent > self._cap:
            raise ValueError("persisted spend is outside the budget cap")
        if self._spent + sum(self._reservations.values(), start=Decimal(0)) > self._cap:
            raise ValueError("persisted reservations exceed the budget cap")

    @contextmanager
    def _guard(self) -> Iterator[None]:
        with self._lock:
            if self._state_path is None:
                yield
                return
            lock_path = self._state_path.with_name(f".{self._state_path.name}.lock")
            with exclusive_file_lock(lock_path):
                self._reload_locked()
                yield

    def _persist_locked(self) -> None:
        if self._state_path is None:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "currency": "USD",
            "cap": format(self._cap, "f"),
            "spent": format(self._spent, "f"),
            "reservations": {
                key: format(value, "f") for key, value in sorted(self._reservations.items())
            },
        }
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self._state_path.parent,
            prefix=f".{self._state_path.name}.",
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self._state_path)
        finally:
            temporary.unlink(missing_ok=True)

    def snapshot(self) -> BudgetSnapshot:
        with self._guard():
            return BudgetSnapshot(
                self._cap,
                self._spent,
                sum(self._reservations.values(), start=Decimal(0)),
            )

    def reserve(self, worst_case_cost: Decimal) -> str:
        if worst_case_cost < 0:
            raise ValueError("worst-case cost cannot be negative")
        with self._guard():
            reserved = sum(self._reservations.values(), start=Decimal(0))
            if self._spent + reserved + worst_case_cost > self._cap:
                raise BudgetExceededError("OpenAI aggregate project budget would be exceeded")
            reservation_id = f"reservation_{uuid.uuid4().hex}"
            self._reservations[reservation_id] = worst_case_cost
            self._persist_locked()
            return reservation_id

    def complete(self, reservation_id: str, actual_cost: Decimal) -> None:
        if actual_cost < 0:
            raise ValueError("actual cost cannot be negative")
        with self._guard():
            reserved = self._reservations[reservation_id]
            if actual_cost > reserved:
                raise ValueError("actual cost exceeds its worst-case reservation")
            if self._spent + actual_cost > self._cap:
                raise BudgetExceededError("OpenAI aggregate project budget would be exceeded")
            self._reservations.pop(reservation_id)
            self._spent += actual_cost
            self._persist_locked()

    def release(self, reservation_id: str) -> None:
        with self._guard():
            self._reservations.pop(reservation_id, None)
            self._persist_locked()
