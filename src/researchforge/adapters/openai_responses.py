"""OpenAI Responses API adapter behind the bounded conclusion port."""

from __future__ import annotations

import hashlib
import json
import time
from decimal import Decimal
from typing import Any, Literal, Protocol, cast

from pydantic import ValidationError

from researchforge.application.budget import BudgetLedger
from researchforge.application.research import ConclusionDraft, StructuredOutputError

LUNA_INPUT_USD_PER_MILLION = Decimal("0.20")
LUNA_OUTPUT_USD_PER_MILLION = Decimal("1.20")
CONCLUSION_INSTRUCTION_WRAPPER = (
    "Use only the supplied precomputed facts. Do not add numbers, sources, causal claims, "
    "investment advice, or facts from memory. reported_check_codes must contain exactly "
    "the checks explicitly recorded in your answer; do not claim a check you did not address."
)


def luna_worst_case_cost(max_input_tokens: int, max_output_tokens: int) -> Decimal:
    """Return the frozen pre-dispatch cost bound for one Responses request."""
    if max_input_tokens < 0 or max_output_tokens < 0:
        raise ValueError("token bounds cannot be negative")
    return (
        Decimal(max_input_tokens) * LUNA_INPUT_USD_PER_MILLION
        + Decimal(max_output_tokens) * LUNA_OUTPUT_USD_PER_MILLION
    ) / Decimal(1_000_000)


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
        max_output_tokens: int = 4000,
        skill_content: str | None = None,
        reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "medium",
    ) -> None:
        self.responses = responses
        self.ledger = ledger
        self.model = model
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.skill_content = skill_content
        self.reasoning_effort = reasoning_effort
        self._usage = self._empty_usage()

    @staticmethod
    def _empty_usage() -> dict[str, int | float | str]:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0,
            "tool_calls": 0,
            "estimated_cost": 0.0,
            "cost_currency": "USD",
        }

    def begin_run(self) -> None:
        """Reset per-run usage before one LangGraph invocation."""
        self._usage = self._empty_usage()

    @property
    def usage(self) -> dict[str, int | float | str]:
        """Return usage accumulated across the one allowed repair route."""
        return dict(self._usage)

    def _instructions(self) -> str:
        skill_instructions = (
            "\n\nTrusted research procedure:\n" + self.skill_content
            if self.skill_content is not None
            else (
                "\n\nNo fundamental-research skill procedure is supplied for this Base condition."
            )
        )
        return CONCLUSION_INSTRUCTION_WRAPPER + skill_instructions

    @property
    def prompt_hashes(self) -> dict[str, str]:
        """Hash both the invariant wrapper and skill-resolved instructions."""
        return {
            "research_wrapper": hashlib.sha256(CONCLUSION_INSTRUCTION_WRAPPER.encode()).hexdigest(),
            "resolved_instructions": hashlib.sha256(self._instructions().encode()).hexdigest(),
        }

    def _worst_case_cost(self) -> Decimal:
        return luna_worst_case_cost(self.max_input_tokens, self.max_output_tokens)

    @property
    def worst_case_cost(self) -> Decimal:
        """Expose the pre-dispatch reservation used by formal preflight."""
        return self._worst_case_cost()

    def generate(self, context: dict[str, Any]) -> ConclusionDraft:
        prompt = json.dumps(context, ensure_ascii=False, sort_keys=True)
        if (len(prompt.encode()) + 1) // 2 > self.max_input_tokens:
            raise ValueError("bounded conclusion input exceeds its token safety estimate")
        reservation_id = self.ledger.reserve(self._worst_case_cost())
        started = time.perf_counter()
        try:
            response = self.responses.create(
                model=self.model,
                instructions=self._instructions(),
                input=prompt,
                reasoning={"effort": self.reasoning_effort},
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
            # A transport exception can arrive after the provider accepted the request.
            # Charge the full reservation so the USD 20 guard remains conservative.
            self.ledger.complete(reservation_id, self._worst_case_cost())
            raise
        self.ledger.complete(reservation_id, actual_cost)
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        self._usage["input_tokens"] = int(self._usage["input_tokens"]) + input_tokens
        self._usage["output_tokens"] = int(self._usage["output_tokens"]) + output_tokens
        self._usage["total_tokens"] = (
            int(self._usage["total_tokens"]) + input_tokens + output_tokens
        )
        self._usage["latency_ms"] = int(self._usage["latency_ms"]) + elapsed_ms
        self._usage["estimated_cost"] = float(
            Decimal(str(self._usage["estimated_cost"])) + actual_cost
        )
        try:
            draft = ConclusionDraft.model_validate_json(cast(str, response.output_text))
        except ValidationError as exc:
            raise StructuredOutputError("OpenAI conclusion output failed validation") from exc
        if draft.reported_check_codes is None:
            raise StructuredOutputError("OpenAI conclusion omitted procedural coverage attestation")
        return draft
