"""Aggregate V2 quality-result JSON files without inventing a composite score."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from researchforge.v2.quality import summarize_quality_results


def _assessment_payloads(inputs: list[Path], output: Path | None) -> list[dict[str, Any]]:
    output_resolved = output.resolve() if output is not None else None
    candidates: list[Path] = []
    for item in inputs:
        path = item.resolve()
        if path.is_dir():
            candidates.extend(sorted(path.rglob("*.json")))
        else:
            candidates.append(path)
    results: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or resolved == output_resolved:
            continue
        seen.add(resolved)
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if not {"case_id", "eligible", "metrics"} <= set(payload):
            continue
        results.append(payload)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = _assessment_payloads(args.inputs, args.output)
    summary = summarize_quality_results(results)
    payload = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(json.dumps({"output": str(output), "cases": len(results)}, ensure_ascii=False))
    else:
        print(payload)


if __name__ == "__main__":
    main()
