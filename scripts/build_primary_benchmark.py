#!/usr/bin/env python3
"""Build the public-safe 24-case V1.4 primary Benchmark package.

Raw official PDFs and verifier-only ground truth remain in ignored directories.
The committed package contains normalized facts, synthetic public evidence,
official links, physical-page locators, hashes, and sealed case manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "v1.4-primary"
G0_DIR = ROOT / "data" / "fixtures" / "g0"
OUTPUT_DIR = ROOT / "data" / "fixtures" / "v1.4-primary"
PRIVATE_DIR = ROOT / "data" / "private" / "benchmark" / "v1.4-primary"
SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.4-primary-preregistered.json"
SCHEMA_VERSION = "1.4.0"
CREATED_AT = "2026-09-01T05:30:00+08:00"
RETRIEVED_AT = "2026-09-01T04:40:00+08:00"
PARSER_VERSION = "1.1.0"
MAPPING_VERSION = "1.1.0"
PACKAGE_ID = "package_v1_4_primary_battery_earnings_quality"

COMPANIES = {
    "catl": {
        "company_id": "cn_300750",
        "legal_name": "宁德时代新能源科技股份有限公司",
        "ticker": "300750",
        "exchange": "SZSE",
        "country_code": "CN",
    },
    "eve": {
        "company_id": "cn_300014",
        "legal_name": "惠州亿纬锂能股份有限公司",
        "ticker": "300014",
        "exchange": "SZSE",
        "country_code": "CN",
    },
    "gotion": {
        "company_id": "cn_002074",
        "legal_name": "国轩高科股份有限公司",
        "ticker": "002074",
        "exchange": "SZSE",
        "country_code": "CN",
    },
    "sunwoda": {
        "company_id": "cn_300207",
        "legal_name": "欣旺达电子股份有限公司",
        "ticker": "300207",
        "exchange": "SZSE",
        "country_code": "CN",
    },
}


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    slug: str
    company_key: str
    period_label: str
    title: str
    published_at: str
    uri: str
    sha256: str
    scale: int

    @property
    def raw_path(self) -> Path:
        return RAW_DIR / f"{self.slug}.pdf"

    @property
    def text_path(self) -> Path:
        return RAW_DIR / f"{self.slug}.txt"

    @property
    def document_id(self) -> str:
        return f"doc_v14_{self.slug.replace('-', '_')}"


@dataclass(frozen=True, slots=True)
class FactSpec:
    metric_code: str
    reported_value: str
    page: int


def _doc(
    slug: str,
    company_key: str,
    period_label: str,
    title: str,
    published_date: str,
    announcement_id: str,
    sha256: str,
    *,
    scale: int = 1,
) -> DocumentSpec:
    return DocumentSpec(
        slug=slug,
        company_key=company_key,
        period_label=period_label,
        title=title,
        published_at=f"{published_date}T23:59:59+08:00",
        uri=f"https://static.cninfo.com.cn/finalpage/{published_date}/{announcement_id}.PDF",
        sha256=sha256,
        scale=scale,
    )


DOCUMENTS = (
    _doc(
        "catl-2024q3",
        "catl",
        "2024Q3",
        "宁德时代新能源科技股份有限公司2024年三季度报告",
        "2024-10-19",
        "1221432744",
        "a0134958d264a2a1630f4006208952f9498bafa8d74f3362b5d6c50a1cbce331",
        scale=10_000,
    ),
    _doc(
        "catl-2024fy",
        "catl",
        "2024FY",
        "宁德时代新能源科技股份有限公司2024年年度报告",
        "2025-03-15",
        "1222806982",
        "b4f1713d7b821eb076c102711d177fe942ccc2bc8dd171ae5d7a95799a65b0ad",
        scale=1_000,
    ),
    _doc(
        "eve-2024q3",
        "eve",
        "2024Q3",
        "惠州亿纬锂能股份有限公司2024年三季度报告",
        "2024-10-25",
        "1221508393",
        "77f8e01c3db565c96edb83a51e258ff4214d39369d17fba11c212ef4a486358b",
    ),
    _doc(
        "eve-2024fy",
        "eve",
        "2024FY",
        "惠州亿纬锂能股份有限公司2024年年度报告",
        "2025-04-18",
        "1223125812",
        "06be1a045d1ec713113cdcf626abfa534e2068f358770d5940975818a5a538aa",
    ),
    _doc(
        "gotion-2023q3",
        "gotion",
        "2023Q3",
        "国轩高科股份有限公司2023年三季度报告",
        "2023-10-28",
        "1218187245",
        "24cae8b63184987ad90531f4365a8e56d8bb6341f2d181b152be5fc9762a0d46",
    ),
    _doc(
        "gotion-2023fy",
        "gotion",
        "2023FY",
        "国轩高科股份有限公司2023年年度报告",
        "2024-04-20",
        "1219700973",
        "865d69b0da6dfa059de2c924e16eb8a4e5b11fabc1b19c985769baf44c94739d",
    ),
    _doc(
        "gotion-2024q1",
        "gotion",
        "2024Q1",
        "国轩高科股份有限公司2024年一季度报告",
        "2024-04-20",
        "1219701032",
        "971ef3c995416a4074bbfab8eea8a511d5ca1016e4576f79548a47a34eaa1fab",
    ),
    _doc(
        "gotion-2024h1",
        "gotion",
        "2024H1",
        "国轩高科股份有限公司2024年半年度报告",
        "2024-08-29",
        "1221032674",
        "69decc23b29cc4f4af05eaac74ea31a2909392a5bb8b9ae9ab26414dd53a6906",
    ),
    _doc(
        "gotion-2024q3",
        "gotion",
        "2024Q3",
        "国轩高科股份有限公司2024年三季度报告",
        "2024-10-30",
        "1221557518",
        "b024c7b32388cc212506acdb788548cf3aaff831a32bf85f2dbe2edbcd618049",
    ),
    _doc(
        "gotion-2024fy",
        "gotion",
        "2024FY",
        "国轩高科股份有限公司2024年年度报告",
        "2025-04-25",
        "1223284129",
        "cacf470f2dea6d0cf64ed9aa61872c726f739129a3715876a0b1059d2a9168ba",
    ),
    _doc(
        "sunwoda-2023q3",
        "sunwoda",
        "2023Q3",
        "欣旺达电子股份有限公司2023年三季度报告",
        "2023-10-27",
        "1218166071",
        "91912204813523ecb51b53edb3b1e07f1d84c6bba39c747dd18a274f8d202e8a",
    ),
    _doc(
        "sunwoda-2023fy",
        "sunwoda",
        "2023FY",
        "欣旺达电子股份有限公司2023年年度报告",
        "2024-04-11",
        "1219567241",
        "2b607a8320966d5648b7d819dbe53cd0b9a0e9fabf0e873f07ebfe0f83a6d821",
    ),
    _doc(
        "sunwoda-2024q1",
        "sunwoda",
        "2024Q1",
        "欣旺达电子股份有限公司2024年一季度报告",
        "2024-04-26",
        "1219827184",
        "5d896172249398c65e38ff1321af728c063bb47c725f51699c622b1479fd422a",
    ),
    _doc(
        "sunwoda-2024h1",
        "sunwoda",
        "2024H1",
        "欣旺达电子股份有限公司2024年半年度报告",
        "2024-08-30",
        "1221053778",
        "621c89394f5d0e4c618f9c83cc29cbf8f8c1d53c9985c048e7779f47c74a6158",
    ),
    _doc(
        "sunwoda-2024q3",
        "sunwoda",
        "2024Q3",
        "欣旺达电子股份有限公司2024年三季度报告",
        "2024-10-30",
        "1221559606",
        "848eb852787ce4667b90f810550426c406a623359dc23ac8c371d94da2f12a23",
    ),
    _doc(
        "sunwoda-2024fy",
        "sunwoda",
        "2024FY",
        "欣旺达电子股份有限公司2024年年度报告",
        "2025-04-22",
        "1223194845",
        "c12b433318341147f879c878899bdb03ffd875505b04ba6a51bb649d6d574c92",
    ),
)


def _facts(
    accounts_receivable: tuple[str, int],
    inventory: tuple[str, int],
    revenue: tuple[str, int],
    operating_cost: tuple[str, int],
    net_income: tuple[str, int],
    operating_cash_flow: tuple[str, int],
) -> tuple[FactSpec, ...]:
    return tuple(
        FactSpec(metric, value, page)
        for metric, (value, page) in (
            ("accounts_receivable", accounts_receivable),
            ("inventory", inventory),
            ("revenue", revenue),
            ("operating_cost", operating_cost),
            ("net_income", net_income),
            ("operating_cash_flow", operating_cash_flow),
        )
    )


FACTS_BY_SLUG = {
    "catl-2024q3": _facts(
        ("6670270.93", 6),
        ("5521527.53", 7),
        ("25904474.86", 9),
        ("18603290.09", 9),
        ("3600107.38", 10),
        ("6744360.11", 12),
    ),
    "catl-2024fy": _facts(
        ("64135510", 114),
        ("59835533", 114),
        ("362012554", 119),
        ("273518959", 119),
        ("50744682", 120),
        ("96990345", 123),
    ),
    "eve-2024q3": _facts(
        ("12493222676.56", 8),
        ("5924579949.11", 8),
        ("34049276929.36", 11),
        ("28130548504.43", 11),
        ("3188651049.63", 12),
        ("2116324374.61", 14),
    ),
    "eve-2024fy": _facts(
        ("13098572528.22", 91),
        ("5251441952.53", 92),
        ("48614556525.09", 97),
        ("40149208233.59", 97),
        ("4075585284.37", 98),
        ("4433732894.55", 101),
    ),
    "gotion-2023q3": _facts(
        ("12844054075.71", 5),
        ("7766479113.35", 5),
        ("21778492192.22", 7),
        ("18078147839.51", 7),
        ("292220176.36", 8),
        ("208523678.23", 9),
    ),
    "gotion-2023fy": _facts(
        ("12910896108.05", 118),
        ("5678694206.58", 118),
        ("31605490020.32", 122),
        ("26257211896.71", 122),
        ("938726847.76", 123),
        ("2418690817.29", 126),
    ),
    "gotion-2024q1": _facts(
        ("15875235802.31", 6),
        ("5438129230.34", 6),
        ("7507913610.08", 7),
        ("6167014491.92", 8),
        ("69137964.65", 9),
        ("72153011.58", 10),
    ),
    "gotion-2024h1": _facts(
        ("17224928781.13", 66),
        ("5369101402.46", 66),
        ("16793872660.65", 71),
        ("13802981718.33", 71),
        ("271142494.62", 72),
        ("180121856.31", 74),
    ),
    "gotion-2024q3": _facts(
        ("19552520549.61", 6),
        ("6267099390.70", 6),
        ("25174850704.11", 8),
        ("20647627469.66", 8),
        ("412341982.84", 9),
        ("243552007.75", 11),
    ),
    "gotion-2024fy": _facts(
        ("16454343330.81", 127),
        ("7121300998.48", 127),
        ("35391817095.44", 132),
        ("29020131352.84", 132),
        ("1206790129.59", 133),
        ("2705571729.01", 135),
    ),
    "sunwoda-2023q3": _facts(
        ("11252905138.10", 8),
        ("8378456988.05", 9),
        ("34318739236.58", 10),
        ("29367616794.18", 10),
        ("803667206.56", 11),
        ("2315163919.49", 13),
    ),
    "sunwoda-2023fy": _facts(
        ("11945783994.65", 128),
        ("7044626788.40", 129),
        ("47862226994.24", 133),
        ("40876301967.08", 133),
        ("1076198343.24", 134),
        ("3618198133.10", 136),
    ),
    "sunwoda-2024q1": _facts(
        ("11464024904.94", 7),
        ("7393058433.21", 7),
        ("10974999651.78", 9),
        ("9162358724.65", 9),
        ("318662277.75", 10),
        ("705856495.31", 11),
    ),
    "sunwoda-2024h1": _facts(
        ("13219630190.74", 62),
        ("7384879099.91", 62),
        ("23918383157.44", 67),
        ("19951377706.84", 67),
        ("823853428.02", 68),
        ("1719337448.67", 70),
    ),
    "sunwoda-2024q3": _facts(
        ("14302478707.44", 8),
        ("8405775565.49", 9),
        ("38278680524.37", 10),
        ("32147830516.05", 10),
        ("1212214585.20", 11),
        ("2616999699.23", 13),
    ),
    "sunwoda-2024fy": _facts(
        ("16079095412.87", 125),
        ("7485085949.50", 125),
        ("56020634117.81", 129),
        ("47518996934.90", 129),
        ("1468240562.81", 130),
        ("3290356813.85", 133),
    ),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _period(period_label: str, metric_code: str) -> dict[str, Any]:
    year = int(period_label[:4])
    fiscal_period = period_label[4:]
    end_by_period = {
        "Q1": f"{year}-03-31",
        "H1": f"{year}-06-30",
        "Q3": f"{year}-09-30",
        "FY": f"{year}-12-31",
    }
    period_end = end_by_period[fiscal_period]
    instant = metric_code in {"accounts_receivable", "inventory"}
    return {
        "period_start": period_end if instant else f"{year}-01-01",
        "period_end": period_end,
        "fiscal_year": year,
        "fiscal_period": fiscal_period,
        "period_basis": "instant" if instant else "ytd",
        "accounting_standard": "CAS",
        "statement_scope": "consolidated",
        "restatement_status": "as_reported",
    }


def _document_type(period_label: str) -> str:
    if period_label.endswith("FY"):
        return "annual_report"
    if period_label.endswith("H1"):
        return "semiannual_report"
    return "quarterly_report"


def _locator(metric_code: str, page: int) -> dict[str, Any]:
    balance = metric_code in {"accounts_receivable", "inventory"}
    cash = metric_code == "operating_cash_flow"
    table = "合并资产负债表" if balance else "合并现金流量表" if cash else "合并利润表"
    row_labels = {
        "accounts_receivable": "应收账款",
        "inventory": "存货",
        "revenue": "营业收入",
        "operating_cost": "营业成本",
        "net_income": "归属于母公司股东/所有者的净利润",
        "operating_cash_flow": "经营活动产生的现金流量净额",
    }
    return {
        "page": page,
        "section": "财务报表",
        "table": table,
        "row_label": row_labels[metric_code],
        "column_label": "报告期末" if balance else "本期/年初至报告期末",
    }


def _verify_raw(spec: DocumentSpec, fact_specs: tuple[FactSpec, ...], raw_dir: Path) -> None:
    pdf_path = raw_dir / spec.raw_path.name
    text_path = raw_dir / spec.text_path.name
    if _sha256(pdf_path) != spec.sha256:
        raise ValueError(f"raw PDF hash mismatch: {pdf_path}")
    text = text_path.read_text(encoding="utf-8")
    parts = re.split(r"===== PDF PAGE (\d+) =====", text)
    pages = {int(parts[index]): parts[index + 1] for index in range(1, len(parts), 2)}
    for fact in fact_specs:
        visible = format(Decimal(fact.reported_value), ",f")
        if visible not in pages.get(fact.page, ""):
            raise ValueError(
                f"{spec.slug}/{fact.metric_code}: {visible} absent on page {fact.page}"
            )


def _source_document(spec: DocumentSpec) -> dict[str, Any]:
    period = _period(spec.period_label, "revenue")
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": spec.document_id,
        "source_id": "source_cninfo",
        "company": COMPANIES[spec.company_key],
        "document_type": _document_type(spec.period_label),
        "title": spec.title,
        "published_at": spec.published_at,
        "available_from": spec.published_at,
        "source_uri": spec.uri,
        "content_hash": spec.sha256,
        "mime_type": "application/pdf",
        "language": "zh-CN",
        "reporting_period": period,
        "license": {
            "license_id": None,
            "publication_mode": "derived_facts_and_short_excerpts",
            "raw_payload_committed": False,
            "notes": (
                "Raw filing excluded. Public package contains normalized factual cells, hashes, "
                "physical-page locators, synthetic evidence, and the official link only."
            ),
        },
        "parser_version": PARSER_VERSION,
        "quality_flags": [
            "sha256_verified",
            "page_text_matched",
            "raw_payload_excluded",
        ],
        "retrieved_at": RETRIEVED_AT,
        "created_at": CREATED_AT,
    }


def _financial_fact(
    spec: DocumentSpec,
    source: dict[str, Any],
    fact: FactSpec,
) -> dict[str, Any]:
    value = Decimal(fact.reported_value) * Decimal(spec.scale)
    fact_id = f"fact_v14_{spec.slug.replace('-', '_')}_{fact.metric_code}"
    return {
        "schema_version": SCHEMA_VERSION,
        "fact_id": fact_id,
        "company": COMPANIES[spec.company_key],
        "metric_code": fact.metric_code,
        "fact_kind": "reported",
        "value": format(value, "f"),
        "currency": "CNY",
        "measurement_unit": "CURRENCY",
        "canonical_scale": 1,
        "sign_convention": "natural_statement_value",
        "period": _period(spec.period_label, fact.metric_code),
        "source": {
            "source_id": "source_cninfo",
            "source_type": "official_filing",
            "document_id": source["document_id"],
            "uri": source["source_uri"],
            "published_at": source["published_at"],
            "retrieved_at": source["retrieved_at"],
            "content_hash": source["content_hash"],
            "license_id": None,
            "redistribution_allowed": False,
        },
        "source_locator": _locator(fact.metric_code, fact.page),
        "availability": "available",
        "quality_flags": ["unit_normalized"],
        "created_at": CREATED_AT,
    }


def _evidence_chunk(source: dict[str, Any], facts: list[dict[str, Any]]) -> dict[str, Any]:
    period = source["reporting_period"]
    lines = [
        "SYNTHETIC PUBLIC EVIDENCE — normalized factual summary; not verbatim filing text.",
        *[f"{fact['metric_code']}: {fact['value']} CNY" for fact in facts],
        "Use the official source URI and physical-page locators for source verification.",
    ]
    content = "\n".join(lines)
    document_id = str(source["document_id"])
    return {
        "schema_version": SCHEMA_VERSION,
        "chunk_id": document_id.replace("doc_", "chunk_") + "_synthetic_financial_summary",
        "document_id": document_id,
        "company": source["company"],
        "reporting_period": period,
        "document_type": (
            "interim_report"
            if source["document_type"] == "semiannual_report"
            else source["document_type"]
        ),
        "published_at": source["published_at"],
        "retrieved_at": source["retrieved_at"],
        "content_role": "untrusted_source",
        "section": "Synthetic normalized financial summary",
        "text": content,
        "text_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "source_uri": source["source_uri"],
        "locator": {
            "page_start": min(fact["source_locator"]["page"] for fact in facts),
            "page_end": max(fact["source_locator"]["page"] for fact in facts),
            "paragraph_start": None,
            "paragraph_end": None,
            "char_start": None,
            "char_end": None,
        },
        "language": "zh-CN",
        "parser_version": PARSER_VERSION,
        "quality_flags": ["table_linearized"],
    }


def _ground_truth(case_id: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    by_metric = {fact["metric_code"]: Decimal(fact["value"]) for fact in facts}
    revenue = by_metric["revenue"]
    cost = by_metric["operating_cost"]
    income = by_metric["net_income"]
    ocf = by_metric["operating_cash_flow"]
    gross_profit = revenue - cost
    conversion = ocf / income if income > 0 else None
    divergence = income > 0 and ocf < 0
    if divergence:
        signal = "positive_profit_negative_ocf"
    elif conversion is not None and conversion < 1:
        signal = "positive_profit_weak_cash_conversion"
    else:
        signal = "positive_profit_positive_ocf"
    return {
        "schema_version": SCHEMA_VERSION,
        "ground_truth_id": f"ground_truth_{case_id}",
        "case_id": case_id,
        "access_class": "verifier_only",
        "fact_hashes": {
            fact["fact_id"]: _canonical_hash(fact)
            for fact in sorted(facts, key=lambda item: item["fact_id"])
        },
        "expected_calculations": {
            "gross_profit": format(gross_profit, "f"),
            "gross_margin": format(gross_profit / revenue, "f"),
            "cash_conversion": None if conversion is None else format(conversion, "f"),
            "profit_cash_divergence": "1" if divergence else "0",
        },
        "required_checks": [
            "operating_cash_flow",
            "accounts_receivable",
            "inventory",
            "cash_conversion",
            "profit_cash_divergence",
            "one_off_contribution",
            "counter_evidence_search",
        ],
        "expected_signal": signal,
        "created_at": CREATED_AT,
    }


def build_primary_package(
    *,
    raw_dir: Path = RAW_DIR,
    output_dir: Path = OUTPUT_DIR,
    private_dir: Path = PRIVATE_DIR,
) -> dict[str, Any]:
    """Build public artifacts and verifier-only ground truth deterministically."""
    if set(FACTS_BY_SLUG) != {spec.slug for spec in DOCUMENTS}:
        raise ValueError("new document and fact specification sets differ")
    for spec in DOCUMENTS:
        _verify_raw(spec, FACTS_BY_SLUG[spec.slug], raw_dir)

    source_dir = output_dir / "source-documents"
    fact_dir = output_dir / "financial-facts"
    chunk_dir = output_dir / "evidence-chunks"
    case_dir = output_dir / "cases"
    ground_truth_dir = private_dir / "ground-truth"
    for directory in (source_dir, fact_dir, chunk_dir, case_dir, ground_truth_dir):
        directory.mkdir(parents=True, exist_ok=True)

    sources: dict[str, dict[str, Any]] = {}
    facts: dict[str, dict[str, Any]] = {}
    for path in sorted((G0_DIR / "source-documents").glob("*.json")):
        source = _load_json(path)
        sources[str(source["document_id"])] = source
        shutil.copy2(path, source_dir / path.name)
    for path in sorted((G0_DIR / "financial-facts").glob("*.json")):
        fact = _load_json(path)
        facts[str(fact["fact_id"])] = fact
        shutil.copy2(path, fact_dir / path.name)

    for spec in DOCUMENTS:
        source = _source_document(spec)
        sources[spec.document_id] = source
        _write_json(source_dir / f"{spec.slug}.json", source)
        for fact_spec in FACTS_BY_SLUG[spec.slug]:
            fact = _financial_fact(spec, source, fact_spec)
            facts[str(fact["fact_id"])] = fact
            _write_json(fact_dir / f"{fact['fact_id']}.json", fact)

    facts_by_document: dict[str, list[dict[str, Any]]] = {}
    for fact in facts.values():
        facts_by_document.setdefault(str(fact["source"]["document_id"]), []).append(fact)
    chunks: dict[str, dict[str, Any]] = {}
    for document_id, document_facts in sorted(facts_by_document.items()):
        chunk = _evidence_chunk(sources[document_id], document_facts)
        chunks[str(chunk["chunk_id"])] = chunk
        _write_json(chunk_dir / f"{chunk['chunk_id']}.json", chunk)

    suite = _load_json(SUITE_PATH)
    source_by_company_period = {
        (
            source["company"]["company_id"],
            f"{source['reporting_period']['fiscal_year']}"
            f"{source['reporting_period']['fiscal_period']}",
        ): source
        for source in sources.values()
    }
    split_cases = [
        (split, case)
        for split in ("evolution", "validation", "final_test")
        for case in suite["splits"][split]
    ]
    ground_truth_hashes: dict[str, str] = {}
    ground_truth_records: dict[str, dict[str, Any]] = {}
    for _split, grouping in split_cases:
        source = source_by_company_period[(grouping["group_key"], grouping["period"])]
        document_facts = facts_by_document[str(source["document_id"])]
        ground_truth = _ground_truth(str(grouping["case_id"]), document_facts)
        path = ground_truth_dir / f"{ground_truth['ground_truth_id']}.json"
        _write_json(path, ground_truth)
        ground_truth_records[str(grouping["case_id"])] = ground_truth
        ground_truth_hashes[str(grouping["case_id"])] = _sha256(path)

    data_hashes: dict[str, str] = {
        f"source:{key}": _canonical_hash(value) for key, value in sources.items()
    }
    data_hashes.update({f"fact:{key}": _canonical_hash(value) for key, value in facts.items()})
    data_hashes.update({f"chunk:{key}": _canonical_hash(value) for key, value in chunks.items()})
    data_hashes.update({f"ground_truth:{key}": value for key, value in ground_truth_hashes.items()})
    data_hashes["preregistered_suite"] = _sha256(SUITE_PATH)
    package_hash = _canonical_hash(data_hashes)

    cases: dict[str, dict[str, Any]] = {}
    for split, grouping in split_cases:
        case_id = str(grouping["case_id"])
        source = source_by_company_period[(grouping["group_key"], grouping["period"])]
        document_id = str(source["document_id"])
        document_facts = sorted(facts_by_document[document_id], key=lambda item: item["fact_id"])
        chunk = next(item for item in chunks.values() if item["document_id"] == document_id)
        published_at = datetime.fromisoformat(str(source["published_at"]))
        ground_truth = ground_truth_records[case_id]
        case = {
            "schema_version": SCHEMA_VERSION,
            "case_id": case_id,
            "benchmark_focus": "earnings_quality",
            "split": split,
            "group_key": grouping["group_key"],
            "company": source["company"],
            "research_question": (
                "该报告期的利润是否转化为高质量经营现金流?请核对应收账款、存货、"
                "现金转化、利润现金背离、一次性贡献和反证。"
            ),
            "research_time": (published_at + timedelta(seconds=1)).isoformat(),
            "target_periods": [source["reporting_period"]],
            "package_id": PACKAGE_ID,
            "package_hash": package_hash,
            "allowed_financial_fact_ids": [fact["fact_id"] for fact in document_facts],
            "allowed_evidence_chunk_ids": [chunk["chunk_id"]],
            "allowed_document_ids": [document_id],
            "verifier_ground_truth_ref": {
                "artifact_id": ground_truth["ground_truth_id"],
                "artifact_hash": ground_truth_hashes[case_id],
                "access_class": "verifier_only",
            },
            "frozen": True,
            "sealed": split == "final_test",
            "created_at": CREATED_AT,
        }
        cases[case_id] = case
        _write_json(case_dir / f"{case_id}.json", case)

    public_artifact_hashes = {
        str(
            path.relative_to(ROOT if output_dir.is_relative_to(ROOT) else output_dir.parent)
        ): _sha256(path)
        for directory in (source_dir, fact_dir, chunk_dir, case_dir)
        for path in sorted(directory.glob("*.json"))
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_id": PACKAGE_ID,
        "package_hash": package_hash,
        "suite_id": suite["suite_id"],
        "preregistered_suite_hash": _sha256(SUITE_PATH),
        "evidence_status": "PREPARED_AWAITING_OWNER_SIGNOFF",
        "formal_run_authorized": False,
        "source_document_count": len(sources),
        "financial_fact_count": len(facts),
        "evidence_chunk_count": len(chunks),
        "case_count": len(cases),
        "split_counts": {
            split: sum(case["split"] == split for case in cases.values())
            for split in ("evolution", "validation", "final_test")
        },
        "company_count": len({case["company"]["company_id"] for case in cases.values()}),
        "metric_codes": sorted({fact["metric_code"] for fact in facts.values()}),
        "mapping_version": MAPPING_VERSION,
        "parser_version": PARSER_VERSION,
        "raw_pdf_committed": False,
        "public_evidence_mode": "synthetic_normalized_fact_summary",
        "ground_truth_committed": False,
        "ground_truth_hashes": ground_truth_hashes,
        "public_artifact_hashes": public_artifact_hashes,
        "representative_visual_review": {
            "status": "completed",
            "sample_size": 4,
            "samples": [
                "catl-2024fy/page-119",
                "eve-2024q3/page-11",
                "gotion-2024h1/page-71",
                "sunwoda-2024fy/page-129",
            ],
        },
        "owner_signoff": {
            "status": "pending",
            "signed_at": None,
            "evidence_file": "docs/evidence/g3-primary-data-signoff.md",
        },
        "limitations": [
            "Public evidence is synthetic normalized factual text, not verbatim filing content.",
            "Ground truth remains verifier-only and is represented publicly by SHA-256 hashes.",
            "This four-company package does not establish full-market coverage or human value.",
        ],
        "created_at": CREATED_AT,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--private-dir", type=Path, default=PRIVATE_DIR)
    args = parser.parse_args()
    manifest = build_primary_package(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        private_dir=args.private_dir,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
