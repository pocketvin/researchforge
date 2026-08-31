"""Run the fixed G1 batch without provider calls."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from researchforge.api.app import DEFAULT_FIXTURE_ROOT, DEFAULT_SKILL_MANIFEST
from researchforge.application.reliability import run_reliability_batch
from researchforge.application.service import ResearchRunService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    if args.artifact_root is not None:
        service = ResearchRunService.build(
            args.artifact_root, DEFAULT_FIXTURE_ROOT, DEFAULT_SKILL_MANIFEST
        )
        print(json.dumps(run_reliability_batch(service), ensure_ascii=False, indent=2))
        return
    with tempfile.TemporaryDirectory(prefix="researchforge-reliability-") as directory:
        service = ResearchRunService.build(
            Path(directory), DEFAULT_FIXTURE_ROOT, DEFAULT_SKILL_MANIFEST
        )
        print(json.dumps(run_reliability_batch(service), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
