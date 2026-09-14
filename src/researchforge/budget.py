"""Thread-safe aggregate OpenAI budget reservation."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterator
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
    """Reserve worst-case cost atomically with crash-safe short reservation leases."""

    def __init__(
        self,
        cap: Decimal = Decimal("20.00"),
        *,
        spent: Decimal = Decimal(0),
        state_path: Path | None = None,
        reservation_ttl_seconds: float = 300.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if cap <= 0:
            raise ValueError("budget cap must be positive")
        if spent < 0 or spent > cap:
            raise ValueError("initial spend must be within the budget cap")
        if reservation_ttl_seconds <= 0:
            raise ValueError("reservation TTL must be positive")
        self._cap = cap
        self._spent = spent
        self._reservations: dict[str, tuple[Decimal, float]] = {}
        self._state_path = state_path.resolve() if state_path is not None else None
        self._reservation_ttl_seconds = reservation_ttl_seconds
        self._clock = clock
        self._lock = threading.RLock()
        if self._state_path is not None:
            with self._guard():
                if not self._state_path.exists():
                    self._persist_locked()

    def _reload_locked(self) -> bool:
        if self._state_path is None or not self._state_path.exists():
            return False
        state = json.loads(self._state_path.read_text(encoding="utf-8"))
        persisted_cap = Decimal(str(state["cap"]))
        if persisted_cap != self._cap:
            raise ValueError("persisted budget cap differs from configured cap")
        self._spent = Decimal(str(state["spent"]))
        now = self._clock()
        migrated_or_pruned = False
        reservations: dict[str, tuple[Decimal, float]] = {}
        for key, value in state.get("reservations", {}).items():
            if isinstance(value, dict):
                amount = Decimal(str(value["amount"]))
                created_at = float(value.get("created_at", 0))
            else:
                # Legacy ledgers did not persist reservation ownership/age. After a restart they
                # cannot prove an in-flight provider call, so treat them as stale rather than
                # reserving project budget forever.
                amount = Decimal(str(value))
                created_at = 0.0
                migrated_or_pruned = True
            if amount < 0:
                raise ValueError("persisted reservation cannot be negative")
            if created_at <= 0 or now - created_at >= self._reservation_ttl_seconds:
                migrated_or_pruned = True
                continue
            reservations[str(key)] = (amount, created_at)
        self._reservations = reservations
        if self._spent < 0 or self._spent > self._cap:
            raise ValueError("persisted spend is outside the budget cap")
        if self._spent + self._reserved_total() > self._cap:
            raise ValueError("persisted reservations exceed the budget cap")
        return migrated_or_pruned

    def _reserved_total(self) -> Decimal:
        return sum(
            (amount for amount, _created_at in self._reservations.values()),
            start=Decimal(0),
        )

    @contextmanager
    def _guard(self) -> Iterator[None]:
        with self._lock:
            if self._state_path is None:
                yield
                return
            lock_path = self._state_path.with_name(f".{self._state_path.name}.lock")
            with exclusive_file_lock(lock_path):
                if self._reload_locked():
                    self._persist_locked()
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
                key: {"amount": format(value, "f"), "created_at": created_at}
                for key, (value, created_at) in sorted(self._reservations.items())
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
                self._reserved_total(),
            )

    def reserve(self, worst_case_cost: Decimal) -> str:
        if worst_case_cost < 0:
            raise ValueError("worst-case cost cannot be negative")
        with self._guard():
            reserved = self._reserved_total()
            if self._spent + reserved + worst_case_cost > self._cap:
                raise BudgetExceededError("OpenAI aggregate project budget would be exceeded")
            reservation_id = f"reservation_{uuid.uuid4().hex}"
            self._reservations[reservation_id] = (worst_case_cost, self._clock())
            self._persist_locked()
            return reservation_id

    def complete(self, reservation_id: str, actual_cost: Decimal) -> None:
        if actual_cost < 0:
            raise ValueError("actual cost cannot be negative")
        with self._guard():
            reserved, _created_at = self._reservations[reservation_id]
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
