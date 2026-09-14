"""Create the canonical public-development FinanceBench suite without reading gold labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

from researchforge.v2.benchmarks.financebench import FINANCEBENCH_COMMIT, FINANCEBENCH_LICENSE
from researchforge.v2.benchmarks.suite import BenchmarkSuiteManifest, finalize_suite

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    PROJECT_ROOT
    / "artifacts"
    / "v2-benchmarks"
    / "financebench"
    / "source"
    / "financebench_open_source.jsonl"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "v2"
    / "benchmarks"
    / "financebench-public-development-10-v1.json"
)
SUITE_ID = "financebench-public-development-10-v1"
SELECTOR_VERSION = "1.1.0"
ANCHORS = ["financebench_id_03029", "financebench_id_07966", "financebench_id_00499"]
SEED = 20260911

Stratum = tuple[str, Callable[[dict[str, Any]], bool]]
STRATA: list[Stratum] = [
    (
        "extraction_metrics",
        lambda row: (
            row.get("question_reasoning") == "Information extraction"
            and row.get("question_type") == "metrics-generated"
        ),
    ),
    (
        "extraction_domain",
        lambda row: (
            row.get("question_reasoning") == "Information extraction"
            and row.get("question_type") == "domain-relevant"
        ),
    ),
    (
        "numerical_metrics",
        lambda row: (
            row.get("question_reasoning") == "Numerical reasoning"
            and row.get("question_type") == "metrics-generated"
        ),
    ),
    (
        "logical_numeric",
        lambda row: (
            row.get("question_reasoning") == "Logical reasoning (based on numerical reasoning)"
            and row.get("question_type") == "domain-relevant"
        ),
    ),
    (
        "num_or_logical",
        lambda row: (
            row.get("question_reasoning") == "Numerical reasoning OR Logical reasoning"
            and row.get("question_type") == "domain-relevant"
        ),
    ),
    (
        "margin_driver",
        lambda row: (
            str(row.get("question_reasoning") or "").startswith(
                "Logical reasoning (based on numerical reasoning) OR Numerical reasoning"
            )
            and row.get("question_type") == "domain-relevant"
        ),
    ),
    (
        "novel_10k",
        lambda row: (
            row.get("question_reasoning") is None and row.get("question_type") == "novel-generated"
        ),
    ),
]


def _load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _case(row: dict[str, Any], stratum: str) -> dict[str, Any]:
    # Deliberately whitelist selection metadata. Gold answer/justification/evidence never enter
    # the suite manifest and therefore cannot influence normal product execution.
    return {
        "financebench_id": str(row["financebench_id"]),
        "stratum": stratum,
        "company": str(row["company"]),
        "doc_name": str(row["doc_name"]),
        "question_type": str(row["question_type"]),
        "question_reasoning": (
            str(row["question_reasoning"]) if row.get("question_reasoning") is not None else None
        ),
        "question": str(row["question"]),
    }


def select(rows: list[dict[str, Any]], *, source_sha256: str) -> BenchmarkSuiteManifest:
    by_id = {str(row["financebench_id"]): row for row in rows}
    if not set(ANCHORS) <= set(by_id):
        raise RuntimeError("canonical FinanceBench anchors are missing from the pinned source")
    selected = [by_id[item] for item in ANCHORS]
    used_companies = {str(row["company"]) for row in selected}
    selected_ids = set(ANCHORS)
    rng = random.Random(SEED)
    selections = [_case(row, "anchor") for row in selected]
    for name, predicate in STRATA:
        candidates = [
            row
            for row in rows
            if predicate(row)
            and str(row["financebench_id"]) not in selected_ids
            and str(row["doc_name"]).endswith("_10K")
        ]
        diverse = [row for row in candidates if str(row["company"]) not in used_companies]
        pool = sorted(diverse or candidates, key=lambda row: str(row["financebench_id"]))
        if not pool:
            raise RuntimeError(f"no eligible FinanceBench row for stratum {name}")
        choice = rng.choice(pool)
        selected_ids.add(str(choice["financebench_id"]))
        used_companies.add(str(choice["company"]))
        selections.append(_case(choice, name))
    return finalize_suite(
        {
            "schema_version": "2.0.0",
            "suite_id": SUITE_ID,
            "benchmark_name": "FinanceBench open-source",
            "benchmark_commit": FINANCEBENCH_COMMIT,
            "benchmark_license": FINANCEBENCH_LICENSE,
            "split": "development",
            "selector_version": SELECTOR_VERSION,
            "seed": SEED,
            "source_questions_sha256": source_sha256,
            "source_question_count": len(rows),
            "scope": (
                "Public 10-K development/canary suite. Selection uses question/company/document/"
                "reasoning metadata only; gold answer, justification and evidence are excluded."
            ),
            "gold_fields_used_in_selection": False,
            "anchors": ANCHORS,
            "cases": selections,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = args.source.resolve()
    payload = source.read_bytes()
    suite = select(_load(source), source_sha256=hashlib.sha256(payload).hexdigest())
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(suite.model_dump_json(indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "suite_id": suite.suite_id,
                "suite_hash": suite.suite_hash,
                "cases": len(suite.cases),
                "companies": len({case.company for case in suite.cases}),
                "split": suite.split,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
