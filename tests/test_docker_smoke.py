from scripts.docker_smoke import reviewed_cache_request


def test_packaging_smoke_uses_network_independent_reviewed_cache_mode() -> None:
    request = reviewed_cache_request("宁德时代", "CN", "2024H1")

    assert request["company_query"] == "宁德时代"
    assert request["market_hint"] == "CN"
    assert request["requested_period_label"] == "2024H1"
    assert request["research_mode"] == "financial_snapshot"
    assert request["research_time"] == "2026-09-05T00:00:00+08:00"
    assert str(request["idempotency_key"]).startswith("docker-smoke-")
