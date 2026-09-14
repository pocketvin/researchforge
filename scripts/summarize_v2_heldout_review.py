"""Validate choice-only held-out judgments and summarize blind owner acceptance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from researchforge.v2.benchmarks.heldout import HeldOutAcceptanceAttempt, HeldOutSuiteSeal
from researchforge.v2.benchmarks.human_review import (
    CandidateResultRef,
    HumanJudgmentFile,
    summarize_human_acceptance,
)
from researchforge.v2.storage import atomic_bytes


def _complete_attempt(
    ledger: Path,
    seal: HeldOutSuiteSeal,
    judgments: HumanJudgmentFile,
) -> str:
    attempts = [
        HeldOutAcceptanceAttempt.model_validate_json(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matching = [item for item in attempts if item.bundle_hash == seal.bundle_hash]
    if not matching:
        raise ValueError("held-out attempt ledger has no attempt for this seal")
    latest = max(matching, key=lambda item: item.started_at)
    if latest.state not in {"running", "completed"}:
        raise ValueError("held-out attempt is not eligible for human-review completion")
    first_choice = min(item.reviewed_at for item in judgments.judgments)
    last_choice = max(item.reviewed_at for item in judgments.judgments)
    updated = latest.model_copy(
        update={
            "state": "completed",
            "results_opened_at": latest.results_opened_at or first_choice,
            "human_review_completed_at": last_choice,
        }
    )
    attempts = [updated if item.attempt_id == latest.attempt_id else item for item in attempts]
    atomic_bytes(
        ledger,
        "".join(item.model_dump_json() + "\n" for item in attempts).encode("utf-8"),
    )
    return updated.attempt_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seal", type=Path)
    parser.add_argument("judgments", type=Path)
    parser.add_argument("candidate_results", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--attempt-ledger", type=Path)
    args = parser.parse_args()
    seal = HeldOutSuiteSeal.model_validate_json(args.seal.resolve().read_text())
    judgment_file = HumanJudgmentFile.model_validate_json(args.judgments.resolve().read_text())
    refs = [
        CandidateResultRef.model_validate_json(line)
        for line in args.candidate_results.resolve().read_text().splitlines()
        if line.strip()
    ]
    summary = summarize_human_acceptance(seal, judgment_file, refs)
    payload = summary.model_dump(mode="json")
    if args.attempt_ledger:
        payload["acceptance_attempt_id"] = _complete_attempt(
            args.attempt_ledger.resolve(), seal, judgment_file
        )
        payload["acceptance_attempt_state"] = "completed"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
