from scripts.start_demo import build_commands


def test_demo_start_is_bounded_to_project_services_and_verifies_both_surfaces() -> None:
    commands = build_commands(build=True, smoke=True)
    serialized = [" ".join(command) for command in commands]
    assert serialized[0] == "docker compose up -d --force-recreate --build --wait"
    assert any(
        "import:workflow --input=/files/researchforge-v1.7.workflow.json" in line
        for line in serialized
    )
    assert any("publish:workflow --id=researchforgeV17" in line for line in serialized)
    assert any("scripts/docker_smoke.py" in line for line in serialized)
    assert any("scripts.n8n_smoke" in line for line in serialized)
    assert all("down" not in command for command in serialized)


def test_demo_start_can_reuse_images_without_smoke() -> None:
    commands = build_commands(build=False, smoke=False)
    assert commands[0] == ["docker", "compose", "up", "-d", "--force-recreate", "--wait"]
    assert not any("docker_smoke" in part for command in commands for part in command)
