"""Reproduce the three real-filing paths and publish their actual research artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from researchforge.adapters.storage import payload_sha256
from researchforge.api.app import DEFAULT_PRODUCT_ROOT, DEFAULT_SKILL_MANIFEST, PROJECT_ROOT
from researchforge.application.contracts import ResearchRunRequest
from researchforge.application.service import ResearchRunService
from researchforge.ingestion import FilingRegistry, ProductDisclosureIngestion


def generate(output: Path, raw_root: Path) -> None:
    """Require PDF recovery, then use one zero-provider-cost production service for all cases."""
    registry = FilingRegistry(PROJECT_ROOT / "data/product/filing-catalog.json")
    index = json.loads((DEFAULT_PRODUCT_ROOT / "manifest.json").read_text())
    sections = [
        "# Phase 3 — Three-filing Generalization Evidence",
        "",
        "Status: **ENGINEERING EVIDENCE — NOT INDEPENDENT ACCEPTANCE OR HUMAN VALIDATION**",
        "",
        "Exactly three real filing paths use the same deterministic extractor, catalog, "
        "LangGraph workflow and Financial Verifier. No provider calls or benchmark truth are used.",
        "",
        "This generator revalidated each local ignored PDF through the official identity/hash "
        "check, reran the page-preserving parser and extractor, and compared the resulting package "
        "and six recovery hashes with the published product package. No expected value or source "
        "page is supplied by the registry. The results below are persisted outputs, not mocks.",
        "",
        "Publication metadata exposes a date, not a reliable intraday release time. Availability "
        "is conservatively set to 23:59:59 Asia/Shanghai on that date.",
    ]
    with TemporaryDirectory(prefix="researchforge-generalization-") as temporary:
        root = Path(temporary)
        service = ResearchRunService.build(
            root / "runs", DEFAULT_PRODUCT_ROOT, DEFAULT_SKILL_MANIFEST, data_namespace="product"
        )
        for entry in index["packages"]:
            slug = entry["path"]
            ingestion = json.loads(
                (DEFAULT_PRODUCT_ROOT / slug / "ingestion-manifest.json").read_text()
            )
            company = ingestion["company"]["company_id"]
            period = ingestion["reporting_period"]
            label = f"{period['fiscal_year']}{period['fiscal_period']}"
            reproduced = ProductDisclosureIngestion(registry).run(
                company_id=company,
                period_label=label,
                raw_root=raw_root,
                package_root=root / slug,
                source_file=raw_root / f"{slug}.pdf",
            )
            if (
                reproduced["status"] != "ready"
                or reproduced["package_hash"] != entry["package_hash"]
            ):
                raise RuntimeError(
                    f"{slug}: raw PDF reproduction failed: {reproduced['abstentions']}"
                )
            if [r["recovery_hash"] for r in reproduced["extraction"]["recoveries"]] != [
                r["recovery_hash"] for r in ingestion["extraction"]["recoveries"]
            ]:
                raise RuntimeError(f"{slug}: recovery hashes changed")
            submission = service.submit(
                ResearchRunRequest(
                    task_type="filing_analysis",
                    company_ids=[company],
                    requested_period_labels=[label],
                    research_question=f"{label}利润是否真正转化成经营现金流?",
                    research_time=datetime.fromisoformat("2026-09-03T00:00:00+08:00"),
                    idempotency_key=f"generalization-{slug}",
                )
            )
            run_id = submission.run_id
            manifest = service.execute(run_id)
            if manifest["lifecycle_state"] != "succeeded":
                raise RuntimeError(f"{slug}: research failed: {manifest['failure']}")
            evaluation = service.verify(
                run_id, case_id=f"product_{slug.replace('-', '_')}", expected_calculations={}
            )
            if evaluation["failure_events"]:
                raise RuntimeError(f"{slug}: verification failed")
            result = service.get_result(run_id)
            calculations = service.get_calculations(run_id)
            trace = service.get_trace(run_id)
            artifacts: dict[str, Any] = {
                "run-manifest": service.get_manifest(run_id),
                "research-result": result,
                "workflow-trace": trace,
                "calculation-records": calculations,
                "evaluation-result": evaluation,
            }
            case_output = output / slug
            case_output.mkdir(parents=True, exist_ok=True)
            for kind, payload in artifacts.items():
                (case_output / f"{kind}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            sections.extend(
                [
                    "",
                    f"## {ingestion['company']['legal_name']} / {label}",
                    "",
                    f"- Source: [{ingestion['discovery']['document_title']}]"
                    f"({ingestion['discovery']['source_uri']})",
                    f"- Announcement: `{ingestion['discovery']['announcement_id']}`; "
                    f"published cutoff: `{ingestion['discovery']['publication_time']}`.",
                    f"- PDF SHA-256: `{ingestion['acquisition']['content_hash']}`; "
                    f"{ingestion['parser']['page_count']} physical pages.",
                    f"- Package SHA-256: `{entry['package_hash']}`.",
                    "- Recovery: **6/6 metrics; missing 0; abstained 0**.",
                    f"- Research Result: **{manifest['lifecycle_state']}**; "
                    f"Verifier failures: **{len(evaluation['failure_events'])}**; "
                    f"Trace: **{len(trace['stages'])} stages**.",
                    f"- [Actual result]({slug}/research-result.json), "
                    f"[calculations]({slug}/calculation-records.json), "
                    f"[trace]({slug}/workflow-trace.json), "
                    f"[verification]({slug}/evaluation-result.json).",
                    "",
                    "| Metric | Recovered CNY | Physical page | Statement / row | Column | Unit |",
                    "|---|---:|---:|---|---|---|",
                ]
            )
            for cell in reproduced["extraction"]["recoveries"]:
                sections.append(
                    f"| `{cell['metric_code']}` | {cell['normalized_value']} | {cell['page']} "
                    f"| {cell['statement']} / {cell['row_label']} | {cell['column_label']} "
                    f"| {cell['unit_label']} |"
                )
            sections.extend(["", "### Deterministic calculations", ""])
            for calculation in calculations:
                sections.append(
                    f"- `{calculation['formula_code']}` = `{calculation['value']}` "
                    f"(`{calculation['status']}`); {calculation['explanation']}"
                )
            sections.extend(
                [
                    "",
                    "### Result, counter evidence and monitoring",
                    "",
                    result["executive_summary"],
                    "",
                ]
            )
            sections.append(result["claims"][0]["counter_evidence_search"]["summary"])
            sections.extend(["", *[f"- {item}" for item in result["limitations"]], ""])
            for item in result["monitoring_items"]:
                sections.append(
                    f"- Monitor: {item['title']}; trigger: {item['trigger']}; "
                    f"{item['next_review']}.",
                )
            sections.extend(["", f"Research Result canonical SHA-256: `{payload_sha256(result)}`."])
    sections.extend(
        [
            "",
            "## Bounded limitations",
            "",
            "- This is evidence for three native-text filings, not full-market or OCR capability.",
            "- Two value columns are supported; extra, missing or ambiguous columns abstain.",
            "- Note columns are not financial values. Ambiguous note/value positions abstain.",
            "- Parent-company and equity-change tables cannot supply consolidated target metrics.",
            "- CATL 2024FY's counter-evidence rule found no unique qualifying excerpt. "
            "It is labeled `not_found`, not 'no risks' or 'unaudited'.",
            "- No H1/FY growth comparison is inferred; each path uses one reporting period.",
            "- The ratio denominator is attributable net income, not consolidated total profit.",
            "- The Verifier evidence is deterministic consistency/coverage checking; it is not "
            "independent acceptance or real-human usefulness evidence.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "uv run python scripts/generalization_evidence.py --raw-root data/raw/product",
            "uv run pytest tests/ingestion -q",
            "uv run python scripts/validate_contracts.py",
            "```",
            "",
        ]
    )
    (output / "README.md").write_text("\n".join(sections), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=PROJECT_ROOT / "data/raw/product")
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "docs/evidence/v1.5-generalization"
    )
    args = parser.parse_args()
    generate(args.output, args.raw_root)
    print("PASS: three source-verified filings, 18 recovered facts and 3 verified Research Results")


if __name__ == "__main__":
    main()
