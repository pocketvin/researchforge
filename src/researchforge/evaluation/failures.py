"""V1.8 product-agent failure taxonomy and deterministic classification."""

from __future__ import annotations

from typing import Any, Literal

FailureClass = Literal[
    "COMPANY_RESOLUTION_FAILURE",
    "DISCOVERY_FAILURE",
    "ACQUISITION_FAILURE",
    "PARSER_FAILURE",
    "RETRIEVAL_FAILURE",
    "INSUFFICIENT_EVIDENCE",
    "TOOL_FAILURE",
    "MODEL_SCHEMA_FAILURE",
    "GROUNDING_FAILURE",
    "CITATION_FAILURE",
    "TIMEOUT",
    "BUDGET_EXCEEDED",
    "STATE_RECOVERY_FAILURE",
    "INFRASTRUCTURE_FAILURE",
]

FAILURE_CLASSES: tuple[FailureClass, ...] = (
    "COMPANY_RESOLUTION_FAILURE",
    "DISCOVERY_FAILURE",
    "ACQUISITION_FAILURE",
    "PARSER_FAILURE",
    "RETRIEVAL_FAILURE",
    "INSUFFICIENT_EVIDENCE",
    "TOOL_FAILURE",
    "MODEL_SCHEMA_FAILURE",
    "GROUNDING_FAILURE",
    "CITATION_FAILURE",
    "TIMEOUT",
    "BUDGET_EXCEEDED",
    "STATE_RECOVERY_FAILURE",
    "INFRASTRUCTURE_FAILURE",
)

_CODE_MAP: dict[str, FailureClass] = {
    "COMPANY_NOT_UNAMBIGUOUS": "COMPANY_RESOLUTION_FAILURE",
    "DISCLOSURE_PROVIDER_UNAVAILABLE": "DISCOVERY_FAILURE",
    "UNTRUSTED_SOURCE_URI": "DISCOVERY_FAILURE",
    "DISCLOSURE_NOT_PDF": "ACQUISITION_FAILURE",
    "DISCLOSURE_SIZE_INVALID": "ACQUISITION_FAILURE",
    "DISCLOSURE_HASH_MISMATCH": "ACQUISITION_FAILURE",
    "DISCLOSURE_SIZE_MISMATCH": "ACQUISITION_FAILURE",
    "DISCLOSURE_PARSE_FAILED": "PARSER_FAILURE",
    "OUTPUT_SCHEMA_INVALID": "MODEL_SCHEMA_FAILURE",
    "BUDGET_EXCEEDED": "BUDGET_EXCEEDED",
    "RUN_TIMEOUT": "TIMEOUT",
    "TIMEOUT": "TIMEOUT",
    "INSUFFICIENT_DATA": "INSUFFICIENT_EVIDENCE",
}

_STAGE_MAP: dict[str, FailureClass] = {
    "discovery": "DISCOVERY_FAILURE",
    "acquisition": "ACQUISITION_FAILURE",
    "parsing": "PARSER_FAILURE",
    "retrieval": "RETRIEVAL_FAILURE",
    "verification": "GROUNDING_FAILURE",
    "recovery": "STATE_RECOVERY_FAILURE",
}


def classify_failure(manifest: dict[str, Any]) -> FailureClass | None:
    """Classify a terminal manifest without inventing a root cause."""
    failure = manifest.get("failure")
    if not isinstance(failure, dict):
        return None
    code = str(failure.get("code") or failure.get("failure_code") or "").upper()
    if code in _CODE_MAP:
        return _CODE_MAP[code]
    if "CITATION" in code:
        return "CITATION_FAILURE"
    if "GROUND" in code or "EVIDENCE_ID" in code or "FACT_ID" in code:
        return "GROUNDING_FAILURE"
    if "TOOL" in code:
        return "TOOL_FAILURE"
    if "TIMEOUT" in code or "DEADLINE" in code:
        return "TIMEOUT"
    stage = str(failure.get("stage") or failure.get("failure_stage") or "").casefold()
    if stage in _STAGE_MAP:
        return _STAGE_MAP[stage]
    return "INFRASTRUCTURE_FAILURE"


def failure_record(manifest: dict[str, Any]) -> dict[str, Any] | None:
    """Return interview-friendly, traceable failure metadata for a failed run."""
    failure_class = classify_failure(manifest)
    if failure_class is None:
        return None
    raw_failure = manifest.get("failure")
    failure: dict[str, Any] = raw_failure if isinstance(raw_failure, dict) else {}
    return {
        "schema_version": "1.8.0",
        "run_id": str(manifest.get("run_id", "unknown")),
        "failure_class": failure_class,
        "stage": failure.get("stage") or failure.get("failure_stage"),
        "code": failure.get("code") or failure.get("failure_code"),
        "retryable": bool(failure.get("retryable", False)),
        "root_cause": failure.get("message") or failure.get("reason") or "not recorded",
        "regression_case_recommended": failure_class not in {"INSUFFICIENT_EVIDENCE"},
    }
