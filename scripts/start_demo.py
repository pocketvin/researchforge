"""Start the Web + API + PostgreSQL + n8n product demo with auto reasoning."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose"]
N8N_COMPOSE = [
    *COMPOSE,
    "-f",
    "docker-compose.yml",
    "-f",
    "integrations/n8n/compose.yml",
    "--profile",
    "n8n",
]


def build_commands(*, build: bool, smoke: bool) -> list[list[str]]:
    base_up = [*COMPOSE, "up", "-d"]
    if build:
        base_up.append("--build")
    base_up.append("--wait")
    commands = [
        base_up,
        [*N8N_COMPOSE, "stop", "n8n"],
        [
            *N8N_COMPOSE,
            "run",
            "--rm",
            "--no-deps",
            "n8n",
            "import:workflow",
            "--input=/files/researchforge-v1.7.workflow.json",
        ],
        [
            *N8N_COMPOSE,
            "run",
            "--rm",
            "--no-deps",
            "n8n",
            "publish:workflow",
            "--id=researchforgeV17",
        ],
        [*N8N_COMPOSE, "up", "-d", "--no-deps", "--wait", "n8n"],
    ]
    if smoke:
        commands.extend(
            [
                [sys.executable, "scripts/docker_smoke.py"],
                [sys.executable, "-m", "scripts.n8n_smoke"],
            ]
        )
    return commands


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-build", action="store_true", help="Reuse existing local images.")
    parser.add_argument("--skip-smoke", action="store_true", help="Start without runtime checks.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without running them."
    )
    args = parser.parse_args()
    commands = build_commands(build=not args.no_build, smoke=not args.skip_smoke)
    environment = os.environ.copy()
    environment.setdefault("RESEARCHFORGE_REASONING_MODE", "auto")
    for command in commands:
        print(shlex.join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=ROOT, env=environment, check=True)
    if not args.dry_run:
        print("Web: http://127.0.0.1:4173/", flush=True)
        print("n8n form: http://127.0.0.1:5678/form/researchforge-v17-form", flush=True)


if __name__ == "__main__":
    main()
