"""Command-line entry point for deterministic research and controlled evolution."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository
from researchforge.adapters.openai_responses import (
    OpenAIResponsesConclusionGenerator,
    ResponsesResource,
    luna_worst_case_cost,
)
from researchforge.api.app import PROJECT_ROOT, build_default_service
from researchforge.application.budget import BudgetLedger
from researchforge.application.calibration import (
    OpenAICalibrationRunner,
    calibration_artifact_passed,
)
from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.evolution import preregister_experiment
from researchforge.application.formal_experiment import FormalExperimentRunner
from researchforge.application.research import ConclusionGenerator
from researchforge.application.simulated_usability import SimulatedUsabilityRunner


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
    for name, help_text in (
        ("evolution-preflight", "validate the primary experiment without provider contact"),
        ("evolution-run", "run or resume the signed primary formal experiment"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument(
            "--experiment-id",
            default="experiment_primary_v1_4_001",
        )
        command.add_argument(
            "--package-root",
            type=Path,
            default=PROJECT_ROOT / "data" / "fixtures" / "v1.4-primary",
        )
        command.add_argument(
            "--private-ground-truth-root",
            type=Path,
            default=(
                PROJECT_ROOT / "data" / "private" / "benchmark" / "v1.4-primary" / "ground-truth"
            ),
        )
        command.add_argument(
            "--suite",
            type=Path,
            default=PROJECT_ROOT / "benchmark" / "suites" / "v1.4-primary-preregistered.json",
        )
    for name, help_text in (
        ("calibration-preflight", "validate model calibration without provider contact"),
        ("calibrate", "run or return the one pinned synthetic provider calibration"),
    ):
        subcommands.add_parser(name, help=help_text)
    for name, help_text in (
        ("usability-preflight", "validate simulated-usability evidence without provider contact"),
        ("usability-run", "run or resume exactly three labeled simulated usability sessions"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--batch-id", default="simulated_usability_v1_4_001")
        command.add_argument("--run-id", required=True)
        command.add_argument(
            "--research-screenshot",
            type=Path,
            default=PROJECT_ROOT / "docs" / "assets" / "research-page.png",
        )
        command.add_argument(
            "--skill-lab-screenshot",
            type=Path,
            default=PROJECT_ROOT / "docs" / "assets" / "skill-lab-page.png",
        )
    subcommands.add_parser("catalog", help="show the allowlisted fixture catalog")
    return parser


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _formal_runner(args: argparse.Namespace) -> FormalExperimentRunner:
    ledger = BudgetLedger(state_path=args.artifact_root / "budget" / "project-openai.json")
    rotated_key_ready = bool(os.getenv("OPENAI_API_KEY")) and (
        os.getenv("RESEARCHFORGE_ROTATED_KEY_CONFIRMED") == "1"
    )
    responses_resource: ResponsesResource | None = None

    def generator_factory(
        skill_content: str | None,
        ledger: BudgetLedger,
    ) -> ConclusionGenerator:
        nonlocal responses_resource
        from openai import OpenAI

        if responses_resource is None:
            responses_resource = cast(ResponsesResource, OpenAI().responses)
        return OpenAIResponsesConclusionGenerator(
            responses_resource,
            ledger,
            max_input_tokens=8000,
            max_output_tokens=4000,
            skill_content=skill_content,
        )

    seed_root = PROJECT_ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0"
    return FormalExperimentRunner(
        experiment_id=str(args.experiment_id),
        package_root=Path(args.package_root),
        private_ground_truth_root=Path(args.private_ground_truth_root),
        suite_path=Path(args.suite),
        seed_manifest_path=seed_root / "skill-version.json",
        seed_content_path=seed_root / "SKILL.md",
        artifact_root=Path(args.artifact_root),
        generator_factory=generator_factory,
        ledger=ledger,
        worst_case_request_cost=luna_worst_case_cost(8000, 4000),
        rotated_key_ready=rotated_key_ready,
        calibration_ready=calibration_artifact_passed(Path(args.artifact_root)),
    )


def _calibration_runner(args: argparse.Namespace) -> OpenAICalibrationRunner:
    ledger = BudgetLedger(state_path=args.artifact_root / "budget" / "project-openai.json")
    rotated_key_ready = bool(os.getenv("OPENAI_API_KEY")) and (
        os.getenv("RESEARCHFORGE_ROTATED_KEY_CONFIRMED") == "1"
    )

    def generator_factory(ledger: BudgetLedger) -> OpenAIResponsesConclusionGenerator:
        from openai import OpenAI

        responses = cast(ResponsesResource, OpenAI().responses)
        seed_content = (
            PROJECT_ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0" / "SKILL.md"
        ).read_text(encoding="utf-8")
        return OpenAIResponsesConclusionGenerator(
            responses,
            ledger,
            max_input_tokens=8000,
            max_output_tokens=4000,
            skill_content=seed_content,
        )

    return OpenAICalibrationRunner(
        artifact_root=Path(args.artifact_root),
        ledger=ledger,
        rotated_key_ready=rotated_key_ready,
        generator_factory=generator_factory if rotated_key_ready else None,
        worst_case_cost=luna_worst_case_cost(8000, 4000),
    )


def _simulated_usability_runner(args: argparse.Namespace) -> SimulatedUsabilityRunner:
    service = build_default_service(args.artifact_root)
    manifest = service.get_manifest(str(args.run_id))
    if manifest["lifecycle_state"] != "succeeded":
        raise ValueError("simulated usability requires a succeeded persisted run")
    run_bundle = {
        "manifest": manifest,
        "result": service.get_result(str(args.run_id)),
        "trace": service.get_trace(str(args.run_id)),
        "facts": service.get_facts(str(args.run_id)),
    }
    rotated_key_ready = bool(os.getenv("OPENAI_API_KEY")) and (
        os.getenv("RESEARCHFORGE_ROTATED_KEY_CONFIRMED") == "1"
    )

    def responses_factory() -> ResponsesResource:
        from openai import OpenAI

        return cast(ResponsesResource, OpenAI().responses)

    return SimulatedUsabilityRunner(
        batch_id=str(args.batch_id),
        run_bundle=run_bundle,
        screenshots={
            "research": Path(args.research_screenshot),
            "skill_lab": Path(args.skill_lab_screenshot),
        },
        artifact_root=Path(args.artifact_root),
        ledger=BudgetLedger(state_path=args.artifact_root / "budget" / "project-openai.json"),
        rotated_key_ready=rotated_key_ready,
        responses_factory=responses_factory if rotated_key_ready else None,
    )


def main(argv: list[str] | None = None) -> None:
    """Execute a run or inspect persisted artifacts without provider calls."""
    args = _parser().parse_args(argv)
    if args.command in {"calibration-preflight", "calibrate"}:
        calibration_runner = _calibration_runner(args)
        _print(
            calibration_runner.preflight()
            if args.command == "calibration-preflight"
            else calibration_runner.run()
        )
        return
    if args.command in {"evolution-preflight", "evolution-run"}:
        formal_runner = _formal_runner(args)
        _print(
            formal_runner.preflight()
            if args.command == "evolution-preflight"
            else formal_runner.run()
        )
        return
    if args.command in {"usability-preflight", "usability-run"}:
        simulation_runner = _simulated_usability_runner(args)
        _print(
            simulation_runner.preflight()
            if args.command == "usability-preflight"
            else simulation_runner.run()
        )
        return
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
