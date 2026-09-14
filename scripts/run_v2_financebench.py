"""Run one pinned FinanceBench public-development case through the real V2 product loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from researchforge.v2.benchmarks.financebench_runner import run_financebench_case

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ROOT = PROJECT_ROOT / "artifacts" / "v2-benchmarks" / "financebench"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("financebench_id")
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    args = parser.parse_args()
    summary = run_financebench_case(PROJECT_ROOT, args.benchmark_root, args.financebench_id)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
