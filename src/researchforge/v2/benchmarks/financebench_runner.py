"""Execute one public FinanceBench development case through the real V2 product runtime."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from researchforge.adapters.storage import payload_sha256
from researchforge.v2.benchmarks.financebench import (
    FINANCEBENCH_PUBLISHED_AT,
    ensure_pdf,
    load_case,
    load_or_build_environment,
    make_quality_case,
    period_label,
)
from researchforge.v2.contracts import ResearchRequest
from researchforge.v2.quality import evaluate_quality
from researchforge.v2.runtime import build_service
from researchforge.v2.storage import atomic_bytes


def _observations(state: dict[str, Any], source_hashes: dict[str, str]) -> list[dict[str, Any]]:
    raw = state.get("observed", state.get("observed_evidence", {}))
    values = list(raw.values()) if isinstance(raw, dict) else list(raw)
    return [
        {**item, "document_hash": source_hashes.get(str(item.get("document_id")))}
        for item in values
        if isinstance(item, dict)
    ]


def run_financebench_case(
    project_root: Path,
    benchmark_root: Path,
    financebench_id: str,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    benchmark_root = benchmark_root.resolve()
    source_root = benchmark_root / "source"
    runtime_base = benchmark_root / "runtime"
    output_root = benchmark_root / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)

    question, document = load_case(source_root, financebench_id)
    pdf_path = ensure_pdf(source_root, str(document["doc_name"]))
    service = build_service(project_root, runtime_base)
    environment = load_or_build_environment(
        service.repository, document=document, pdf_payload=pdf_path.read_bytes()
    )
    research_time = FINANCEBENCH_PUBLISHED_AT
    quality_case = make_quality_case(
        question=question,
        document=document,
        environment=environment,
        research_time=research_time,
    )
    case_path = source_root / "cases" / f"{financebench_id}.json"
    atomic_bytes(
        case_path,
        (
            json.dumps(quality_case.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        ).encode(),
    )

    # The runtime receives only question + source environment. Gold labels stay in quality_case.
    service.prepare = lambda _request, _run_id, _check: environment
    request = ResearchRequest(
        company_query=str(document["company"]),
        market_hint="US",
        requested_period_label=period_label(document),
        research_question=str(question["question"]),
        research_time=datetime.fromisoformat(research_time),
        idempotency_key=f"financebench-{financebench_id}-{uuid.uuid4().hex}",
    )
    manifest, _created = service.submit(request)
    run_id = str(manifest["run_id"])
    final = service.execute(run_id)

    result: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    if final["lifecycle_state"] == "succeeded":
        result = service.repository.artifact(run_id, "result")
        report = result.get("report") if isinstance(result.get("report"), dict) else None
    state = service.repository.artifact(run_id, "research_state")
    source_hashes = {
        str(item["document_id"]): str(item["content_hash"])
        for item in environment["documents"].values()
    }
    eval_environment = {
        **environment,
        "company": environment["entity"],
        "corpus_hash": quality_case.corpus_hash,
    }
    report_hash = payload_sha256(report) if report is not None else None
    assessment = evaluate_quality(
        quality_case,
        run=final,
        environment=eval_environment,
        observed_evidence=_observations(state, source_hashes),
        report_hash=report_hash,
        report=report,
        events=service.repository.events(run_id),
    )
    assessment["report_hash"] = report_hash
    assessment["external_benchmark"] = {
        "name": "FinanceBench open-source",
        "financebench_id": financebench_id,
        "public_development_sample": True,
        "public_validation_sample": False,
        "gold_answer_loaded_after_product_run": True,
        "gold_labels_in_runtime": False,
    }
    output = output_root / f"{run_id}-{financebench_id}.json"
    atomic_bytes(output, (json.dumps(assessment, ensure_ascii=False, indent=2) + "\n").encode())

    metrics = assessment.get("metrics", {})
    trajectory = assessment.get("trajectory", {})
    summary: dict[str, Any] = {
        "run_id": run_id,
        "state": final["lifecycle_state"],
        "financebench_id": financebench_id,
        "question": question["question"],
        "report_title": report.get("title") if report else None,
        "executive_summary": report.get("executive_summary") if report else None,
        "evidence_observation_recall": metrics.get("required_evidence_observation_recall", {}).get(
            "value"
        ),
        "reference_scalar_presence": metrics.get("reference_answer_scalar_presence", {}).get(
            "value"
        ),
        "answer_correctness": metrics.get("answer_correctness", {}).get("value"),
        "trajectory": trajectory,
        "usage": final.get("usage"),
        "quality_output": str(output),
        "case_path": str(case_path),
    }
    return summary
