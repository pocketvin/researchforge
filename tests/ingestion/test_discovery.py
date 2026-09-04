from __future__ import annotations

from urllib.error import URLError

import pytest

from researchforge.ingestion import discovery
from researchforge.ingestion.discovery import SecDiscoveryProvider
from researchforge.ingestion.errors import IngestionAbstention


def test_provider_network_error_becomes_safe_abstention(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> object:
        raise URLError("blocked")

    monkeypatch.setattr(discovery, "urlopen", fail)
    with pytest.raises(IngestionAbstention) as captured:
        discovery._json_get("https://www.sec.gov/files/company_tickers.json")

    error = captured.value
    assert error.code == "DISCLOSURE_PROVIDER_UNAVAILABLE"
    assert error.stage == "discovery"
    assert "SEC" in error.reason


def test_sec_user_agent_can_be_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEARCHFORGE_SEC_USER_AGENT", "ResearchForge/1.6 qa@example.com")
    headers = SecDiscoveryProvider._headers()
    assert headers["User-Agent"] == "ResearchForge/1.6 qa@example.com"
    assert headers["Accept"] == "application/json"
