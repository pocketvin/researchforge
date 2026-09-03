"""Shared abstention errors for bounded disclosure ingestion."""

from __future__ import annotations

from typing import Any

JsonObject = dict[str, Any]


class IngestionAbstention(ValueError):
    """A bounded refusal to promote unverified disclosure content."""

    def __init__(self, code: str, stage: str, reason: str) -> None:
        super().__init__(reason)
        self.code = code
        self.stage = stage
        self.reason = reason
        self.acquisition: JsonObject | None = None

    def artifact(self) -> JsonObject:
        return {"code": self.code, "stage": self.stage, "reason": self.reason}
