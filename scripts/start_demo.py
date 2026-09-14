"""Start the canonical ResearchForge V2 Web + API + n8n product stack."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import urllib.request
from pathlib import Path

from researchforge.config import load_runtime_settings

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
    base_up = [*COMPOSE, "up", "-d", "--force-recreate", "--remove-orphans"]
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
            "--input=/files/researchforge-v2.workflow.json",
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


def verify_runtime(expected_reasoning_mode: str) -> None:
    """Verify the effective non-secret V2 provider routing in the running container."""
    settings = load_runtime_settings(ROOT)
    expected_provider = settings.researchforge_provider
    expected_model = {
        "hybrid": settings.researchforge_deepseek_model,
        "qwen": settings.researchforge_qwen_model,
        "openai": settings.researchforge_model,
    }[expected_provider]
    with urllib.request.urlopen("http://127.0.0.1:8000/v2/capabilities", timeout=10.0) as response:
        v2 = json.load(response)
    if v2.get("provider") != expected_provider:
        raise RuntimeError(
            f"V2 provider mismatch: expected {expected_provider}, got {v2.get('provider')}"
        )
    if v2.get("model") != expected_model:
        raise RuntimeError(f"V2 model mismatch: expected {expected_model}, got {v2.get('model')}")
    expected_agent_ready = expected_reasoning_mode != "deterministic"
    if bool(v2.get("agent_ready")) != expected_agent_ready:
        raise RuntimeError(
            "V2 agent readiness mismatch: "
            f"expected {expected_agent_ready}, got {v2.get('agent_ready')}"
        )
    if expected_provider == "hybrid":
        expected_roles = {
            "reflection_model": settings.researchforge_deepseek_model,
            "synthesis_model": settings.researchforge_deepseek_model,
            "semantic_review_model": settings.researchforge_qwen_review_model,
            "research_fallback_model": settings.researchforge_qwen_model,
            "fallback_reflection_model": settings.researchforge_qwen_fallback_synthesis_model,
            "fallback_synthesis_model": settings.researchforge_qwen_fallback_synthesis_model,
            "fallback_semantic_review_model": settings.researchforge_deepseek_model,
            "vision_model": settings.researchforge_qwen_vision_model,
        }
        mismatches = {
            key: {"expected": value, "actual": v2.get(key)}
            for key, value in expected_roles.items()
            if v2.get(key) != value
        }
        if mismatches:
            raise RuntimeError(f"V2 hybrid role routing mismatch: {mismatches}")
    print(
        f"Runtime: v2={v2.get('provider')}/{v2.get('model')} · agent_ready={v2.get('agent_ready')}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-build", action="store_true", help="Reuse existing local images.")
    parser.add_argument("--skip-smoke", action="store_true", help="Start without runtime checks.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without running them."
    )
    parser.add_argument(
        "--reasoning-mode",
        choices=("auto", "openai", "deterministic"),
        default="auto",
        help="V2 reasoning mode; deterministic is reserved for explicit test runs.",
    )
    args = parser.parse_args()
    commands = build_commands(build=not args.no_build, smoke=not args.skip_smoke)
    environment = os.environ.copy()
    environment["RESEARCHFORGE_REASONING_MODE"] = args.reasoning_mode
    for index, command in enumerate(commands):
        print(shlex.join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, cwd=ROOT, env=environment, check=True)
            if index == 0:
                verify_runtime(args.reasoning_mode)
    if not args.dry_run:
        print("Web: http://127.0.0.1:4173/", flush=True)
        print("n8n form: http://127.0.0.1:5678/form/researchforge-v2-form", flush=True)


if __name__ == "__main__":
    main()
