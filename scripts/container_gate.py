"""Run the deterministic packaged container gate without mutating the Owner stack."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "researchforge-gate"
COMPOSE = ["docker", "compose", "-p", PROJECT]


def main() -> None:
    env = os.environ.copy()
    env.update(
        {
            "RESEARCHFORGE_REASONING_MODE": "deterministic",
            "RESEARCHFORGE_API_PORT": "18000",
            "RESEARCHFORGE_WEB_PORT": "14173",
        }
    )
    try:
        subprocess.run([*COMPOSE, "up", "-d", "--build", "--wait"], cwd=ROOT, env=env, check=True)
        subprocess.run(
            [sys.executable, "scripts/docker_smoke.py", "--base-url", "http://127.0.0.1:14173"],
            cwd=ROOT,
            env=env,
            check=True,
        )
    finally:
        subprocess.run(
            [*COMPOSE, "down", "--volumes", "--remove-orphans"], cwd=ROOT, env=env, check=False
        )


if __name__ == "__main__":
    main()
