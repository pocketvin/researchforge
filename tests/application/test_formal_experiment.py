"""Offline tests for formal experiment controls; never formal research evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
from decimal import Decimal
from pathlib import Path
from typing import Any

from researchforge.adapters.openai_responses import luna_worst_case_cost
from researchforge.application.budget import BudgetLedger
from researchforge.application.formal_experiment import (
    FormalExperimentRunner,
    formal_run_plan,
    preflight_primary_experiment,
)
from researchforge.application.research import ConclusionDraft, ConclusionGenerator
from tests.runtime_helpers import assert_v14_schema

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_PACKAGE = ROOT / "data" / "fixtures" / "v1.4-primary"
CONTINGENCY_PACKAGE = ROOT / "data" / "fixtures" / "v1.5-contingency"
SEED_ROOT = ROOT / "skills" / "fundamental-research" / "versions" / "1.0.0"
SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.4-primary-preregistered.json"
CONTINGENCY_SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.5-contingency-preregistered.json"
ALL_REPORTED_CHECKS = [
    "operating_cash_flow",
    "accounts_receivable",
    "inventory",
    "cash_conversion",
    "profit_cash_divergence",
    "one_off_contribution",
    "counter_evidence",
]


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()


def signed_test_package(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create private synthetic truth only inside pytest's temporary directory."""
    project_root = tmp_path / "project"
    package_root = project_root / "data" / "fixtures" / "v1.4-primary"
    private_root = project_root / "data" / "private" / "ground-truth"
    suite_path = project_root / "benchmark" / "suites" / SUITE_PATH.name
    shutil.copytree(PUBLIC_PACKAGE, package_root)
    shutil.copytree(
        CONTINGENCY_PACKAGE,
        project_root / "data" / "fixtures" / "v1.5-contingency",
    )
    suite_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SUITE_PATH, suite_path)
    shutil.copy2(CONTINGENCY_SUITE_PATH, suite_path.parent / CONTINGENCY_SUITE_PATH.name)
    facts = {
        fact["fact_id"]: fact
        for path in (package_root / "financial-facts").glob("*.json")
        for fact in (load_json(path),)
    }
    cases = {
        case["case_id"]: (path, case)
        for path in (package_root / "cases").glob("*.json")
        for case in (load_json(path),)
    }
    truth_hashes: dict[str, str] = {}
    for case_id, (_case_path, case) in cases.items():
        by_metric = {
            facts[fact_id]["metric_code"]: Decimal(facts[fact_id]["value"])
            for fact_id in case["allowed_financial_fact_ids"]
        }
        gross_profit = by_metric["revenue"] - by_metric["operating_cost"]
        truth = {
            "schema_version": "1.4.0",
            "ground_truth_id": f"ground_truth_{case_id}",
            "case_id": case_id,
            "access_class": "verifier_only",
            "expected_calculations": {
                "gross_profit": format(gross_profit, "f"),
                "gross_margin": format(gross_profit / by_metric["revenue"], "f"),
                "cash_conversion": format(
                    by_metric["operating_cash_flow"] / by_metric["net_income"], "f"
                ),
                "profit_cash_divergence": (
                    "1"
                    if by_metric["net_income"] > 0 and by_metric["operating_cash_flow"] < 0
                    else "0"
                ),
            },
        }
        truth_path = private_root / f"ground_truth_{case_id}.json"
        write_json(truth_path, truth)
        truth_hash = file_hash(truth_path)
        truth_hashes[case_id] = truth_hash
        case["verifier_ground_truth_ref"]["artifact_hash"] = truth_hash

    sources = {
        source["document_id"]: source
        for path in (package_root / "source-documents").glob("*.json")
        for source in (load_json(path),)
    }
    chunks = {
        chunk["chunk_id"]: chunk
        for path in (package_root / "evidence-chunks").glob("*.json")
        for chunk in (load_json(path),)
    }
    suite_hash = file_hash(suite_path)
    package_hash = canonical_hash(
        {
            **{f"source:{key}": canonical_hash(value) for key, value in sources.items()},
            **{f"fact:{key}": canonical_hash(value) for key, value in facts.items()},
            **{f"chunk:{key}": canonical_hash(value) for key, value in chunks.items()},
            **{f"ground_truth:{key}": value for key, value in truth_hashes.items()},
            "preregistered_suite": suite_hash,
        }
    )
    for case_path, case in cases.values():
        case["package_hash"] = package_hash
        write_json(case_path, case)

    manifest = load_json(package_root / "manifest.json")
    manifest["evidence_status"] = "SIGNED"
    manifest["formal_run_authorized"] = True
    manifest["owner_signoff"] = {
        "status": "signed",
        "signed_at": "2026-09-01T06:00:00+08:00",
        "evidence_file": "docs/evidence/g3-primary-data-signoff.md",
    }
    manifest["ground_truth_hashes"] = truth_hashes
    manifest["package_hash"] = package_hash
    manifest["preregistered_suite_hash"] = suite_hash
    artifact_paths = sorted(
        path
        for directory in ("source-documents", "financial-facts", "evidence-chunks", "cases")
        for path in (package_root / directory).glob("*.json")
    )
    manifest["public_artifact_hashes"] = {
        str(path.relative_to(project_root)): file_hash(path) for path in artifact_paths
    }
    write_json(package_root / "manifest.json", manifest)
    return package_root, private_root, suite_path


