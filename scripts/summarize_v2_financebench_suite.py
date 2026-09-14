"""Summarize one FinanceBench public-development suite execution by stratum and company."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from researchforge.v2.benchmarks.suite import BenchmarkSuiteExecution, BenchmarkSuiteManifest
from researchforge.v2.benchmarks.suite_summary import summarize_suite_execution

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "v2"
    / "benchmarks"
    / "financebench-public-development-10-v1.json"
)


def _assessment_for(
    case_id: str, run_id: str, path: Path, *, prefer_assessed: bool
) -> dict[str, Any]:
    candidate = path.resolve()
    if prefer_assessed:
        assessed = candidate.with_name(f"{run_id}-{case_id}-assessed.json")
        if assessed.is_file():
            candidate = assessed
    payload = json.loads(candidate.read_text())
    if not isinstance(payload, dict) or not {"case_id", "eligible", "metrics"} <= set(payload):
        raise ValueError(f"not a quality assessment: {candidate}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("execution", type=Path)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base-only", action="store_true", help="Ignore post-run assessed files")
    args = parser.parse_args()
    execution = BenchmarkSuiteExecution.model_validate_json(args.execution.resolve().read_text())
    suite = BenchmarkSuiteManifest.model_validate_json(args.suite.resolve().read_text())
    assessments: dict[str, dict[str, Any]] = {}
    for case in execution.cases:
        if case.status != "succeeded" or not case.run_id or not case.assessment_path:
            continue
        assessments[case.financebench_id] = _assessment_for(
            case.financebench_id,
            case.run_id,
            Path(case.assessment_path),
            prefer_assessed=not args.base_only,
        )
    summary = summarize_suite_execution(suite, execution, assessments)
    payload = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    output = args.output or args.execution.with_name(args.execution.stem + "-summary.json")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload)
    print(
        json.dumps(
            {
                "output": str(output),
                "suite_id": suite.suite_id,
                "execution_id": execution.execution_id,
                "assessment_cases": len(assessments),
                "overall_score": None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
