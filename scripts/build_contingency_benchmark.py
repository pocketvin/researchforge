#!/usr/bin/env python3
"""Build the sealed, public-safe 24-case V1.5 contingency Benchmark.

The suite is completely disjoint from the V1.4 primary suite. Raw PDFs and
verifier-only truth remain ignored; committed evidence is synthetic and derived.
Building this package does not authorize activation or any provider request.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from scripts import build_primary_benchmark as common
else:
    import build_primary_benchmark as common

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "v1.5-contingency"
OUTPUT_DIR = ROOT / "data" / "fixtures" / "v1.5-contingency"
PRIVATE_DIR = ROOT / "data" / "private" / "benchmark" / "v1.5-contingency"
SUITE_PATH = ROOT / "benchmark" / "suites" / "v1.5-contingency-preregistered.json"
SCHEMA_VERSION = "1.4.0"
CREATED_AT = "2026-09-01T14:30:00+08:00"
RETRIEVED_AT = "2026-09-01T14:00:00+08:00"
PARSER_VERSION = "1.1.0"
MAPPING_VERSION = "1.1.0"
PACKAGE_ID = "package_v1_5_contingency_battery_earnings_quality"

COMPANIES = {
    "greatpower": {
        "company_id": "cn_300438",
        "legal_name": "广州鹏辉能源科技股份有限公司",
        "ticker": "300438",
        "exchange": "SZSE",
        "country_code": "CN",
    },
    "farasis": {
        "company_id": "cn_688567",
        "legal_name": "孚能科技（赣州）股份有限公司",  # noqa: RUF001
        "ticker": "688567",
        "exchange": "SSE",
        "country_code": "CN",
    },
    "byd": {
        "company_id": "cn_002594",
        "legal_name": "比亚迪股份有限公司",
        "ticker": "002594",
        "exchange": "SZSE",
        "country_code": "CN",
    },
    "cosmx": {
        "company_id": "cn_688772",
        "legal_name": "珠海冠宇电池股份有限公司",
        "ticker": "688772",
        "exchange": "SSE",
        "country_code": "CN",
    },
}


@dataclass(frozen=True, slots=True)
class DocumentSpec:
    slug: str
    company_key: str
    period_label: str
    title: str
    published_date: str
    announcement_id: str
    sha256: str
    scale: int = 1

    @property
    def published_at(self) -> str:
        return f"{self.published_date}T23:59:59+08:00"

    @property
    def uri(self) -> str:
        return (
            f"https://static.cninfo.com.cn/finalpage/{self.published_date}/"
            f"{self.announcement_id}.PDF"
        )

    @property
    def document_id(self) -> str:
        return f"doc_v15_{self.slug.replace('-', '_')}"


def _document(
    slug: str,
    company_key: str,
    period_label: str,
    title: str,
    published_date: str,
    announcement_id: str,
    sha256: str,
    scale: int = 1,
) -> DocumentSpec:
    return DocumentSpec(
        slug,
        company_key,
        period_label,
        title,
        published_date,
        announcement_id,
        sha256,
        scale,
    )


DOCUMENTS = (
    _document(
        "greatpower-2023q3",
        "greatpower",
        "2023Q3",
        "鹏辉能源2023年三季度报告",
        "2023-10-27",
        "1218168059",
        "5fa9dd76a5d9f41afa2bd91cf8e7b9ef38a9c1ab34d4f2d04fd11e85256d8bc5",
    ),
    _document(
        "greatpower-2023fy",
        "greatpower",
        "2023FY",
        "鹏辉能源2023年年度报告",
        "2024-04-27",
        "1219864805",
        "824151efba6a010c2a66a8728ae8c640ad67d9147b8ea891323b12e9cb45422f",
    ),
    _document(
        "greatpower-2024q1",
        "greatpower",
        "2024Q1",
        "鹏辉能源2024年一季度报告",
        "2024-04-27",
        "1219864786",
        "68922b7b0e87a3dcf67090e9e00b875b7f34cc821bc02285b1c0a21adc22933b",
    ),
    _document(
        "greatpower-2024h1",
        "greatpower",
        "2024H1",
        "鹏辉能源2024年半年度报告",
        "2024-08-28",
        "1221004760",
        "c89be8020ac2d50930ba95bbdaba81a210d70264388e6eee31cc1829b3ec1655",
    ),
    _document(
        "greatpower-2024q3",
        "greatpower",
        "2024Q3",
        "鹏辉能源2024年三季度报告",
        "2024-10-25",
        "1221507622",
        "d2cb2b67227585d6f9d080b4179140df58118eb6eed403e8233deaa8634d3f6b",
    ),
    _document(
        "greatpower-2024fy",
        "greatpower",
        "2024FY",
        "鹏辉能源2024年年度报告",
        "2025-04-24",
        "1223245174",
        "8307e390aa10aa3f5d1b3007206cc1a0fd8712cbf3b3a854988c2729639b9e2f",
    ),
    _document(
        "farasis-2023q3",
        "farasis",
        "2023Q3",
        "孚能科技2023年第三季度报告",
        "2023-10-28",
        "1218191393",
        "b940bc01990ceeb84a552b7882d173015394f0741d4e185b2dbd1482caf2c841",
    ),
    _document(
        "farasis-2023fy",
        "farasis",
        "2023FY",
        "孚能科技2023年年度报告全文（更新版）",  # noqa: RUF001
        "2024-06-22",
        "1220427841",
        "ecad88bf1dcd0f119eafb6694906bf54b646202f28d8e58fb578a82df6b7ccb9",
    ),
    _document(
        "farasis-2024q1",
        "farasis",
        "2024Q1",
        "孚能科技2024年第一季度报告",
        "2024-04-30",
        "1219909725",
        "7c632b8e36ed6e4eb902e86db11bedaa15bcbc812be5fd4553fd0ef4a1660a5b",
    ),
    _document(
        "farasis-2024h1",
        "farasis",
        "2024H1",
        "孚能科技2024年半年度报告",
        "2024-08-24",
        "1220962674",
        "1574bc8010b14ee11203f9256909f706063dab8e218e1c19121f5e060500d48e",
    ),
    _document(
        "farasis-2024q3",
        "farasis",
        "2024Q3",
        "孚能科技2024年第三季度报告",
        "2024-10-31",
        "1221573882",
        "79247f6efd744dae929021cc9dbfd4448e6a846668b455e71b99d4cc62dfae7b",
    ),
    _document(
        "farasis-2024fy",
        "farasis",
        "2024FY",
        "孚能科技2024年年度报告",
        "2025-04-30",
        "1223418150",
        "be08441c902d1a8273899b8f97abcbf19a89bcee03c6540dff1b40d3bf50a8d5",
    ),
    _document(
        "byd-2023q3",
        "byd",
        "2023Q3",
        "比亚迪2023年三季度报告",
        "2023-10-31",
        "1218200103",
        "61f893148a6de41d46058ff296a1aa56b733cad49633a001e207d5da2ee55cda",
    ),
    _document(
        "byd-2023fy",
        "byd",
        "2023FY",
        "比亚迪2023年年度报告",
        "2024-03-27",
        "1219412018",
        "959b00a12055470a63962303d90557dca90e84d104d92025aeb70805aa7cc036",
        1000,
    ),
    _document(
        "byd-2024q1",
        "byd",
        "2024Q1",
        "比亚迪2024年一季度报告",
        "2024-04-30",
        "1219909910",
        "1dc4c027549816ddf5d932599bc1b97bd4d35bb022a98c1cf98cdc9528fd1f16",
    ),
    _document(
        "byd-2024h1",
        "byd",
        "2024H1",
        "比亚迪2024年半年度报告",
        "2024-08-29",
        "1221030552",
        "769e9fc195141e7f525d65f0daa308d441c7e39408f0dd584a3722cfc8a306ba",
        1000,
    ),
    _document(
        "byd-2024q3",
        "byd",
        "2024Q3",
        "比亚迪2024年三季度报告",
        "2024-10-31",
        "1221574602",
        "20625a0f315cdcd02f8a87140ffb7053c5519f8f412d88c1d5c9d8d0ab013587",
    ),
    _document(
        "byd-2024fy",
        "byd",
        "2024FY",
        "比亚迪2024年年度报告",
        "2025-03-25",
        "1222881496",
        "e9c2d7fdd088e151ccb6c8ad3d95587b2b014b10f2c9731508d23ce07fde4de3",
        1000,
    ),
    _document(
        "cosmx-2023q3",
        "cosmx",
        "2023Q3",
        "珠海冠宇2023年第三季度报告",
        "2023-10-28",
        "1218190495",
        "81dc856f7ac7d0323c3cfde3162a5839d8b7215882d923c3757eb96209a225bc",
    ),
    _document(
        "cosmx-2023fy",
        "cosmx",
        "2023FY",
        "珠海冠宇2023年年度报告",
        "2024-04-09",
        "1219538336",
        "abff7a3b893a1c6c9551b6ee9ecc51d36cbd6ff2f072ec43c557c1e051ab6799",
    ),
    _document(
        "cosmx-2024q1",
        "cosmx",
        "2024Q1",
        "珠海冠宇2024年第一季度报告",
        "2024-04-23",
        "1219739499",
        "1b9fe9d98ab51306c838bdbfd6271e4ede1cd5000b308ce7ec1ef5995d10baca",
    ),
    _document(
        "cosmx-2024h1",
        "cosmx",
        "2024H1",
        "珠海冠宇2024年半年度报告",
        "2024-08-16",
        "1220880041",
        "a0318082876b630ffc30af2b7d8fa1b4bcddb6be4b58a1a1be11b03924c830e7",
    ),
    _document(
        "cosmx-2024q3",
        "cosmx",
        "2024Q3",
        "珠海冠宇2024年第三季度报告",
        "2024-10-29",
        "1221541861",
        "86801a1179b34085cedd5f9fecfb16f4f867f474ad34363c7441ad56e9d66444",
    ),
    _document(
        "cosmx-2024fy",
        "cosmx",
        "2024FY",
        "珠海冠宇2024年年度报告",
        "2025-03-31",
        "1222962517",
        "82ea9fca3139a97219ea8c1473c58c98acb4a1f7cb982a843ecf6315dd9b6c0b",
    ),
)


def _facts(*rows: tuple[str, int]) -> tuple[common.FactSpec, ...]:
    metrics = (
        "accounts_receivable",
        "inventory",
        "revenue",
        "operating_cost",
        "net_income",
        "operating_cash_flow",
    )
    return tuple(
        common.FactSpec(metric, value, page)
        for metric, (value, page) in zip(metrics, rows, strict=True)
    )


FACTS_BY_SLUG = {
    "greatpower-2023q3": _facts(
        ("1710647195.55", 8),
        ("2929600080.49", 8),
        ("5739444221.27", 9),
        ("4673266908.87", 10),
        ("274656674.74", 11),
        ("410600489.84", 12),
    ),
    "greatpower-2023fy": _facts(
        ("1653695916.28", 82),
        ("3102543766.77", 82),
        ("6932475479.75", 86),
        ("5787790210.50", 86),
        ("43102038.12", 88),
        ("415156740.69", 90),
    ),
    "greatpower-2024q1": _facts(
        ("1906157208.33", 7),
        ("3187784373.90", 8),
        ("1597013711.20", 9),
        ("1407948394.61", 9),
        ("16356922.23", 10),
        ("-90502319.07", 12),
    ),
    "greatpower-2024h1": _facts(
        ("2468192274.12", 41),
        ("2959298759.84", 41),
        ("3773000960.61", 46),
        ("3237214830.10", 46),
        ("41679012.00", 47),
        ("-284728599.50", 49),
    ),
    "greatpower-2024q3": _facts(
        ("2496305199.77", 7),
        ("3087378442.91", 7),
        ("5647856143.46", 9),
        ("4853545572.33", 9),
        ("60502693.44", 10),
        ("-480598493.46", 11),
    ),
    "greatpower-2024fy": _facts(
        ("2600946096.82", 79),
        ("2797950157.09", 79),
        ("7960507262.13", 83),
        ("6941964004.12", 84),
        ("-252455728.32", 85),
        ("-244423466.18", 87),
    ),
    "farasis-2023q3": _facts(
        ("2807737168.60", 6),
        ("4570413708.16", 7),
        ("11231656359.50", 8),
        ("10848075588.01", 8),
        ("-1563176227.95", 9),
        ("341902393.50", 10),
    ),
    "farasis-2023fy": _facts(
        ("3664044675.04", 127),
        ("3598578781.46", 127),
        ("16436419118.50", 131),
        ("15311439904.21", 131),
        ("-1867747324.24", 131),
        ("664030601.12", 135),
    ),
    "farasis-2024q1": _facts(
        ("4119715372.77", 5),
        ("3281928231.27", 5),
        ("2924212373.69", 7),
        ("2576601816.24", 7),
        ("-217296159.17", 7),
        ("-1115950967.03", 9),
    ),
    "farasis-2024h1": _facts(
        ("4354023209.67", 68),
        ("2257580276.90", 68),
        ("6973894596.88", 71),
        ("6033458121.25", 71),
        ("-190363136.25", 72),
        ("-552186771.38", 74),
    ),
    "farasis-2024q3": _facts(
        ("2869627940.39", 6),
        ("2403504862.79", 6),
        ("9211731512.00", 8),
        ("7953339258.79", 8),
        ("-303794290.10", 8),
        ("277325351.98", 9),
    ),
    "farasis-2024fy": _facts(
        ("2702901377.22", 116),
        ("2717591760.47", 116),
        ("11680468636.74", 120),
        ("10358214072.49", 120),
        ("-332059388.86", 120),
        ("908771562.61", 123),
    ),
    "byd-2023q3": _facts(
        ("52970472000.00", 6),
        ("92711639000.00", 6),
        ("422274838000.00", 7),
        ("338726669000.00", 8),
        ("21366896000.00", 8),
        ("97860288000.00", 9),
    ),
    "byd-2023fy": _facts(
        ("61866019", 138),
        ("87676748", 138),
        ("602315354", 140),
        ("480558350", 140),
        ("30040811", 140),
        ("169725025", 144),
    ),
    "byd-2024q1": _facts(
        ("61265729000.00", 6),
        ("98778886000.00", 6),
        ("124944397000.00", 7),
        ("97603387000.00", 7),
        ("4568793000.00", 8),
        ("10227984000.00", 9),
    ),
    "byd-2024h1": _facts(
        ("71814516", 81),
        ("112753013", 81),
        ("301126713", 84),
        ("240859982", 84),
        ("13631257", 84),
        ("14178310", 88),
    ),
    "byd-2024q3": _facts(
        ("79443781000.00", 6),
        ("124358648000.00", 6),
        ("502251312000.00", 7),
        ("397953563000.00", 7),
        ("25238115000.00", 8),
        ("56273315000.00", 9),
    ),
    "byd-2024fy": _facts(
        ("62298988", 142),
        ("116036237", 142),
        ("777102455", 145),
        ("626046616", 145),
        ("40254346", 145),
        ("133453873", 149),
    ),
    "cosmx-2023q3": _facts(
        ("3221983430.96", 6),
        ("2044541691.19", 7),
        ("8540172178.20", 9),
        ("6426314881.33", 9),
        ("289603597.17", 10),
        ("1552028608.91", 12),
    ),
    "cosmx-2023fy": _facts(
        ("2854977139.11", 114),
        ("1950776252.67", 114),
        ("11445622179.58", 118),
        ("8564229576.04", 118),
        ("344189429.16", 119),
        ("2603121617.96", 123),
    ),
    "cosmx-2024q1": _facts(
        ("2442956139.77", 5),
        ("1873592638.53", 6),
        ("2548830423.39", 8),
        ("1920386593.86", 8),
        ("9996303.22", 9),
        ("617841098.63", 11),
    ),
    "cosmx-2024h1": _facts(
        ("2898586246.06", 70),
        ("1758853168.16", 70),
        ("5347209225.01", 74),
        ("4043060682.16", 74),
        ("101787639.74", 75),
        ("836099645.81", 79),
    ),
    "cosmx-2024q3": _facts(
        ("3054812389.03", 7),
        ("1847362551.10", 7),
        ("8517475269.75", 10),
        ("6316803175.77", 10),
        ("267980620.08", 11),
        ("1658419673.63", 13),
    ),
    "cosmx-2024fy": _facts(
        ("3232362652.10", 119),
        ("1892218484.67", 119),
        ("11541072032.26", 123),
        ("8576246223.56", 123),
        ("430354744.97", 124),
        ("2443697179.56", 127),
    ),
}


def _verify_raw(spec: DocumentSpec, facts: tuple[common.FactSpec, ...], raw_dir: Path) -> None:
    pdf_path = raw_dir / f"{spec.slug}.pdf"
    text_path = raw_dir / f"{spec.slug}.txt"
    if common._sha256(pdf_path) != spec.sha256:
        raise ValueError(f"raw PDF hash mismatch: {pdf_path}")
    parts = re.split(r"===== PDF PAGE (\d+) =====", text_path.read_text(encoding="utf-8"))
    pages = {int(parts[index]): parts[index + 1] for index in range(1, len(parts), 2)}
    for fact in facts:
        visible = format(Decimal(fact.reported_value), ",f")
        if visible not in pages.get(fact.page, ""):
            raise ValueError(
                f"{spec.slug}/{fact.metric_code}: {visible} absent on page {fact.page}"
            )


def _source_document(spec: DocumentSpec) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "document_id": spec.document_id,
        "source_id": "source_cninfo",
        "company": COMPANIES[spec.company_key],
        "document_type": common._document_type(spec.period_label),
        "title": spec.title,
        "published_at": spec.published_at,
        "available_from": spec.published_at,
        "source_uri": spec.uri,
        "content_hash": spec.sha256,
        "mime_type": "application/pdf",
        "language": "zh-CN",
        "reporting_period": common._period(spec.period_label, "revenue"),
        "license": {
            "license_id": None,
            "publication_mode": "derived_facts_and_short_excerpts",
            "raw_payload_committed": False,
            "notes": (
                "Raw filing excluded; only normalized facts, hashes, physical-page "
                "locators, synthetic evidence, and official links are public."
            ),
        },
        "parser_version": PARSER_VERSION,
        "quality_flags": ["sha256_verified", "page_text_matched", "raw_payload_excluded"],
        "retrieved_at": RETRIEVED_AT,
        "created_at": CREATED_AT,
    }


def _financial_fact(
    spec: DocumentSpec, source: dict[str, Any], fact: common.FactSpec
) -> dict[str, Any]:
    value = Decimal(fact.reported_value) * Decimal(spec.scale)
    fact_id = f"fact_v15_{spec.slug.replace('-', '_')}_{fact.metric_code}"
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
        "period": common._period(spec.period_label, fact.metric_code),
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
        "source_locator": common._locator(fact.metric_code, fact.page),
        "availability": "available",
        "quality_flags": ["unit_normalized"],
        "created_at": CREATED_AT,
    }


def build_contingency_package(
    *, raw_dir: Path = RAW_DIR, output_dir: Path = OUTPUT_DIR, private_dir: Path = PRIVATE_DIR
) -> dict[str, Any]:
    """Build the immutable public package plus ignored verifier truth."""
    if set(FACTS_BY_SLUG) != {spec.slug for spec in DOCUMENTS}:
        raise ValueError("document and fact specification sets differ")
    for spec in DOCUMENTS:
        _verify_raw(spec, FACTS_BY_SLUG[spec.slug], raw_dir)

    source_dir = output_dir / "source-documents"
    fact_dir = output_dir / "financial-facts"
    chunk_dir = output_dir / "evidence-chunks"
    case_dir = output_dir / "cases"
    truth_dir = private_dir / "ground-truth"
    for directory in (source_dir, fact_dir, chunk_dir, case_dir, truth_dir):
        directory.mkdir(parents=True, exist_ok=True)

    sources: dict[str, dict[str, Any]] = {}
    facts: dict[str, dict[str, Any]] = {}
    for spec in DOCUMENTS:
        source = _source_document(spec)
        sources[spec.document_id] = source
        common._write_json(source_dir / f"{spec.slug}.json", source)
        for fact_spec in FACTS_BY_SLUG[spec.slug]:
            fact = _financial_fact(spec, source, fact_spec)
            facts[str(fact["fact_id"])] = fact
            common._write_json(fact_dir / f"{fact['fact_id']}.json", fact)

    facts_by_document: dict[str, list[dict[str, Any]]] = {}
    for fact in facts.values():
        facts_by_document.setdefault(str(fact["source"]["document_id"]), []).append(fact)
    chunks: dict[str, dict[str, Any]] = {}
    for document_id, document_facts in sorted(facts_by_document.items()):
        chunk = common._evidence_chunk(sources[document_id], document_facts)
        chunks[str(chunk["chunk_id"])] = chunk
        common._write_json(chunk_dir / f"{chunk['chunk_id']}.json", chunk)

    suite = common._load_json(SUITE_PATH)
    split_cases = [
        (split, case)
        for split in ("evolution", "validation", "final_test")
        for case in suite["splits"][split]
    ]
    source_by_company_period = {
        (
            source["company"]["company_id"],
            f"{source['reporting_period']['fiscal_year']}{source['reporting_period']['fiscal_period']}",
        ): source
        for source in sources.values()
    }
    truth_hashes: dict[str, str] = {}
    truth_records: dict[str, dict[str, Any]] = {}
    for _split, grouping in split_cases:
        source = source_by_company_period[(grouping["group_key"], grouping["period"])]
        document_facts = facts_by_document[str(source["document_id"])]
        truth = common._ground_truth(str(grouping["case_id"]), document_facts)
        path = truth_dir / f"{truth['ground_truth_id']}.json"
        common._write_json(path, truth)
        truth_records[str(grouping["case_id"])] = truth
        truth_hashes[str(grouping["case_id"])] = common._sha256(path)

    data_hashes = {f"source:{key}": common._canonical_hash(value) for key, value in sources.items()}
    data_hashes.update(
        {f"fact:{key}": common._canonical_hash(value) for key, value in facts.items()}
    )
    data_hashes.update(
        {f"chunk:{key}": common._canonical_hash(value) for key, value in chunks.items()}
    )
    data_hashes.update({f"ground_truth:{key}": value for key, value in truth_hashes.items()})
    data_hashes["preregistered_suite"] = common._sha256(SUITE_PATH)
    package_hash = common._canonical_hash(data_hashes)

    cases: dict[str, dict[str, Any]] = {}
    for split, grouping in split_cases:
        case_id = str(grouping["case_id"])
        source = source_by_company_period[(grouping["group_key"], grouping["period"])]
        document_id = str(source["document_id"])
        document_facts = sorted(facts_by_document[document_id], key=lambda item: item["fact_id"])
        chunk = next(value for value in chunks.values() if value["document_id"] == document_id)
        published_at = datetime.fromisoformat(str(source["published_at"]))
        truth = truth_records[case_id]
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
                "artifact_id": truth["ground_truth_id"],
                "artifact_hash": truth_hashes[case_id],
                "access_class": "verifier_only",
            },
            "frozen": True,
            "sealed": split == "final_test",
            "created_at": CREATED_AT,
        }
        cases[case_id] = case
        common._write_json(case_dir / f"{case_id}.json", case)

    public_hashes = {
        str(path.relative_to(ROOT)): common._sha256(path)
        for directory in (source_dir, fact_dir, chunk_dir, case_dir)
        for path in sorted(directory.glob("*.json"))
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package_id": PACKAGE_ID,
        "package_hash": package_hash,
        "suite_id": suite["suite_id"],
        "preregistered_suite_hash": common._sha256(SUITE_PATH),
        "evidence_status": "FROZEN_CONTINGENCY_SEALED",
        "formal_run_authorized": False,
        "contingency_activation_authorized": False,
        "sealed_until": suite["sealed_until"],
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
        "ground_truth_hashes": truth_hashes,
        "public_artifact_hashes": public_hashes,
        "representative_visual_review": {
            "status": "completed",
            "sample_size": 4,
            "samples": [
                "greatpower-2024fy/page-84",
                "farasis-2023fy/page-131",
                "byd-2024h1/page-84",
                "cosmx-2024fy/page-124",
            ],
        },
        "limitations": [
            "The package cannot be activated unless primary Validation rejects its Candidate.",
            "Public evidence is synthetic normalized factual text, not verbatim filing content.",
            "Ground truth remains verifier-only and is represented publicly by SHA-256 hashes.",
        ],
        "created_at": CREATED_AT,
    }
    common._write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--private-dir", type=Path, default=PRIVATE_DIR)
    args = parser.parse_args()
    print(
        json.dumps(
            build_contingency_package(
                raw_dir=args.raw_dir, output_dir=args.output_dir, private_dir=args.private_dir
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
