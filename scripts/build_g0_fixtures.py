#!/usr/bin/env python3
"""Build the reviewed G0 public fixture package from frozen reported cells.

Raw PDFs stay under the ignored ``data/raw/g0`` directory. This script verifies
their hashes, normalizes reviewed values with Decimal, and writes only metadata
and factual JSON artifacts suitable for the public repository.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "g0"
OUTPUT_DIR = ROOT / "data" / "fixtures" / "g0"
SOURCE_DIR = OUTPUT_DIR / "source-documents"
FACT_DIR = OUTPUT_DIR / "financial-facts"
GOLDEN_CASES_PATH = OUTPUT_DIR / "golden-cases.json"
SCHEMA_VERSION = "1.4.0"
PARSER_VERSION = "1.0.0"
MAPPING_VERSION = "1.0.0"
RETRIEVED_AT = "2026-08-30T22:16:00+08:00"
CREATED_AT = "2026-08-30T22:30:00+08:00"
OWNER_SIGNED_AT = "2026-08-31T15:51:55+08:00"

CATL = {
    "company_id": "cn_300750",
    "legal_name": "宁德时代新能源科技股份有限公司",
    "ticker": "300750",
    "exchange": "SZSE",
    "country_code": "CN",
}
EVE = {
    "company_id": "cn_300014",
    "legal_name": "惠州亿纬锂能股份有限公司",
    "ticker": "300014",
    "exchange": "SZSE",
    "country_code": "CN",
}


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    """Frozen metadata for one official filing."""

    slug: str
    company: dict[str, str]
    document_type: str
    title: str
    published_at: str
    uri: str
    sha256: str
    period_start: str
    period_end: str
    fiscal_year: int
    fiscal_period: str
    restatement_status: str = "as_reported"
    source_id: str = "source_cninfo"

    @property
    def document_id(self) -> str:
        return f"doc_g0_{self.slug.replace('-', '_')}"


@dataclass(frozen=True, slots=True)
class ReportedFact:
    """One visually reviewed cell before base-unit normalization."""

    document_slug: str
    metric_code: str
    reported_value: str
    reported_scale: int
    page: int
    table: str
    row_label: str
    column_label: str
    period_basis: str


DOCUMENTS = (
    DocumentSpec(
        slug="catl-2023q3",
        company=CATL,
        document_type="quarterly_report",
        title="宁德时代新能源科技股份有限公司2023年第三季度报告",
        published_at="2023-10-20T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2023-10-20/1218095874.PDF",
        sha256="7681bd022913880699d1c58c404ae8c5a526f891f4275851b09b5da19f82cad3",
        period_start="2023-01-01",
        period_end="2023-09-30",
        fiscal_year=2023,
        fiscal_period="Q3",
    ),
    DocumentSpec(
        slug="catl-2023fy",
        company=CATL,
        document_type="annual_report",
        title="宁德时代新能源科技股份有限公司2023年年度报告",
        published_at="2024-03-16T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2024-03-16/1219313047.PDF",
        sha256="6081f0377617dddb82f900569d6458c278a7ab26697b34c87684188eac083471",
        period_start="2023-01-01",
        period_end="2023-12-31",
        fiscal_year=2023,
        fiscal_period="FY",
    ),
    DocumentSpec(
        slug="catl-2024q1",
        company=CATL,
        document_type="quarterly_report",
        title="宁德时代新能源科技股份有限公司2024年第一季度报告",
        published_at="2024-04-16T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2024-04-16/1219619642.PDF",
        sha256="7be8765c33298b96a1010e61a7bcac3212db7f58dc3d360888548cfd11424265",
        period_start="2024-01-01",
        period_end="2024-03-31",
        fiscal_year=2024,
        fiscal_period="Q1",
    ),
    DocumentSpec(
        slug="catl-2024h1",
        company=CATL,
        document_type="semiannual_report",
        title="宁德时代新能源科技股份有限公司2024年半年度报告",
        published_at="2024-07-26T23:59:59+08:00",
        uri=(
            "https://disc.static.szse.cn/disc/disk03/finalpage/2024-07-26/"
            "6d9c1c9e-239e-4946-a477-84ea91313086.PDF"
        ),
        sha256="2a690cb2471c1f0d4539d909a9f068c03710a838ddd35313175790169e85eab1",
        period_start="2024-01-01",
        period_end="2024-06-30",
        fiscal_year=2024,
        fiscal_period="H1",
        source_id="source_szse",
    ),
    DocumentSpec(
        slug="eve-2023q3",
        company=EVE,
        document_type="quarterly_report",
        title="惠州亿纬锂能股份有限公司2023年第三季度报告",
        published_at="2023-10-26T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2023-10-26/1218149368.PDF",
        sha256="dafbcdf7980cbfcb154a9c4dc1a9456ce04dc32066ca92a59653ceeeb4148f49",
        period_start="2023-01-01",
        period_end="2023-09-30",
        fiscal_year=2023,
        fiscal_period="Q3",
    ),
    DocumentSpec(
        slug="eve-2023fy",
        company=EVE,
        document_type="annual_report",
        title="惠州亿纬锂能股份有限公司2023年年度报告",
        published_at="2024-04-19T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2024-04-19/1219668064.PDF",
        sha256="959d6d51d529fd5129c829d1358ad41d384c95560ef2f8dc23caedd91e01f33e",
        period_start="2023-01-01",
        period_end="2023-12-31",
        fiscal_year=2023,
        fiscal_period="FY",
    ),
    DocumentSpec(
        slug="eve-2024q1",
        company=EVE,
        document_type="quarterly_report",
        title="惠州亿纬锂能股份有限公司2024年第一季度报告",
        published_at="2024-04-25T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2024-04-25/1219791452.PDF",
        sha256="7427e016767527a676a9ebe20fcf23df4d4ee786edd10e231fe6791416d47019",
        period_start="2024-01-01",
        period_end="2024-03-31",
        fiscal_year=2024,
        fiscal_period="Q1",
    ),
    DocumentSpec(
        slug="eve-2024h1-corrected",
        company=EVE,
        document_type="semiannual_report",
        title="惠州亿纬锂能股份有限公司2024年半年度报告（更正后）",  # noqa: RUF001
        published_at="2024-09-03T23:59:59+08:00",
        uri="https://static.cninfo.com.cn/finalpage/2024-09-03/1221114672.PDF",
        sha256="28f193e0c8f4d19b4868d451d29ad47d52f0c4ba8d3bf3f34705e5f8b885e652",
        period_start="2024-01-01",
        period_end="2024-06-30",
        fiscal_year=2024,
        fiscal_period="H1",
        restatement_status="restated",
    ),
)


def facts_for(
    slug: str,
    *,
    scale: int,
    accounts_receivable: tuple[str, int],
    inventory: tuple[str, int],
    revenue: tuple[str, int],
    operating_cost: tuple[str, int],
    net_income: tuple[str, int],
    operating_cash_flow: tuple[str, int],
) -> tuple[ReportedFact, ...]:
    """Create the six frozen fact cells for one filing."""
    return (
        ReportedFact(
            slug,
            "accounts_receivable",
            accounts_receivable[0],
            scale,
            accounts_receivable[1],
            "合并资产负债表",
            "应收账款",
            "报告期末",
            "instant",
        ),
        ReportedFact(
            slug,
            "inventory",
            inventory[0],
            scale,
            inventory[1],
            "合并资产负债表",
            "存货",
            "报告期末",
            "instant",
        ),
        ReportedFact(
            slug,
            "revenue",
            revenue[0],
            scale,
            revenue[1],
            "合并利润表",
            "营业收入",
            "本期/年初至报告期末",
            "ytd",
        ),
        ReportedFact(
            slug,
            "operating_cost",
            operating_cost[0],
            scale,
            operating_cost[1],
            "合并利润表",
            "营业成本",
            "本期/年初至报告期末",
            "ytd",
        ),
        ReportedFact(
            slug,
            "net_income",
            net_income[0],
            scale,
            net_income[1],
            "合并利润表",
            "归属于母公司股东/所有者的净利润",
            "本期/年初至报告期末",
            "ytd",
        ),
        ReportedFact(
            slug,
            "operating_cash_flow",
            operating_cash_flow[0],
            scale,
            operating_cash_flow[1],
            "合并现金流量表",
            "经营活动产生的现金流量净额",
            "本期/年初至报告期末",
            "ytd",
        ),
    )


FACTS = (
    *facts_for(
        "catl-2023q3",
        scale=10_000,
        accounts_receivable=("6872679.85", 7),
        inventory=("4888401.17", 7),
        revenue=("29467725.06", 10),
        operating_cost=("23009603.81", 10),
        net_income=("3114547.36", 11),
        operating_cash_flow=("5265369.23", 12),
    ),
    *facts_for(
        "catl-2023fy",
        scale=10_000,
        accounts_receivable=("6402053.34", 115),
        inventory=("4543389.01", 115),
        revenue=("40091704.49", 120),
        operating_cost=("30907043.40", 120),
        net_income=("4412124.83", 121),
        operating_cash_flow=("9282612.44", 124),
    ),
    *facts_for(
        "catl-2024q1",
        scale=10_000,
        accounts_receivable=("5118689.72", 5),
        inventory=("4397931.13", 6),
        revenue=("7977077.86", 8),
        operating_cost=("5869890.63", 8),
        net_income=("1050992.32", 9),
        operating_cash_flow=("2835791.06", 11),
    ),
    *facts_for(
        "catl-2024h1",
        scale=10_000,
        accounts_receivable=("5809947.60", 64),
        inventory=("4805067.62", 64),
        revenue=("16676683.36", 69),
        operating_cost=("12251784.88", 69),
        net_income=("2286498.74", 70),
        operating_cash_flow=("4470895.46", 73),
    ),
    *facts_for(
        "eve-2023q3",
        scale=1,
        accounts_receivable=("11008577641.35", 8),
        inventory=("8790701505.80", 8),
        revenue=("35528837484.66", 11),
        operating_cost=("29567112888.91", 11),
        net_income=("3424389233.10", 12),
        operating_cash_flow=("5358649318.89", 14),
    ),
    *facts_for(
        "eve-2023fy",
        scale=1,
        accounts_receivable=("12427533747.50", 93),
        inventory=("6316007223.39", 94),
        revenue=("48783587175.86", 99),
        operating_cost=("40473296810.60", 99),
        net_income=("4050174699.52", 100),
        operating_cash_flow=("8676259761.12", 103),
    ),
    *facts_for(
        "eve-2024q1",
        scale=1,
        accounts_receivable=("12086041697.14", 7),
        inventory=("6703161813.17", 7),
        revenue=("9317321354.65", 10),
        operating_cost=("7673910397.50", 10),
        net_income=("1065713845.72", 11),
        operating_cash_flow=("-1751380202.07", 13),
    ),
    *facts_for(
        "eve-2024h1-corrected",
        scale=1,
        accounts_receivable=("12502761822.36", 57),
        inventory=("6357901044.76", 57),
        revenue=("21659398588.08", 62),
        operating_cost=("18095684686.37", 62),
        net_income=("2137249689.22", 63),
        operating_cash_flow=("311882588.92", 66),
    ),
)

SIGNOFF_FACT_IDS = (
    "fact_g0_catl_2023q3_revenue",
    "fact_g0_catl_2023q3_operating_cash_flow",
    "fact_g0_catl_2023fy_operating_cost",
    "fact_g0_catl_2023fy_net_income",
    "fact_g0_catl_2024q1_accounts_receivable",
    "fact_g0_catl_2024q1_inventory",
    "fact_g0_catl_2024q1_revenue",
    "fact_g0_catl_2024h1_operating_cost",
    "fact_g0_catl_2024h1_net_income",
    "fact_g0_catl_2024h1_operating_cash_flow",
    "fact_g0_eve_2023q3_accounts_receivable",
    "fact_g0_eve_2023q3_inventory",
    "fact_g0_eve_2023fy_revenue",
    "fact_g0_eve_2023fy_operating_cost",
    "fact_g0_eve_2023fy_net_income",
    "fact_g0_eve_2024q1_net_income",
    "fact_g0_eve_2024q1_operating_cash_flow",
    "fact_g0_eve_2024h1_corrected_accounts_receivable",
    "fact_g0_eve_2024h1_corrected_inventory",
    "fact_g0_eve_2024h1_corrected_operating_cash_flow",
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_hash(artifact_hashes: dict[str, str]) -> str:
    payload = json.dumps(
        artifact_hashes,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _ratio(numerator: Decimal, denominator: Decimal) -> str:
    if denominator <= 0:
        raise ValueError("golden-case denominator must be positive")
    return format(numerator / denominator, "f")


def _golden_cases(facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    def value(fact_id: str) -> Decimal:
        return Decimal(facts[fact_id]["value"])

    def earnings_quality(company: str, period: str) -> dict[str, Any]:
        prefix = f"fact_g0_{company}_{period}_"
        revenue_id = prefix + "revenue"
        cost_id = prefix + "operating_cost"
        income_id = prefix + "net_income"
        ocf_id = prefix + "operating_cash_flow"
        revenue = value(revenue_id)
        cost = value(cost_id)
        income = value(income_id)
        ocf = value(ocf_id)
        gross_profit_value = revenue - cost
        divergence = income > 0 and ocf < 0
        return {
            "fact_ids": [revenue_id, cost_id, income_id, ocf_id],
            "calculations": {
                "gross_profit": format(gross_profit_value, "f"),
                "gross_margin": _ratio(gross_profit_value, revenue),
                "cash_conversion": _ratio(ocf, income),
                "profit_cash_divergence": "1" if divergence else "0",
            },
        }

    catl_q1 = earnings_quality("catl", "2024q1")
    eve_q1 = earnings_quality("eve", "2024q1")
    catl_h1 = earnings_quality("catl", "2024h1")
    eve_h1 = earnings_quality("eve", "2024h1_corrected")
    return {
        "fixture_version": "1.0.0",
        "schema_version": SCHEMA_VERSION,
        "review_status": "owner_signed",
        "cases": [
            {
                "case_id": "golden_g0_catl_2024q1_earnings_quality",
                "task_type": "company_research",
                "research_time": "2024-04-17T00:00:00+08:00",
                "companies": ["cn_300750"],
                "periods": ["2024Q1"],
                **catl_q1,
                "expected_signal": "positive_profit_positive_ocf_strong_conversion",
                "limitations": [
                    "One-period deterministic evidence; no causal explanation is inferred."
                ],
            },
            {
                "case_id": "golden_g0_eve_2024q1_earnings_quality",
                "task_type": "company_research",
                "research_time": "2024-04-26T00:00:00+08:00",
                "companies": ["cn_300014"],
                "periods": ["2024Q1"],
                **eve_q1,
                "expected_signal": "positive_profit_negative_ocf_divergence",
                "limitations": ["The divergence is an investigation signal, not causal proof."],
            },
            {
                "case_id": "golden_g0_catl_eve_2024h1_peer",
                "task_type": "peer_comparison",
                "research_time": "2024-09-04T00:00:00+08:00",
                "companies": ["cn_300750", "cn_300014"],
                "periods": ["2024H1", "2024H1-restated"],
                "fact_ids": catl_h1["fact_ids"] + eve_h1["fact_ids"],
                "calculations": {
                    "catl": catl_h1["calculations"],
                    "eve": eve_h1["calculations"],
                },
                "expected_signal": "aligned_h1_framework_with_eve_corrected_lineage",
                "limitations": [
                    "Cross-company ratios are descriptive and do not establish investment merit.",
                    "EVE uses its corrected filing available at the recorded research time.",
                ],
            },
        ],
    }


def _verify_raw_hash(document: DocumentSpec) -> int:
    path = RAW_DIR / f"{document.slug}.pdf"
    if not path.is_file():
        raise FileNotFoundError(f"authorized raw filing is missing: {path}")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != document.sha256:
        raise ValueError(f"raw filing hash mismatch for {document.slug}: {digest}")
    if not payload.startswith(b"%PDF-"):
        raise ValueError(f"raw filing is not a PDF: {document.slug}")
    return len(payload)


def _period(document: DocumentSpec, basis: str) -> dict[str, Any]:
    return {
        "period_start": (document.period_end if basis == "instant" else document.period_start),
        "period_end": document.period_end,
        "fiscal_year": document.fiscal_year,
        "fiscal_period": document.fiscal_period,
        "period_basis": basis,
        "accounting_standard": "CAS",
        "statement_scope": "consolidated",
        "restatement_status": document.restatement_status,
    }


def _source_document(document: DocumentSpec) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": document.document_id,
        "source_id": document.source_id,
        "company": document.company,
        "document_type": document.document_type,
        "title": document.title,
        "published_at": document.published_at,
        "retrieved_at": RETRIEVED_AT,
        "available_from": document.published_at,
        "source_uri": document.uri,
        "content_hash": document.sha256,
        "mime_type": "application/pdf",
        "language": "zh-CN",
        "reporting_period": _period(document, "ytd"),
        "license": {
            "license_id": None,
            "publication_mode": "derived_facts_and_short_excerpts",
            "raw_payload_committed": False,
            "notes": (
                "Raw filing excluded. Public package contains normalized factual cells, "
                "hashes, page/table locators, and the official link only."
            ),
        },
        "parser_version": PARSER_VERSION,
        "quality_flags": [
            "sha256_verified",
            "page_cells_visually_reviewed",
            "raw_payload_excluded",
        ],
        "created_at": CREATED_AT,
    }


def _financial_fact(document: DocumentSpec, fact: ReportedFact) -> dict[str, Any]:
    value = Decimal(fact.reported_value) * Decimal(fact.reported_scale)
    return {
        "schema_version": SCHEMA_VERSION,
        "fact_id": f"fact_g0_{document.slug.replace('-', '_')}_{fact.metric_code}",
        "fact_kind": "reported",
        "company": document.company,
        "metric_code": fact.metric_code,
        "value": format(value, "f"),
        "measurement_unit": "CURRENCY",
        "currency": "CNY",
        "canonical_scale": 1,
        "period": _period(document, fact.period_basis),
        "sign_convention": "natural_statement_value",
        "source": {
            "source_id": document.source_id,
            "document_id": document.document_id,
            "source_type": "official_filing",
            "published_at": document.published_at,
            "retrieved_at": RETRIEVED_AT,
            "uri": document.uri,
            "content_hash": document.sha256,
            "license_id": None,
            "redistribution_allowed": False,
        },
        "source_locator": {
            "page": fact.page,
            "section": "财务报表",
            "table": fact.table,
            "row_label": fact.row_label,
            "column_label": fact.column_label,
        },
        "availability": "available",
        "quality_flags": (
            ["unit_normalized", "restated"]
            if document.restatement_status == "restated"
            else ["unit_normalized"]
        ),
        "created_at": CREATED_AT,
    }


def main() -> None:
    """Verify raw evidence and emit the public G0 package."""
    document_by_slug = {document.slug: document for document in DOCUMENTS}
    if len(document_by_slug) != len(DOCUMENTS):
        raise ValueError("document slugs must be unique")
    if len(FACTS) != 48:
        raise ValueError(f"expected 48 reviewed facts, found {len(FACTS)}")

    byte_counts = {document.slug: _verify_raw_hash(document) for document in DOCUMENTS}
    source_ids: list[str] = []
    for document in DOCUMENTS:
        source = _source_document(document)
        source_ids.append(document.document_id)
        _write_json(SOURCE_DIR / f"{document.slug}.json", source)

    fact_ids: list[str] = []
    facts_by_id: dict[str, dict[str, Any]] = {}
    reported_cells: list[dict[str, Any]] = []
    for fact in FACTS:
        document = document_by_slug[fact.document_slug]
        artifact = _financial_fact(document, fact)
        fact_ids.append(artifact["fact_id"])
        facts_by_id[artifact["fact_id"]] = artifact
        _write_json(FACT_DIR / f"{artifact['fact_id']}.json", artifact)
        reported_cells.append(
            {
                "fact_id": artifact["fact_id"],
                "reported_value": fact.reported_value,
                "reported_scale": fact.reported_scale,
                "canonical_value": artifact["value"],
                "visual_match": True,
            }
        )

    missing_signoff_ids = set(SIGNOFF_FACT_IDS) - set(fact_ids)
    if missing_signoff_ids:
        raise ValueError(f"signoff sample contains unknown facts: {sorted(missing_signoff_ids)}")
    _write_json(GOLDEN_CASES_PATH, _golden_cases(facts_by_id))

    artifact_paths = sorted((*SOURCE_DIR.glob("*.json"), *FACT_DIR.glob("*.json")))
    artifact_paths.append(GOLDEN_CASES_PATH)
    artifact_hashes = {str(path.relative_to(ROOT)): _sha256(path) for path in artifact_paths}

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_id": "g0_catl_eve_2023q3_to_2024h1",
        "status": "owner_signed",
        "mapping_version": MAPPING_VERSION,
        "parser_version": PARSER_VERSION,
        "created_at": CREATED_AT,
        "raw_pdf_committed": False,
        "source_document_count": len(source_ids),
        "financial_fact_count": len(fact_ids),
        "source_document_ids": source_ids,
        "financial_fact_ids": fact_ids,
        "artifact_hashes": artifact_hashes,
        "package_hash": _package_hash(artifact_hashes),
        "raw_byte_counts": byte_counts,
        "reconciliation": {
            "sample_size": len(reported_cells),
            "semantic_complete_count": len(reported_cells),
            "visual_match_count": len(reported_cells),
            "unresolved_mismatch_count": 0,
            "semantic_completeness_rate": "1.0",
            "numeric_agreement_rate": "1.0",
            "cells": reported_cells,
        },
        "owner_signoff": {
            "status": "signed",
            "signed_at": OWNER_SIGNED_AT,
            "evidence_file": "docs/evidence/g0-owner-signoff.md",
            "sample_size": len(SIGNOFF_FACT_IDS),
            "fact_ids": list(SIGNOFF_FACT_IDS),
        },
        "limitations": [
            "Two-company, four-period source spike only; not full-market coverage.",
            "Public package excludes raw PDFs and does not establish redistribution rights.",
            "Publication timestamps use a conservative end-of-disclosure-day boundary.",
        ],
    }
    _write_json(OUTPUT_DIR / "manifest.json", manifest)
    print(f"WROTE {len(source_ids)} source documents and {len(fact_ids)} facts")


if __name__ == "__main__":
    main()
