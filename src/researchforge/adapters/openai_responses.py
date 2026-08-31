"""OpenAI Responses API adapter behind the bounded conclusion port."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Protocol, cast

from pydantic import ValidationError

from researchforge.application.budget import BudgetLedger
from researchforge.application.research import ConclusionDraft, StructuredOutputError

LUNA_INPUT_USD_PER_MILLION = Decimal("0.20")
LUNA_OUTPUT_USD_PER_MILLION = Decimal("1.20")


class ResponsesResource(Protocol):
    """Narrow SDK surface used for dependency injection in tests."""

    def create(self, **kwargs: Any) -> Any:
        """Create one response."""

        ...


class OpenAIResponsesConclusionGenerator:
    """Use Structured Outputs without built-in tools or provider-side storage."""

    def __init__(
        self,
        responses: ResponsesResource,
        ledger: BudgetLedger,
        *,
        model: str = "gpt-5.6-luna",
        max_input_tokens: int = 8000,
        max_output_tokens: int = 1000,
    ) -> None:
        self.responses = responses
        self.ledger = ledger
        self.model = model
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens

    def _worst_case_cost(self) -> Decimal:
        return (
            Decimal(self.max_input_tokens) * LUNA_INPUT_USD_PER_MILLION
            + Decimal(self.max_output_tokens) * LUNA_OUTPUT_USD_PER_MILLION
        ) / Decimal(1_000_000)

    def generate(self, context: dict[str, Any]) -> ConclusionDraft:
        prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
        if len(prompt) // 2 > self.max_input_tokens:
            raise ValueError("bounded conclusion input exceeds its token safety estimate")
        reservation_id = self.ledger.reserve(self._worst_case_cost())
        try:
            response = self.responses.create(
                model=self.model,
                instructions=(
                    "Use only the supplied precomputed facts. Do not add numbers, sources, "
                    "causal claims, investment advice, or facts from memory."
                ),
                input=prompt,
                reasoning={"effort": "medium"},
                max_output_tokens=self.max_output_tokens,
                store=False,
                tools=[],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "researchforge_conclusion_draft",
                        "strict": True,
                        "schema": ConclusionDraft.model_json_schema(),
                    }
                },
            )
            usage = response.usage
            input_tokens = int(usage.input_tokens)
            output_tokens = int(usage.output_tokens)
            actual_cost = (
                Decimal(input_tokens) * LUNA_INPUT_USD_PER_MILLION
                + Decimal(output_tokens) * LUNA_OUTPUT_USD_PER_MILLION
            ) / Decimal(1_000_000)
        except Exception:
            self.ledger.release(reservation_id)
            raise
        try:
            draft = ConclusionDraft.model_validate_json(cast(str, response.output_text))
        except ValidationError as exc:
            self.ledger.complete(reservation_id, actual_cost)
            raise StructuredOutputError("OpenAI conclusion output failed validation") from exc
        self.ledger.complete(reservation_id, actual_cost)
        return draft
