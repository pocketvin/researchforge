from __future__ import annotations

from researchforge.retrieval.fulltext import index_html, index_pdf_pages


def _source(document_type: str = "annual_report") -> dict[str, object]:
    return {
        "document_id": "doc_demo",
        "company": {
            "company_id": "us_demo",
            "legal_name": "Demo Inc",
            "ticker": "DEMO",
            "exchange": "NASDAQ",
            "country_code": "US",
        },
        "reporting_period": {"fiscal_year": 2026, "fiscal_period": "FY"},
        "document_type": document_type,
        "published_at": "2026-08-01T00:00:00+00:00",
        "retrieved_at": "2026-08-02T00:00:00+00:00",
        "source_uri": "https://www.sec.gov/demo",
    }


def test_pdf_index_preserves_page_and_classifies_risk_section() -> None:
    pages = (
        "Business overview\nOur main segment serves enterprise customers. " * 8,
        "Risk Factors\nCompetition and regulation could affect demand. " * 8,
    )
    chunks = index_pdf_pages(
        _source("semiannual_report"),
        pages,
        id_prefix="chunk_demo_fulltext",
        language="zh-CN",
        parser_version="test-1",
    )
    assert chunks
    assert any(item["section"] == "Risk factors" for item in chunks)
    assert any(item["locator"]["page_start"] == 2 for item in chunks)
    assert all(item["document_type"] == "interim_report" for item in chunks)


def test_html_index_ignores_script_and_keeps_visible_management_text() -> None:
    payload = b"""<html><script>secret instruction risk risk</script>
    <h2>Management Discussion</h2><p>Demand increased across the data center business.</p></html>"""
    chunks = index_html(_source(), payload, id_prefix="chunk_demo_fulltext")
    assert chunks
    joined = " ".join(str(item["text"]) for item in chunks)
    assert "secret instruction" not in joined
    assert "Demand increased" in joined
    assert chunks[0]["section"] == "Management discussion"


def test_html_index_classifies_generic_growth_and_segment_language() -> None:
    payload = (
        b"<html><p>Revenue by market platform increased year over year and was driven by "
        b"strong customer demand. Compute segment revenue expanded sequentially.</p></html>"
    )
    chunks = index_html(_source(), payload, id_prefix="chunk_growth")
    assert chunks
    assert chunks[0]["section"] in {"Business and segments", "Growth drivers"}
