"""Command-line entry point for deterministic research and controlled evolution."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.api.app import PROJECT_ROOT, build_default_service
from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.evolution import preregister_experiment


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="researchforge")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path(os.getenv("RESEARCHFORGE_ARTIFACT_ROOT", PROJECT_ROOT / "artifacts")),
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    run = subcommands.add_parser("run", help="run one frozen filing-analysis case")
    run.add_argument(
        "--task-type",
        choices=[
            "company_research",
            "filing_analysis",
            "peer_comparison",
            "thesis_investigation",
            "risk_detection",
        ],
        default="filing_analysis",
    )
    run.add_argument("--company", action="append", required=True)
    run.add_argument("--period", action="append", required=True)
    run.add_argument("--question", required=True)
    run.add_argument("--research-time", required=True)
    run.add_argument("--idempotency-key", required=True)

    show = subcommands.add_parser("show", help="show a persisted run bundle")
    show.add_argument("run_id")
    verify = subcommands.add_parser("verify", help="verify a succeeded run")
    verify.add_argument("run_id")
    verify.add_argument("--case-id", required=True)
    verify.add_argument("--expected-calculations", required=True, type=Path)
    evolution = subcommands.add_parser(
        "evolution-preregister", help="freeze an isolated experiment grouping"
    )
    evolution.add_argument("--experiment-id", required=True)
    evolution.add_argument("--suite", required=True, type=Path)
    evolution_show = subcommands.add_parser(
        "evolution-show", help="show a controlled experiment artifact"
    )
    evolution_show.add_argument("experiment_id")
    evolution_show.add_argument("--kind", default="experiment")
    subcommands.add_parser("catalog", help="show the allowlisted fixture catalog")
    return parser


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> None:
    """Execute a run or inspect persisted artifacts without provider calls."""
    args = _parser().parse_args(argv)
    service = build_default_service(args.artifact_root)
    if args.command == "catalog":
        _print(service.fixture_catalog.catalog().model_dump(mode="json"))
        return
    if args.command == "evolution-preregister":
        suite = json.loads(args.suite.read_text(encoding="utf-8"))
        experiment = preregister_experiment(
            experiment_id=args.experiment_id,
            suite_id=str(suite["suite_id"]),
            split_cases=cast(dict[str, list[dict[str, str]]], suite["splits"]),
            seed_skill_version_id="skill_fundamental_1_0_0",
            timestamp=datetime.now().astimezone(),
        )
        EvolutionArtifactRepository(args.artifact_root).save(
            args.experiment_id, "experiment", experiment
        )
        _print(experiment)
        return
    if args.command == "evolution-show":
        _print(EvolutionArtifactRepository(args.artifact_root).get(args.experiment_id, args.kind))
        return
    if args.command == "show":
        manifest = service.get_manifest(args.run_id)
        bundle: dict[str, Any] = {"manifest": manifest}
        if manifest["artifacts"]["workflow_trace_id"] is not None:
            bundle["trace"] = service.get_trace(args.run_id)
        if manifest["artifacts"]["result_id"] is not None:
            bundle["result"] = service.get_result(args.run_id)
        if manifest["artifacts"]["evaluation_id"] is not None:
            bundle["evaluation"] = service.get_evaluation(args.run_id)
        _print(bundle)
        return
    if args.command == "verify":
        expected = json.loads(args.expected_calculations.read_text(encoding="utf-8"))
        if not isinstance(expected, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in expected.items()
        ):
            raise ValueError("expected calculations must be a JSON object of strings")
        _print(
            service.verify(
                args.run_id,
                case_id=args.case_id,
                expected_calculations=expected,
            )
        )
        return

    request = ResearchRunRequest(
        task_type=args.task_type,
        research_question=args.question,
        company_ids=args.company,
        requested_period_labels=args.period,
        research_time=datetime.fromisoformat(args.research_time),
        idempotency_key=args.idempotency_key,
    )
    submission = service.submit(request)
    manifest = service.execute(submission.run_id)
    bundle = {"submission": submission.model_dump(mode="json"), "manifest": manifest}
    if manifest["artifacts"]["workflow_trace_id"] is not None:
        bundle["trace"] = service.get_trace(submission.run_id)
    if manifest["artifacts"]["result_id"] is not None:
        bundle["result"] = service.get_result(submission.run_id)
    _print(bundle)


if __name__ == "__main__":
    main()
