"""Run/resume the canonical public-development FinanceBench suite with explicit cost bounds."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from researchforge.v2.benchmarks.financebench import FINANCEBENCH_COMMIT
from researchforge.v2.benchmarks.financebench_runner import run_financebench_case
from researchforge.v2.benchmarks.suite import (
    BenchmarkSuiteExecution,
    BenchmarkSuiteManifest,
    SuiteCaseExecution,
    execution_cost,
    implementation_fingerprint,
)
from researchforge.v2.storage import atomic_bytes

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "v2"
    / "benchmarks"
    / "financebench-public-development-10-v1.json"
)
DEFAULT_BENCHMARK_ROOT = PROJECT_ROOT / "artifacts" / "v2-benchmarks" / "financebench"


def _git_state() -> tuple[str | None, bool]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return head or None, bool(status.strip())


def _write(path: Path, execution: BenchmarkSuiteExecution) -> None:
    atomic_bytes(path, (execution.model_dump_json(indent=2) + "\n").encode())


def _load_suite(path: Path, benchmark_root: Path) -> BenchmarkSuiteManifest:
    suite = BenchmarkSuiteManifest.model_validate_json(path.read_text())
    if suite.benchmark_commit != FINANCEBENCH_COMMIT:
        raise RuntimeError("suite benchmark commit differs from the pinned runtime adapter")
    source = benchmark_root / "source" / "financebench_open_source.jsonl"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_hash != suite.source_questions_sha256:
        raise RuntimeError("suite source hash differs from the pinned local question corpus")
    return suite


def _targets(
    suite: BenchmarkSuiteManifest,
    *,
    case_ids: set[str],
    strata: set[str],
) -> list[SuiteCaseExecution]:
    selected = [
        case
        for case in suite.cases
        if (not case_ids or case.financebench_id in case_ids)
        and (not strata or case.stratum in strata)
    ]
    if not selected:
        raise ValueError("suite filters selected no cases")
    missing = case_ids - {case.financebench_id for case in selected}
    if missing:
        raise ValueError(f"unknown or filtered case IDs: {sorted(missing)}")
    return [
        SuiteCaseExecution(
            financebench_id=case.financebench_id,
            stratum=case.stratum,
            company=case.company,
        )
        for case in selected
    ]


def _new_execution(
    suite: BenchmarkSuiteManifest,
    cases: list[SuiteCaseExecution],
    *,
    max_new_runs: int,
    max_cost: float | None,
) -> BenchmarkSuiteExecution:
    implementation_hash = implementation_fingerprint(PROJECT_ROOT)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    execution_id = f"{suite.suite_id}-{stamp}-{implementation_hash[:10]}"
    head, dirty = _git_state()
    return BenchmarkSuiteExecution(
        execution_id=execution_id,
        suite_id=suite.suite_id,
        suite_hash=suite.suite_hash,
        implementation_hash=implementation_hash,
        git_head=head,
        git_dirty=dirty,
        started_at=datetime.now(UTC),
        max_new_runs=max_new_runs,
        max_estimated_cost_usd=max_cost,
        target_case_ids=[case.financebench_id for case in cases],
        cases=cases,
    )


def _resume_execution(
    path: Path,
    suite: BenchmarkSuiteManifest,
    *,
    max_new_runs: int,
    max_cost: float | None,
) -> BenchmarkSuiteExecution:
    execution = BenchmarkSuiteExecution.model_validate_json(path.read_text())
    if execution.suite_hash != suite.suite_hash or execution.suite_id != suite.suite_id:
        raise RuntimeError("resume execution belongs to a different benchmark suite")
    current_hash = implementation_fingerprint(PROJECT_ROOT)
    if current_hash != execution.implementation_hash:
        raise RuntimeError(
            "implementation fingerprint changed; start a new suite execution instead of resuming"
        )
    return execution.model_copy(
        update={
            "max_new_runs": max_new_runs,
            "max_estimated_cost_usd": max_cost,
            "finished_at": None,
            "stopped_reason": None,
        }
    )


def _result_update(case: SuiteCaseExecution, summary: dict[str, Any]) -> SuiteCaseExecution:
    usage: dict[str, Any] = summary["usage"] if isinstance(summary.get("usage"), dict) else {}
    trajectory: dict[str, Any] = (
        summary["trajectory"] if isinstance(summary.get("trajectory"), dict) else {}
    )
    lifecycle = str(summary.get("state") or "failed")
    return case.model_copy(
        update={
            "status": "succeeded" if lifecycle == "succeeded" else "failed",
            "run_id": str(summary.get("run_id")) if summary.get("run_id") else None,
            "lifecycle_state": lifecycle,
            "assessment_path": str(summary.get("quality_output"))
            if summary.get("quality_output")
            else None,
            "estimated_cost_usd": float(usage.get("estimated_cost", 0.0) or 0.0),
            "provider_calls": int(trajectory.get("provider_calls", 0) or 0),
            "total_tokens": int(trajectory.get("total_tokens", 0) or 0),
            "agent_turns": int(trajectory.get("agent_turns", 0) or 0),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--execution", type=Path, help="Resume an existing execution JSON")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--stratum", action="append", default=[])
    parser.add_argument("--max-new-runs", type=int, default=1)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=0.25)
    parser.add_argument("--continue-on-failure", action="store_true")
    args = parser.parse_args()
    if args.max_new_runs < 0 or args.max_estimated_cost_usd < 0:
        parser.error("run/cost bounds must be nonnegative")

    benchmark_root = args.benchmark_root.resolve()
    suite = _load_suite(args.suite.resolve(), benchmark_root)
    output_dir = benchmark_root / "suite-runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.execution:
        output_path = args.execution.resolve()
        execution = _resume_execution(
            output_path,
            suite,
            max_new_runs=args.max_new_runs,
            max_cost=args.max_estimated_cost_usd,
        )
    else:
        cases = _targets(suite, case_ids=set(args.case_id), strata=set(args.stratum))
        execution = _new_execution(
            suite,
            cases,
            max_new_runs=args.max_new_runs,
            max_cost=args.max_estimated_cost_usd,
        )
        output_path = output_dir / f"{execution.execution_id}.json"
        _write(output_path, execution)

    new_runs = 0
    cases = list(execution.cases)
    stopped_reason: str | None = None
    for index, case in enumerate(cases):
        if case.status in {"succeeded", "failed", "skipped"}:
            continue
        if new_runs >= args.max_new_runs:
            stopped_reason = "max_new_runs"
            break
        current_cost = execution_cost(execution.model_copy(update={"cases": cases}))
        if current_cost >= args.max_estimated_cost_usd:
            stopped_reason = "estimated_cost_cap"
            break
        try:
            summary = run_financebench_case(PROJECT_ROOT, benchmark_root, case.financebench_id)
            updated = _result_update(case, summary)
        except Exception as exc:
            updated = case.model_copy(
                update={
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc)[:800],
                }
            )
        cases[index] = updated
        new_runs += 1
        execution = execution.model_copy(
            update={
                "cases": cases,
                "new_runs_started": execution.new_runs_started + 1,
                "estimated_cost_usd": float(
                    execution_cost(execution.model_copy(update={"cases": cases}))
                ),
            }
        )
        _write(output_path, execution)
        if updated.status == "failed" and not args.continue_on_failure:
            stopped_reason = "case_failure"
            break

    pending = any(case.status == "pending" for case in cases)
    if stopped_reason is None:
        stopped_reason = "max_new_runs" if pending else "completed"
    execution = execution.model_copy(
        update={
            "cases": cases,
            "finished_at": datetime.now(UTC),
            "stopped_reason": stopped_reason,
            "estimated_cost_usd": float(
                execution_cost(execution.model_copy(update={"cases": cases}))
            ),
        }
    )
    _write(output_path, execution)
    print(
        json.dumps(
            {
                "execution": str(output_path),
                "execution_id": execution.execution_id,
                "suite_id": execution.suite_id,
                "suite_hash": execution.suite_hash,
                "implementation_hash": execution.implementation_hash,
                "stopped_reason": execution.stopped_reason,
                "new_runs_started_this_invocation": new_runs,
                "new_runs_started_total": execution.new_runs_started,
                "succeeded": sum(case.status == "succeeded" for case in cases),
                "failed": sum(case.status == "failed" for case in cases),
                "pending": sum(case.status == "pending" for case in cases),
                "estimated_cost_usd": execution.estimated_cost_usd,
                "cost_is_billing_truth": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
