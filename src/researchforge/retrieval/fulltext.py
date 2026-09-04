"""Deterministic full-filing evidence indexing and lexical retrieval helpers."""

from __future__ import annotations

import hashlib
import html
import re
from html.parser import HTMLParser
from typing import Any

JsonObject = dict[str, Any]

_SECTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Risk factors", ("risk factors", "principal risks", "主要风险", "风险因素", "风险提示")),
    (
        "Management discussion",
        (
            "management discussion",
            "management's discussion",
            "md&a",
            "results of operations",
            "管理层讨论",
            "经营情况讨论",
        ),
    ),
    (
        "Business and segments",
        (
            "business overview",
            "our business",
            "segment information",
            "reportable segments",
            "reportable segment",
            "business segments",
            "operating segments",
            "segment revenue",
            "revenue by market platform",
            "revenue by geographic",
            "业务概述",
            "业务分部",
            "分部信息",
            "主营业务",
        ),
    ),
    (
        "Growth drivers",
        (
            "growth strategy",
            "growth drivers",
            "drivers of growth",
            "driven by",
            "year-over-year",
            "year over year",
            "sequentially",
            "增长战略",
            "增长驱动",
            "同比增长",
            "主要驱动",
        ),
    ),
    (
        "Research and development",
        ("research and development", "r&d expenses", "研发投入", "研究与开发"),
    ),
    (
        "Liquidity and capital",
        (
            "liquidity and capital",
            "capital resources",
            "capital expenditures",
            "资本开支",
            "流动性",
            "资本资源",
        ),
    ),
    (
        "Outlook",
        (
            "business outlook",
            "future development",
            "future outlook",
            "经营展望",
            "未来发展",
            "经营计划",
        ),
    ),
    (
        "Customers and suppliers",
        ("customers and suppliers", "major customers", "major suppliers", "主要客户", "主要供应商"),
    ),
    (
        "Financial statements",
        (
            "consolidated statements",
            "income statement",
            "balance sheet",
            "cash flows",
            "财务报表",
            "利润表",
            "资产负债表",
            "现金流量表",
        ),
    ),
)


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"script", "style", "noscript"}:
            self._hidden_depth += 1
        elif self._hidden_depth == 0 and tag.casefold() in {
            "p",
            "div",
            "br",
            "tr",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript"} and self._hidden_depth:
            self._hidden_depth -= 1
        elif self._hidden_depth == 0 and tag.casefold() in {"p", "div", "tr", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._hidden_depth == 0:
            self.parts.append(data)


def _normalize_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in html.unescape(value).splitlines()]
    return "\n".join(line for line in lines if line)


def _section(text: str) -> str:
    probe = text.casefold()[:2000]
    for label, markers in _SECTION_RULES:
        if any(marker.casefold() in probe for marker in markers):
            return label
    return "Filing narrative"


def _windows(text: str, *, size: int = 2400, overlap: int = 220) -> list[tuple[int, int, str]]:
    if not text:
        return []
    output: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            split = max(
                text.rfind("\n", start, end),
                text.rfind("。", start, end),
                text.rfind(". ", start, end),
            )
            if split > start + size // 2:
                end = split + 1
        chunk = text[start:end].strip()
        if len(chunk) >= 40:
            output.append((start, end, chunk))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return output


def _chunk(
    source: JsonObject,
    *,
    chunk_id: str,
    text: str,
    section: str,
    page: int,
    char_start: int | None,
    char_end: int | None,
    language: str,
    parser_version: str,
) -> JsonObject:
    return {
        "schema_version": "1.4.0",
        "chunk_id": chunk_id,
        "document_id": source["document_id"],
        "company": source["company"],
        "reporting_period": source.get("reporting_period"),
        "document_type": (
            "interim_report"
            if source["document_type"] == "semiannual_report"
            else source["document_type"]
        ),
        "published_at": source["published_at"],
        "retrieved_at": source["retrieved_at"],
        "content_role": "untrusted_source",
        "section": section,
        "text": text,
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "source_uri": source["source_uri"],
        "locator": {
            "page_start": page,
            "page_end": page,
            "paragraph_start": None,
            "paragraph_end": None,
            "char_start": char_start,
            "char_end": char_end,
        },
        "language": language,
        "parser_version": parser_version,
        "quality_flags": ["text_native"],
    }


def index_pdf_pages(
    source: JsonObject,
    pages: tuple[str, ...],
    *,
    id_prefix: str,
    language: str,
    parser_version: str,
) -> list[JsonObject]:
    """Turn native-text PDF pages into short, page-addressable Evidence Chunks."""
    chunks: list[JsonObject] = []
    for page_number, raw in enumerate(pages, start=1):
        text = _normalize_text(raw)
        for part, (start, end, excerpt) in enumerate(_windows(text), start=1):
            chunks.append(
                _chunk(
                    source,
                    chunk_id=f"{id_prefix}_page_{page_number}_{part}",
                    text=excerpt,
                    section=_section(excerpt),
                    page=page_number,
                    char_start=start,
                    char_end=end,
                    language=language,
                    parser_version=parser_version,
                )
            )
    return chunks


def index_html(
    source: JsonObject,
    payload: bytes,
    *,
    id_prefix: str,
    language: str = "en-US",
    parser_version: str = "htmlparser-1.0.0",
) -> list[JsonObject]:
    """Create locator-preserving chunks from official HTML without executing markup."""
    parser = _VisibleTextParser()
    parser.feed(payload.decode("utf-8", errors="ignore"))
    text = _normalize_text("".join(parser.parts))
    return [
        _chunk(
            source,
            chunk_id=f"{id_prefix}_html_{index}",
            text=excerpt,
            section=_section(excerpt),
            page=1,
            char_start=start,
            char_end=end,
            language=language,
            parser_version=parser_version,
        )
        for index, (start, end, excerpt) in enumerate(_windows(text), start=1)
    ]
