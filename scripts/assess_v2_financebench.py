"""Post-run semantic assessment for one isolated FinanceBench V2 run.

Gold labels are loaded only after the product run has finished. The output remains explicitly
uncalibrated and is not suitable for a product-quality claim until human calibration exists.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from researchforge.adapters.storage import payload_sha256
from researchforge.config import load_runtime_settings
from researchforge.v2.benchmarks.semantic_assessor import (
    assess_with_kimi,
    assess_with_qwen_max,
    assessor_independence_label,
)
from researchforge.v2.quality import QualityCase, evaluate_quality
from researchforge.v2.storage import ResearchRepository, atomic_bytes

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "artifacts" / "v2-benchmarks" / "financebench"


def _observations(state: dict[str, Any], environment: dict[str, Any]) -> list[dict[str, Any]]:
    hashes = {
        str(item["document_id"]): str(item["content_hash"])
        for item in environment.get("documents", {}).values()
    }
    raw = state.get("observed", state.get("observed_evidence", {}))
    values = list(raw.values()) if isinstance(raw, dict) else list(raw)
    return [
        {**item, "document_hash": hashes.get(str(item.get("document_id")))}
        for item in values
        if isinstance(item, dict)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("financebench_id")
    parser.add_argument("run_id")
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--assessor-provider",
        choices=("qwen-max", "kimi"),
        default="qwen-max",
        help="Uncalibrated semantic judge. Product runtime never receives benchmark gold labels.",
    )
    parser.add_argument("--assessor-model")
    args = parser.parse_args()

    root = args.benchmark_root.resolve()
    repository = ResearchRepository(root / "runtime" / "v2")
    manifest = repository.get(args.run_id)
    if manifest["lifecycle_state"] != "succeeded":
        raise RuntimeError("semantic assessment requires a succeeded product run")
    result = repository.artifact(args.run_id, "result")
    environment = repository.artifact(args.run_id, "environment")
    state = repository.artifact(args.run_id, "research_state")
    report = result["report"]
    report_hash = payload_sha256(report)
    case_path = root / "source" / "cases" / f"{args.financebench_id}.json"
    case = QualityCase.model_validate_json(case_path.read_text(encoding="utf-8"))
    observed = _observations(state, environment)
    events = repository.events(args.run_id)
    eval_environment = {
        **environment,
        "company": environment["entity"],
        "corpus_hash": case.corpus_hash,
    }
    preliminary = evaluate_quality(
        case,
        run=manifest,
        environment=eval_environment,
        observed_evidence=observed,
        report_hash=report_hash,
        report=report,
        events=events,
    )
    if not preliminary["eligible"]:
        raise RuntimeError(f"run is not eligible for this frozen case: {preliminary['errors']}")

    settings = load_runtime_settings(PROJECT_ROOT)
    if args.assessor_provider == "qwen-max":
        if settings.researchforge_qwen_api_key is None or not settings.researchforge_qwen_base_url:
            raise RuntimeError("Qwen benchmark assessor is not configured")
        assessor_model = args.assessor_model or "qwen3-max"
        independence, product_model_roles = assessor_independence_label(
            manifest, assessor_provider="qwen", assessor_model=assessor_model
        )
        annotations, assessor_metadata = assess_with_qwen_max(
            case,
            report_hash=report_hash,
            report=report,
            observed_evidence=observed,
            trajectory=preliminary["trajectory"],
            api_key=settings.researchforge_qwen_api_key.get_secret_value(),
            base_url=settings.researchforge_qwen_base_url,
            model=assessor_model,
            independence=independence,
        )
        assessor_metadata["product_model_roles"] = product_model_roles
    else:
        if settings.researchforge_kimi_api_key is None or not settings.researchforge_kimi_base_url:
            raise RuntimeError("Kimi benchmark assessor is not configured")
        assessor_model = args.assessor_model or settings.researchforge_kimi_model
        independence, product_model_roles = assessor_independence_label(
            manifest, assessor_provider="kimi", assessor_model=assessor_model
        )
        annotations, assessor_metadata = assess_with_kimi(
            case,
            report_hash=report_hash,
            report=report,
            observed_evidence=observed,
            trajectory=preliminary["trajectory"],
            api_key=settings.researchforge_kimi_api_key.get_secret_value(),
            base_url=settings.researchforge_kimi_base_url,
            model=assessor_model,
            independence=independence,
        )
        assessor_metadata["product_model_roles"] = product_model_roles
    final = evaluate_quality(
        case,
        run=manifest,
        environment=eval_environment,
        observed_evidence=observed,
        report_hash=report_hash,
        report=report,
        events=events,
        annotations=annotations,
    )
    final["benchmark_assessor"] = assessor_metadata
    final["assessment_boundary"] = (
        f"{assessor_metadata['provider']} / {assessor_metadata['model']} semantic assessment is "
        "uncalibrated model judgment, not ground truth. It cannot make this public validation "
        "case product-claim suitable."
    )
    output_dir = root / "outputs"
    annotations_path = output_dir / f"{args.run_id}-{args.financebench_id}-annotations.json"
    assessment_path = output_dir / f"{args.run_id}-{args.financebench_id}-assessed.json"
    atomic_bytes(
        annotations_path,
        json.dumps(annotations.model_dump(mode="json"), ensure_ascii=False, indent=2).encode(),
    )
    atomic_bytes(assessment_path, json.dumps(final, ensure_ascii=False, indent=2).encode())
    metrics = final["metrics"]
    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "case_id": final["case_id"],
                "assessor": assessor_metadata,
                "answer_correctness": metrics["answer_correctness"],
                "reference_finding_coverage": metrics["reference_finding_coverage"],
                "citation_support": metrics["citation_support"],
                "citation_completeness": metrics["citation_completeness"],
                "stop_quality": metrics["stop_quality"],
                "product_claim_suitable": final["suitable_for_product_quality_claim"],
                "assessment": str(assessment_path),
                "annotations": str(annotations_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
