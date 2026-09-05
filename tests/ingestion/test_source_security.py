from __future__ import annotations

from io import BytesIO
from urllib.request import Request

import pytest

from researchforge.ingestion import discovery, hk_ifrs, sec_xbrl
from researchforge.ingestion.errors import IngestionAbstention


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


def test_sec_fetch_rejects_redirect_to_non_official_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sec_xbrl,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"<html></html>", "https://evil.example/file"),
    )

    with pytest.raises(IngestionAbstention) as caught:
        sec_xbrl._fetch("https://www.sec.gov/Archives/demo.htm")

    assert caught.value.code == "UNTRUSTED_SOURCE_URI"


def test_hk_pdf_fetch_rejects_redirect_to_non_official_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        hk_ifrs,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"%PDF-1.7 demo", "https://evil.example/file.pdf"),
    )

    with pytest.raises(IngestionAbstention) as caught:
        hk_ifrs.HkIfrsProductIngestion._fetch(
            "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/demo.pdf"
        )

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
