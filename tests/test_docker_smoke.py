from scripts import docker_smoke


def test_packaging_smoke_is_v2_only_and_zero_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        docker_smoke,
        "request_text",
        lambda url, timeout=10.0: "ok" if url.endswith("/healthz") else '<div id="root"></div>',
    )
    monkeypatch.setattr(
        docker_smoke,
        "request_json",
        lambda url, timeout=10.0: {
            "real_agent_loop": True,
            "provider": "hybrid",
            "model": "deepseek-v4-flash",
            "agent_ready": True,
        },
    )
    checked: list[tuple[str, int]] = []
    monkeypatch.setattr(
        docker_smoke,
        "expect_status",
        lambda url, expected, timeout=10.0: checked.append((url, expected)),
    )

    result = docker_smoke.run_smoke("http://test")

    assert result["runtime"] == "v2"
    assert result["provider_calls"] == 0
    assert result["legacy_v1_live_api"] is False
    assert any("/v1/runtime-capabilities" in url and status == 404 for url, status in checked)
