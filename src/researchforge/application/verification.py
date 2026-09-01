"""Deterministic financial and coverage verifier, independent of LangGraph."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from researchforge.application.research import LoadedResearchData
from researchforge.domain.finance import (
    cash_conversion,
    gross_margin,
    gross_profit,
    growth_rate,
    profit_cash_divergence,
)

VERIFIER_VERSION = "1.0.0"
COVERAGE_REQUIREMENTS = {
    "operating_cash_flow": "performed",
    "accounts_receivable": "performed",
    "inventory": "performed",
    "cash_conversion": "performed",
    "profit_cash_divergence": "performed",
    "one_off_contribution": "recorded",
    "counter_evidence": "performed",
}


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _check(
    code: str,
    passed: bool,
    expected: str,
    observed: str,
    *,
    fact_ids: Iterable[str] = (),
    evidence_ids: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "check_code": code,
        "status": "PASS" if passed else "FAIL",
        "expected": expected,
        "observed": observed,
        "fact_ids": list(fact_ids),
        "evidence_ids": list(evidence_ids),
    }


def _calculated_value(
    calculation: dict[str, Any],
    facts: dict[str, dict[str, Any]],
) -> Decimal | None:
    inputs = [facts[fact_id] for fact_id in calculation["input_fact_ids"]]
    by_metric = {fact["metric_code"]: Decimal(fact["value"]) for fact in inputs}
    formula = calculation["formula_code"]
    if formula == "gross_profit":
        result = gross_profit(by_metric.get("revenue"), by_metric.get("operating_cost"))
    elif formula == "gross_margin":
        profit = gross_profit(by_metric.get("revenue"), by_metric.get("operating_cost"))
        result = gross_margin(profit.value, by_metric.get("revenue"))
    elif formula == "cash_conversion":
        result = cash_conversion(by_metric.get("operating_cash_flow"), by_metric.get("net_income"))
    elif formula == "profit_cash_divergence":
        result = profit_cash_divergence(
            by_metric.get("net_income"), by_metric.get("operating_cash_flow")
        )
    elif formula in {"revenue_growth", "profit_growth"}:
        current = Decimal(inputs[0]["value"])
        previous = Decimal(inputs[1]["value"])
        result = growth_rate(current, previous)
    else:
        return None
    return result.value


class FinancialVerifier:
    """Recompute important values and enforce evidence/coverage invariants."""

    def __init__(self, *, clock: Callable[[], datetime] = _default_clock) -> None:
        self.clock = clock

    def evaluate(
        self,
        *,
        case_id: str,
        manifest: dict[str, Any],
        result: dict[str, Any],
        trace: dict[str, Any],
        calculations: list[dict[str, Any]],
        loaded: LoadedResearchData,
        expected_calculations: dict[str, str],
        ground_truth_hash: str | None = None,
        tool_records: Iterable[dict[str, Any]] = (),
    ) -> dict[str, Any]:
        facts = {fact["fact_id"]: fact for fact in loaded.facts}
        sources = {source["document_id"]: source for source in loaded.source_documents}
        tool_record_ids = {record["tool_record_id"] for record in tool_records}
        deterministic: list[dict[str, Any]] = []

        identity_ok = (
            manifest["run_id"] == result["run_id"] == trace["run_id"]
            and manifest["lifecycle_state"] == trace["terminal_state"] == "succeeded"
        )
        deterministic.append(
            _check(
                "artifact_identity_and_terminal_state",
                identity_ok,
                "manifest, result and trace share one succeeded run_id",
                (
                    f"manifest={manifest['run_id']}:{manifest['lifecycle_state']}; "
                    f"result={result['run_id']}; trace={trace['run_id']}:{trace['terminal_state']}"
                ),
            )
        )

        required_result_keys = {
            "schema_version",
            "result_id",
            "run_id",
            "mandatory_checks",
            "claims",
            "source_document_ids",
            "evidence_cutoff",
        }
        schema_shape_ok = result.get("schema_version") == "1.4.0" and required_result_keys <= set(
            result
        )
        deterministic.append(
            _check(
                "schema_contract_shape",
                schema_shape_ok,
                "V1.4 result contains every verifier-required contract field",
                "required fields present" if schema_shape_ok else "required fields missing",
            )
        )

        calculation_checks: list[dict[str, Any]] = []
        for calculation in calculations:
            formula = calculation["formula_code"]
            referenced = calculation["input_fact_ids"]
            references_exist = all(fact_id in facts for fact_id in referenced)
            recomputed = _calculated_value(calculation, facts) if references_exist else None
            observed = Decimal(calculation["value"]) if calculation["value"] is not None else None
            expected = (
                Decimal(expected_calculations[formula])
                if formula in expected_calculations
                else recomputed
            )
            passed = references_exist and recomputed == observed == expected
            calculation_checks.append(
                _check(
                    f"calculation_{formula}",
                    passed,
                    f"recomputed and golden value equal {expected}",
                    f"persisted={observed}; recomputed={recomputed}",
                    fact_ids=referenced,
                )
            )
        deterministic.extend(calculation_checks)

        cutoff = datetime.fromisoformat(result["evidence_cutoff"])
        point_in_time_ok = all(
            datetime.fromisoformat(source["published_at"]) <= cutoff for source in sources.values()
        ) and all(
            datetime.fromisoformat(fact["source"]["published_at"]) <= cutoff
            for fact in facts.values()
        )
        deterministic.append(
            _check(
                "point_in_time_validity",
                point_in_time_ok,
                "every fact and source was published by the evidence cutoff",
                f"checked {len(facts)} facts and {len(sources)} sources at {cutoff.isoformat()}",
                fact_ids=facts,
            )
        )

        claim_fact_ids = {fact_id for claim in result["claims"] for fact_id in claim["fact_ids"]}
        claim_evidence_ids = {
            evidence_id
            for claim in result["claims"]
            for evidence_id in claim["support_evidence_ids"]
        }
        material_claims_grounded = all(
            claim["fact_ids"] or claim["support_evidence_ids"]
            for claim in result["claims"]
            if claim["materiality"] == "material"
        )
        citations_ok = (
            claim_fact_ids <= facts.keys()
            and not claim_evidence_ids
            and set(result["source_document_ids"]) <= sources.keys()
            and material_claims_grounded
        )
        deterministic.append(
            _check(
                "citation_existence",
                citations_ok,
                "all fact/source citations exist and material claims are grounded",
                (
                    f"{len(claim_fact_ids)} fact citations, {len(claim_evidence_ids)} evidence "
                    f"citations, {len(result['source_document_ids'])} source citations"
                ),
                fact_ids=claim_fact_ids,
                evidence_ids=claim_evidence_ids,
            )
        )

        trace_tool_ids = {
            tool_id for stage in trace["stages"] for tool_id in stage["tool_record_ids"]
        }
        tools_ok = trace_tool_ids <= tool_record_ids
        deterministic.append(
            _check(
                "tool_record_existence",
                tools_ok,
                "every traced tool call resolves to a Tool Record",
                f"{len(trace_tool_ids)} traced calls and {len(tool_record_ids)} records",
            )
        )

        period_contexts = {
            (
                fact["company"]["company_id"],
                fact["period"]["period_end"],
                fact["period"]["accounting_standard"],
                fact["period"]["statement_scope"],
            )
            for fact in facts.values()
        }
        company_periods = {
            (company_id, period_end) for company_id, period_end, _, _ in period_contexts
        }
        period_ok = len(period_contexts) == len(company_periods)
        deterministic.append(
            _check(
                "period_compatibility",
                period_ok,
                "all facts share period end, accounting standard and statement scope",
                f"observed company-period contexts={sorted(period_contexts)}",
                fact_ids=facts,
            )
        )

        checks_by_code = {item["check_code"]: item for item in result["mandatory_checks"]}
        coverage: list[dict[str, Any]] = []
        for code, requirement in COVERAGE_REQUIREMENTS.items():
            item = checks_by_code.get(code)
            if requirement == "recorded":
                passed = item is not None and item["status"] in {
                    "performed",
                    "unavailable",
                    "not_applicable",
                }
            else:
                passed = item is not None and item["status"] == requirement
            coverage.append(
                _check(
                    f"coverage_{code}",
                    passed,
                    f"mandatory check is {requirement}",
                    "missing" if item is None else f"status={item['status']}; {item['finding']}",
                    fact_ids=[] if item is None else item["fact_ids"],
                    evidence_ids=[] if item is None else item["evidence_ids"],
                )
            )

        all_checks = deterministic + coverage
        failures = [item for item in all_checks if item["status"] == "FAIL"]
        failure_events = [
            self._failure_event(manifest["run_id"], case_id, item, index)
            for index, item in enumerate(failures, 1)
        ]
        calculation_accuracy = self._rate(calculation_checks)
        evidence_coverage = self._rate(coverage)
        citation_check = next(
            item for item in deterministic if item["check_code"] == "citation_existence"
        )
        critical_omissions = sum(
            1 for event in failure_events if event["failure_label"] == "CRITICAL_OMISSION"
        )
        critical_omission_rate = critical_omissions / len(coverage)
        citation_accuracy = 1.0 if citation_check["status"] == "PASS" else 0.0
        task_score = (
            0.30 * calculation_accuracy
            + 0.25 * citation_accuracy
            + 0.25 * evidence_coverage
            + 0.20 * (1 - critical_omission_rate)
        )
        ground_truth = {
            "case_id": case_id,
            "expected_calculations": expected_calculations,
            "coverage_requirements": COVERAGE_REQUIREMENTS,
        }
        return {
            "schema_version": "1.4.0",
            "evaluation_id": f"eval_{manifest['run_id']}_{case_id}",
            "run_id": manifest["run_id"],
            "case_id": case_id,
            "skill_version": manifest["configuration"]["skill_version"],
            "skill_hash": manifest["configuration"]["skill_hash"],
            "verifier_version": VERIFIER_VERSION,
            "ground_truth_hash": ground_truth_hash or _hash_payload(ground_truth),
            "deterministic_checks": deterministic,
            "coverage_checks": coverage,
            "qualitative_checks": [],
            "failure_events": failure_events,
            "metrics": {
                "task_score": task_score,
                "calculation_accuracy": calculation_accuracy,
                "evidence_coverage": evidence_coverage,
                "critical_omission_rate": critical_omission_rate,
                "citation_accuracy": citation_accuracy,
            },
            "created_at": self.clock().isoformat(),
        }

    @staticmethod
    def _rate(checks: list[dict[str, Any]]) -> float:
        if not checks:
            return 0.0
        passed = sum(1 for item in checks if str(item["status"]) == "PASS")
        return passed / len(checks)

    @staticmethod
    def _failure_event(
        run_id: str,
        case_id: str,
        check: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        code = check["check_code"]
        if code.startswith("calculation_"):
            label = "CALCULATION_ERROR"
            severity = "critical"
        elif code == "period_compatibility" or code == "point_in_time_validity":
            label = "PERIOD_ERROR"
            severity = "critical"
        elif code.startswith("coverage_"):
            label = "CRITICAL_OMISSION"
            severity = "major"
        elif code == "citation_existence":
            label = "CITATION_ERROR"
            severity = "critical"
        elif code == "tool_record_existence":
            label = "TOOL_MISUSE"
            severity = "major"
        else:
            label = "OVERCLAIM"
            severity = "major"
        return {
            "failure_id": f"failure_{run_id}_{case_id}_{index:03d}",
            "failure_label": label,
            "signature": f"{code}:{_hash_payload(check)[:16]}",
            "severity": severity,
            "check_codes": [code],
            "description": f"Expected {check['expected']}; observed {check['observed']}",
        }
