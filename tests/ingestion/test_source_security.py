from __future__ import annotations

from io import BytesIO
from urllib.request import Request

import pytest

from researchforge.ingestion import discovery
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.v2.preparation import OfficialRedirects, validate_url


class _FakeResponse(BytesIO):
    def __init__(self, payload: bytes, final_url: str) -> None:
        super().__init__(payload)
        self._final_url = final_url

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def geturl(self) -> str:
        return self._final_url


def test_v2_acquisition_rejects_non_official_direct_url() -> None:
    with pytest.raises(IngestionAbstention) as caught:
        validate_url("https://evil.example/report.pdf")
    assert caught.value.code == "UNTRUSTED_SOURCE_URI"


def test_v2_acquisition_rejects_redirect_to_non_official_host() -> None:
    handler = OfficialRedirects()
    with pytest.raises(IngestionAbstention) as caught:
        handler.redirect_request(None, None, 302, "redirect", {}, "https://evil.example/file.pdf")
    assert caught.value.code == "UNTRUSTED_SOURCE_URI"


def test_discovery_json_rejects_redirect_to_non_official_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        discovery,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"{}", "https://evil.example/data.json"),
    )

    with pytest.raises(IngestionAbstention) as caught:
        discovery._read_json(Request("https://www.sec.gov/files/company_tickers.json"))

    assert caught.value.code == "UNTRUSTED_SOURCE_URI"