class SyntheticCoverageGenerator:
    """Deterministic test double that creates one repairable omission in Seed."""

    def __init__(self, skill_content: str | None) -> None:
        self.skill_content = skill_content

    def generate(self, context: dict[str, Any]) -> ConclusionDraft:
        if self.skill_content is None:
            reported = ["operating_cash_flow"]
        elif "## Candidate Reinforcement" in self.skill_content:
            reported = ALL_REPORTED_CHECKS
        else:
            reported = [code for code in ALL_REPORTED_CHECKS if code != "cash_conversion"]
        return ConclusionDraft.model_validate(
            {
                "executive_summary": "Synthetic offline experiment plumbing result.",
                "earnings_quality_text": "Synthetic coverage behavior for a test double.",
                "gross_margin_text": "Gross margin came from deterministic calculation.",
                "limitations": ["SYNTHETIC TEST DOUBLE; not formal evidence."],
                "reported_check_codes": reported,
            }
        )


def synthetic_generator_factory(
    skill_content: str | None,
    ledger: BudgetLedger,
) -> ConclusionGenerator:
    del ledger
    return SyntheticCoverageGenerator(skill_content)


def test_formal_plan_freezes_all_repeated_run_denominators() -> None:
    plan = formal_run_plan()

    assert plan["repeats_per_case_condition"] == 3
    assert plan["phases"]["evolution"]["run_count"] == 72
    assert plan["phases"]["validation"]["run_count"] == 36
    assert plan["phases"]["final_test"]["run_count"] == 36
    assert plan["maximum_formal_runs"] == 144
    assert plan["maximum_provider_requests_with_one_repair_per_run"] == 288


def test_unsigned_real_package_preflight_blocks_without_provider_contact(tmp_path: Path) -> None:
    report = preflight_primary_experiment(
        package_root=PUBLIC_PACKAGE,
        private_ground_truth_root=tmp_path / "unavailable-private-truth",
        seed_manifest_path=SEED_ROOT / "skill-version.json",
        seed_content_path=SEED_ROOT / "SKILL.md",
        ledger=BudgetLedger(state_path=tmp_path / "budget.json"),
        rotated_key_ready=False,
        calibration_ready=False,
        worst_case_request_cost=luna_worst_case_cost(8000, 4000),
    )

    assert report["status"] == "BLOCKED"
    assert report["provider_contacted"] is False
    assert "primary package owner signoff is not SIGNED" in report["blockers"]
    assert "rotated local OpenAI key is not confirmed ready" in report["blockers"]
    assert "pinned OpenAI calibration has not passed" in report["blockers"]
    assert report["budget"]["experiment_worst_case"] == "1.8432"


def test_primary_preflight_requires_the_sealed_contingency_commitment(tmp_path: Path) -> None:
    package_root, private_root, _suite_path = signed_test_package(tmp_path)
    (tmp_path / "project" / "data" / "fixtures" / "v1.5-contingency" / "manifest.json").unlink()

    report = preflight_primary_experiment(
        package_root=package_root,
        private_ground_truth_root=private_root,
        seed_manifest_path=SEED_ROOT / "skill-version.json",
        seed_content_path=SEED_ROOT / "SKILL.md",
        ledger=BudgetLedger(state_path=tmp_path / "budget.json"),
        rotated_key_ready=True,
        calibration_ready=True,
        worst_case_request_cost=luna_worst_case_cost(8000, 4000),
    )

    assert report["status"] == "BLOCKED"
    assert report["provider_contacted"] is False
    assert "sealed V1.5 contingency package or suite is missing" in report["blockers"]


def test_synthetic_full_runner_proves_controls_but_not_research_hypothesis(
    tmp_path: Path,
) -> None:
    package_root, private_root, suite_path = signed_test_package(tmp_path)
    runner = FormalExperimentRunner(
        experiment_id="experiment_synthetic_end_to_end",
        package_root=package_root,
        private_ground_truth_root=private_root,
        suite_path=suite_path,
        seed_manifest_path=SEED_ROOT / "skill-version.json",
        seed_content_path=SEED_ROOT / "SKILL.md",
        artifact_root=tmp_path / "artifacts",
        generator_factory=synthetic_generator_factory,
        ledger=BudgetLedger(state_path=tmp_path / "artifacts" / "budget.json"),
        worst_case_request_cost=luna_worst_case_cost(8000, 4000),
        rotated_key_ready=True,
        calibration_ready=True,
    )

    completed = runner.run()

    assert completed["outcome"] == "SUPPORTED"
    assert completed["final_test_consumed"] is True
    assert len(completed["run_ids"]) == 144
    assert len(completed["evaluation_ids"]) == 144
    assert completed["budget"]["spent"] == 0.0
    assert_v14_schema(completed, "evolution-experiment.schema.json")
    final_marker = runner.evolution_repository.get(
        "experiment_synthetic_end_to_end", "final-test-consumption"
    )
    assert final_marker["status"] == "UNSEALED_ONCE"
    assert_v14_schema(
        runner.evolution_repository.get("experiment_synthetic_end_to_end", "experience"),
        "experience.schema.json",
    )
    assert_v14_schema(
        runner.evolution_repository.get("experiment_synthetic_end_to_end", "patch"),
        "skill-patch.schema.json",
    )
    assert_v14_schema(
        runner.evolution_repository.get("experiment_synthetic_end_to_end", "candidate-skill"),
        "skill-version.schema.json",
    )
    candidate_run_id = next(
        run_id
        for run_id in completed["run_ids"]
        if runner.run_repository.get_manifest(run_id)["configuration"]["skill_version"].endswith(
            "-candidate.1"
        )
    )
    assert_v14_schema(
        runner.run_repository.get_manifest(candidate_run_id), "run-manifest.schema.json"
    )
    assert_v14_schema(
        runner.run_repository.get_result(candidate_run_id), "research-result.schema.json"
    )
    assert_v14_schema(
        runner.run_repository.get_trace(candidate_run_id), "workflow-trace.schema.json"
    )
    assert_v14_schema(
        runner.run_repository.get_evaluation(candidate_run_id),
        "evaluation-result.schema.json",
    )
