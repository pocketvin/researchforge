import io
import json
from pathlib import Path
from types import SimpleNamespace

from scripts import start_demo
from scripts.start_demo import build_commands


def test_demo_start_uses_only_v2_runtime_and_v2_n8n_workflow() -> None:
    commands = build_commands(build=True, smoke=True)
    serialized = [" ".join(command) for command in commands]
    assert serialized[0] == "docker compose up -d --force-recreate --remove-orphans --build --wait"
    assert any(
        "import:workflow --input=/files/researchforge-v2.workflow.json" in line
        for line in serialized
    )
    assert any("publish:workflow --id=researchforgeV17" in line for line in serialized)
    assert any("scripts/docker_smoke.py" in line for line in serialized)
    assert any("scripts.n8n_smoke" in line for line in serialized)
    assert all("/v1/" not in line for line in serialized)
    assert all("down" not in command for command in serialized)


def test_demo_start_can_reuse_images_without_smoke() -> None:
    commands = build_commands(build=False, smoke=False)
    assert commands[0] == [
        "docker",
        "compose",
        "up",
        "-d",
        "--force-recreate",
        "--remove-orphans",
        "--wait",
    ]
    assert not any("docker_smoke" in part for command in commands for part in command)


def test_compose_forwards_only_v2_runtime_configuration() -> None:
    compose = (Path(__file__).resolve().parents[1] / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    required = {
        "RESEARCHFORGE_PROVIDER",
        "RESEARCHFORGE_QWEN_API_KEY",
        "RESEARCHFORGE_QWEN_BASE_URL",
        "RESEARCHFORGE_DEEPSEEK_API_KEY",
        "RESEARCHFORGE_DEEPSEEK_BASE_URL",
        "RESEARCHFORGE_KIMI_API_KEY",
        "RESEARCHFORGE_KIMI_BASE_URL",
        "RESEARCHFORGE_V2_RUN_BUDGET_USD",
    }
    for name in required:
        assert f"{name}: ${{{name}" in compose
    assert "postgres:" not in compose
    assert "RESEARCHFORGE_DATABASE_" not in compose
    assert "RESEARCHFORGE_DATA_ROOT" not in compose


def test_verify_runtime_checks_hybrid_role_routing(monkeypatch) -> None:
    settings = SimpleNamespace(
        researchforge_provider="hybrid",
        researchforge_model="gpt-5.6-luna",
        researchforge_deepseek_model="deepseek-v4-flash",
        researchforge_qwen_model="qwen-plus",
        researchforge_qwen_review_model="qwen-plus",
        researchforge_qwen_fallback_synthesis_model="qwen3-max",
        researchforge_qwen_vision_model="qwen3-vl-plus",
    )
    monkeypatch.setattr(start_demo, "load_runtime_settings", lambda _root: settings)
    payload = {
        "agent_ready": True,
        "provider": "hybrid",
        "model": "deepseek-v4-flash",
        "reflection_model": "deepseek-v4-flash",
        "synthesis_model": "deepseek-v4-flash",
        "semantic_review_model": "qwen-plus",
        "research_fallback_model": "qwen-plus",
        "fallback_reflection_model": "qwen3-max",
        "fallback_synthesis_model": "qwen3-max",
        "fallback_semantic_review_model": "deepseek-v4-flash",
        "vision_model": "qwen3-vl-plus",
    }

    def fake_urlopen(url: str, timeout: float):
        assert url == "http://127.0.0.1:8000/v2/capabilities"
        assert timeout == 10.0
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(start_demo.urllib.request, "urlopen", fake_urlopen)
    start_demo.verify_runtime("auto")
