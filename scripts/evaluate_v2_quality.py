"""Evaluate a frozen V2 run using a separately reviewed reference case.

No model calls are made. This entry point is separate from product execution so
reference labels cannot leak into the research agent's prompt or tools.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.quality import QualityCase, SemanticAnnotations, evaluate_quality
from researchforge.v2.storage import ResearchRepository, atomic_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = ResearchRepository(args.artifact_root.resolve())
    run = repository.get(args.run_id)
    environment = repository.artifact(args.run_id, "environment")
    if not isinstance(environment, dict):
        raise SystemExit("The run does not yet have a persisted filing environment.")
    case = QualityCase.model_validate_json(args.case.read_text(encoding="utf-8"))
    raw_documents = environment.get("documents", {})
    documents = (
        list(raw_documents.values()) if isinstance(raw_documents, dict) else list(raw_documents)
    )
    source_hashes = {
        str(document["document_id"]): str(document["content_hash"]) for document in documents
    }
    # Identity is based on actual persisted source hashes, never the case's own value.
    corpus_hash = payload_sha256(sorted(source_hashes.values()))
    enriched_environment: dict[str, Any] = {
        **environment,
        "corpus_hash": corpus_hash,
        "company": environment.get("company")
        or environment.get("entity")
        or (documents[0].get("company", {}) if documents else {}),
    }

    def optional_artifact(kind: str) -> dict[str, Any] | None:
        try:
            value = repository.artifact(args.run_id, kind)
            return cast(dict[str, Any], value) if isinstance(value, dict) else None
        except KeyError:
            return None

    working = optional_artifact("research_state") or {}
    raw_observed = working.get("observed_evidence", working.get("observed", {}))
    observed = list(raw_observed.values()) if isinstance(raw_observed, dict) else raw_observed
    observations = [
        {**item, "document_hash": source_hashes.get(str(item.get("document_id")))}
        for item in observed
    ]
    result = optional_artifact("result")
    report = (
        result.get("report")
        if isinstance(result, dict) and isinstance(result.get("report"), dict)
        else None
    )
    report_hash = payload_sha256(report) if report is not None else None
    annotations = (
        SemanticAnnotations.model_validate_json(args.annotations.read_text(encoding="utf-8"))
        if args.annotations is not None
        else None
    )
    assessment = evaluate_quality(
        case,
        run=run,
        environment=enriched_environment,
        observed_evidence=observations,
        report_hash=report_hash,
        report=report,
        events=repository.events(args.run_id),
        annotations=annotations,
    )
    assessment["report_hash"] = report_hash
    output = args.output.resolve()
    atomic_bytes(output, json.dumps(assessment, ensure_ascii=False, indent=2).encode("utf-8"))
    print(
        json.dumps(
            {
                "output": str(output),
                "eligible": assessment["eligible"],
                "suitable_for_product_quality_claim": assessment.get(
                    "suitable_for_product_quality_claim", False
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
