"""Stratified suite summaries without a synthetic composite quality score."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from researchforge.v2.benchmarks.suite import BenchmarkSuiteExecution, BenchmarkSuiteManifest
from researchforge.v2.quality import summarize_quality_results

Json = dict[str, Any]


def summarize_suite_execution(
    suite: BenchmarkSuiteManifest,
    execution: BenchmarkSuiteExecution,
    assessments: dict[str, Json],
) -> Json:
    if execution.suite_hash != suite.suite_hash or execution.suite_id != suite.suite_id:
        raise ValueError("execution does not belong to this benchmark suite")
    suite_cases = {case.financebench_id: case for case in suite.cases}
    if not set(execution.target_case_ids) <= set(suite_cases):
        raise ValueError("execution contains case IDs outside the suite")

    results = [
        assessments[case_id] for case_id in execution.target_case_ids if case_id in assessments
    ]
    by_stratum: dict[str, list[Json]] = defaultdict(list)
    by_company: dict[str, list[Json]] = defaultdict(list)
    for case_id, assessment in assessments.items():
        if case_id not in execution.target_case_ids:
            continue
        case = suite_cases[case_id]
        by_stratum[case.stratum].append(assessment)
        by_company[case.company].append(assessment)

    independence = Counter(
        str(item.get("benchmark_assessor", {}).get("independence"))
        for item in results
        if isinstance(item.get("benchmark_assessor"), dict)
        and item["benchmark_assessor"].get("independence")
    )
    statuses = Counter(case.status for case in execution.cases)
    return {
        "schema_version": "2.0.0",
        "suite_id": suite.suite_id,
        "suite_hash": suite.suite_hash,
        "split": suite.split,
        "public_development_suite": True,
        "execution_id": execution.execution_id,
        "implementation_hash": execution.implementation_hash,
        "git_head": execution.git_head,
        "git_dirty": execution.git_dirty,
        "coverage": {
            "target_cases": len(execution.target_case_ids),
            "assessment_cases": len(results),
            "status_counts": dict(sorted(statuses.items())),
            "companies_targeted": len(
                {suite_cases[identifier].company for identifier in execution.target_case_ids}
            ),
            "strata_targeted": sorted(
                {suite_cases[identifier].stratum for identifier in execution.target_case_ids}
            ),
        },
        "overall": summarize_quality_results(results),
        "by_stratum": {
            key: summarize_quality_results(value) for key, value in sorted(by_stratum.items())
        },
        "by_company": {
            key: summarize_quality_results(value) for key, value in sorted(by_company.items())
        },
        "assessor_independence_counts": dict(sorted(independence.items())),
        "execution_efficiency": {
            "estimated_cost_usd": execution.estimated_cost_usd,
            "cost_is_billing_truth": False,
            "new_runs_started": execution.new_runs_started,
        },
        "overall_score": None,
        "quality_claim_boundary": (
            "This is a public development/canary suite. Model-assessed semantics remain "
            "uncalibrated and cannot establish held-out product-quality superiority."
        ),
    }
