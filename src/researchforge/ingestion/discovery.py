"""Live discovery of official public-company disclosures.

Discovery owns entity resolution and filing metadata only. Financial truth still comes from
verified source artifacts and deterministic extraction.
"""

# ruff: noqa: RUF001 -- issuer names and punctuation are real multilingual inputs.

from __future__ import annotations

import html
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from functools import cached_property
from typing import Any, Literal, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from opencc import OpenCC  # type: ignore[import-untyped]

from researchforge.ingestion.errors import IngestionAbstention

Market = Literal["CN", "US", "HK"]
JsonObject = dict[str, Any]

_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 ResearchForge/1.6",
    "Accept": "application/json,text/plain,*/*",
}


def _provider_label(url: str) -> str:
    host = (urlparse(url).hostname or "official disclosure provider").casefold()
    if "sec.gov" in host:
        return "SEC"
    if "cninfo.com.cn" in host:
        return "CNINFO"
    if "hkexnews.hk" in host:
        return "HKEX"
    return host


def _read_json(request: Request) -> Any:
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        provider = _provider_label(request.full_url)
        raise IngestionAbstention(
            "DISCLOSURE_PROVIDER_UNAVAILABLE",
            "discovery",
            f"{provider} could not be reached safely ({type(exc).__name__}).",
        ) from exc


def _json_get(url: str, *, headers: dict[str, str] | None = None) -> Any:
    return _read_json(Request(url, headers=headers or _BROWSER_HEADERS))


def _json_post(url: str, payload: dict[str, str], *, headers: dict[str, str]) -> Any:
    request = Request(url, data=urlencode(payload).encode(), headers=headers)
    return _read_json(request)


_S2T = OpenCC("s2t")


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value.strip())
    value = re.sub(r"-(?:SW|W|R|S)$", "", value, flags=re.IGNORECASE)
    compact = re.sub(r"[\s.·\-_－（）()]", "", value).casefold()
    suffixes = (
        "股份有限公司",
        "控股有限公司",
        "有限公司",
        "控股集團",
        "控股集团",
        "控股",
        "集團",
        "集团",
        "公司",
        "incorporated",
        "corporation",
        "holdings",
        "limited",
        "corp",
        "inc",
        "ltd",
        "plc",
    )
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            folded = suffix.casefold()
            if compact.endswith(folded) and len(compact) > len(folded):
                compact = compact[: -len(folded)]
                changed = True
                break
    return compact


@dataclass(frozen=True, slots=True)
class ResolvedCompany:
    company_id: str
    legal_name: str
    ticker: str
    exchange: str
    country_code: str
    market: Market
    provider_company_id: str

    def artifact_value(self) -> JsonObject:
        return {
            "company_id": self.company_id,
            "legal_name": self.legal_name,
            "ticker": self.ticker,
            "exchange": self.exchange,
            "country_code": self.country_code,
        }


@dataclass(frozen=True, slots=True)
class DiscoveredFiling:
    provider: str
    filing_id: str
    title: str
    document_type: str
    evidence_document_type: str
    source_uri: str
    published_at: str
    reporting_period: JsonObject
    company: ResolvedCompany

    @property
    def period_label(self) -> str:
        period = self.reporting_period
        return f"{period['fiscal_year']}{period['fiscal_period']}"

    def dynamic_record(self) -> JsonObject:
        filing_token = re.sub(r"[^a-z0-9]+", "-", self.filing_id.casefold()).strip("-")
        slug = (
            f"{self.company.market.lower()}-{self.company.ticker.lower()}-"
            f"{self.period_label.lower()}-{filing_token[-24:]}"
        )
        return {
            "record_id": slug,
            "package_id": f"product_{slug.replace('-', '_')}_live",
            "ingestion_id": f"ingestion_{slug.replace('-', '_')}_live",
            "registry": self.provider,
            "source_id": f"source_{self.provider.lower()}",
            "announcement_id": self.filing_id,
            "document_id": f"doc_{slug.replace('-', '_')}",
            "document_title": self.title,
            "document_type": self.document_type,
            "evidence_document_type": self.evidence_document_type,
            "source_uri": self.source_uri,
            "published_at": self.published_at,
            "reviewed_retrieved_at": datetime.now(UTC).isoformat(),
            "identity_policy": "pin_on_first_acquisition",
            "company": self.company.artifact_value(),
            "reporting_period": self.reporting_period,
        }


class CninfoDiscoveryProvider:
    """Resolve A-share issuers and official CNINFO periodic reports."""

    stock_list_url = "https://www.cninfo.com.cn/new/data/szse_stock.json"
    query_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"

    def resolve(self, query: str) -> ResolvedCompany | None:
        payload = cast(JsonObject, _json_get(self.stock_list_url))
        stocks = cast(list[JsonObject], payload.get("stockList", []))
        needle = query.strip().removesuffix(".SZ").removesuffix(".SH")
        normalized = _normalized(needle)
        exact = [
            item
            for item in stocks
            if str(item.get("code", "")) == needle
            or _normalized(str(item.get("zwjc", ""))) == normalized
        ]
        if not exact and len(normalized) >= 2:
            exact = [
                item for item in stocks if normalized in _normalized(str(item.get("zwjc", "")))
            ]
        if len(exact) != 1:
            return None
        item = exact[0]
        code = str(item["code"])
        exchange = "SSE" if code.startswith(("6", "9")) else "SZSE"
        return ResolvedCompany(
            company_id=f"cn_{code}",
            legal_name=str(item["zwjc"]),
            ticker=code,
            exchange=exchange,
            country_code="CN",
            market="CN",
            provider_company_id=str(item["orgId"]),
        )

    def discover(
        self,
        company: ResolvedCompany,
        *,
        period_label: str | None,
        research_time: datetime,
    ) -> DiscoveredFiling:
        requested_period = period_label or "latest"
        category = self._category(requested_period)
        end_date = research_time.date()
        start_date = end_date.replace(year=max(2000, end_date.year - 4))
        payload = {
            "pageNum": "1",
            "pageSize": "30",
            "column": "szse",
            "tabName": "fulltext",
            "plate": "",
            "stock": f"{company.ticker},{company.provider_company_id}",
            "searchkey": "",
            "secid": "",
            "category": category,
            "trade": "",
            "seDate": f"{start_date.isoformat()}~{end_date.isoformat()}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {
            **_BROWSER_HEADERS,
            "Referer": "https://www.cninfo.com.cn/",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        response = cast(JsonObject, _json_post(self.query_url, payload, headers=headers))
        items = cast(list[JsonObject], response.get("announcements") or [])
        candidates = [item for item in items if self._is_full_report(item, requested_period)]
        if period_label is not None:
            candidates = [
                item for item in candidates if self._period_from_title(item) == period_label
            ]
        if not candidates:
            raise IngestionAbstention(
                "DISCLOSURE_NOT_FOUND",
                "discovery",
                f"No official CNINFO report for {company.ticker}.",
            )
        candidate = max(candidates, key=lambda item: int(item["announcementTime"]))
        resolved_period = self._period_from_title(candidate)
        if resolved_period is None:
            raise IngestionAbstention(
                "PERIOD_UNRESOLVED", "discovery", "Could not resolve filing period."
            )
        return self._filing(company, candidate, resolved_period)

    @staticmethod
    def _category(period_label: str) -> str:
        if period_label == "latest" or period_label.endswith("FY"):
            return "category_ndbg_szsh"
        if period_label.endswith("H1"):
            return "category_bndbg_szsh"
        if period_label.endswith("Q1"):
            return "category_yjdbg_szsh"
        if period_label.endswith("Q3"):
            return "category_sjdbg_szsh"
        raise IngestionAbstention(
            "PERIOD_UNSUPPORTED", "discovery", f"Unsupported period {period_label}."
        )

    @staticmethod
    def _is_full_report(item: JsonObject, requested_period: str) -> bool:
        title = html.unescape(re.sub(r"<[^>]+>", "", str(item.get("announcementTitle", ""))))
        if "摘要" in title or "取消" in title:
            return False
        markers = {
            "FY": "年度报告",
            "H1": "半年度报告",
            "Q1": "第一季度报告",
            "Q3": "第三季度报告",
        }
        suffix = "FY" if requested_period == "latest" else requested_period[-2:]
        return markers.get(suffix, "") in title

    @staticmethod
    def _period_from_title(item: JsonObject) -> str | None:
        title = html.unescape(re.sub(r"<[^>]+>", "", str(item.get("announcementTitle", ""))))
        year_match = re.search(r"(20\d{2})年", title)
        if year_match is None:
            return None
        year = year_match.group(1)
        if "半年度" in title:
            return f"{year}H1"
        if "第一季度" in title:
            return f"{year}Q1"
        if "第三季度" in title:
            return f"{year}Q3"
        if "年度报告" in title:
            return f"{year}FY"
        return None

    @staticmethod
    def _filing(company: ResolvedCompany, item: JsonObject, period_label: str) -> DiscoveredFiling:
        year = int(period_label[:4])
        suffix = period_label[4:]
        month_day = {"FY": (12, 31), "H1": (6, 30), "Q1": (3, 31), "Q3": (9, 30)}[suffix]
        period_end = datetime(year, *month_day).date()
        published = datetime.fromtimestamp(
            int(item["announcementTime"]) / 1000,
            tz=timezone(timedelta(hours=8)),
        )
        relative = str(item["adjunctUrl"]).lstrip("/")
        title = html.unescape(re.sub(r"<[^>]+>", "", str(item["announcementTitle"])))
        return DiscoveredFiling(
            provider="CNINFO",
            filing_id=f"cninfo-{item['announcementId']}",
            title=title,
            document_type={
                "FY": "annual_report",
                "H1": "semiannual_report",
                "Q1": "quarterly_report",
                "Q3": "quarterly_report",
            }[suffix],
            evidence_document_type="annual_report" if suffix == "FY" else "interim_report",
            source_uri=f"https://static.cninfo.com.cn/{relative}",
            published_at=published.isoformat(),
            reporting_period={
                "period_start": f"{year}-01-01",
                "period_end": period_end.isoformat(),
                "fiscal_year": year,
                "fiscal_period": suffix,
                "period_basis": "ytd",
                "accounting_standard": "CAS",
                "statement_scope": "consolidated",
                "restatement_status": "as_reported",
            },
            company=company,
        )


class SecDiscoveryProvider:
    """Resolve US issuers and their latest official SEC periodic filing."""

    tickers_url = "https://www.sec.gov/files/company_tickers.json"

    def resolve(self, query: str) -> ResolvedCompany | None:
        payload = cast(dict[str, JsonObject], _json_get(self.tickers_url, headers=self._headers()))
        needle = query.strip().upper().removesuffix(".US")
        normalized = _normalized(query)
        matches = [
            item
            for item in payload.values()
            if str(item.get("ticker", "")).upper() == needle
            or _normalized(str(item.get("title", ""))) == normalized
        ]
        if not matches and len(normalized) >= 3:
            matches = [
                item
                for item in payload.values()
                if normalized in _normalized(str(item.get("title", "")))
            ]
        if len(matches) != 1:
            return None
        item = matches[0]
        ticker = str(item["ticker"]).upper()
        cik = f"{int(item['cik_str']):010d}"
        return ResolvedCompany(
            company_id=f"us_{ticker.lower()}",
            legal_name=str(item["title"]),
            ticker=ticker,
            exchange="US",
            country_code="US",
            market="US",
            provider_company_id=cik,
        )

    def discover(
        self,
        company: ResolvedCompany,
        *,
        period_label: str | None,
        research_time: datetime,
    ) -> DiscoveredFiling:
        url = f"https://data.sec.gov/submissions/CIK{company.provider_company_id}.json"
        payload = cast(JsonObject, _json_get(url, headers=self._headers()))
        recent = cast(JsonObject, cast(JsonObject, payload["filings"])["recent"])
        forms = cast(list[str], recent["form"])
        accepted = cast(list[str], recent["acceptanceDateTime"])
        filing_dates = cast(list[str], recent["filingDate"])
        reports = cast(list[str], recent["reportDate"])
        accessions = cast(list[str], recent["accessionNumber"])
        primary_docs = cast(list[str], recent["primaryDocument"])
        companyfacts_url = (
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company.provider_company_id}.json"
        )
        companyfacts = cast(JsonObject, _json_get(companyfacts_url, headers=self._headers()))
        candidates: list[tuple[int, str]] = []
        for index, form in enumerate(forms):
            if form not in {"10-K", "10-Q"}:
                continue
            published = datetime.fromisoformat(accepted[index].replace("Z", "+00:00"))
            if published > research_time.astimezone(UTC):
                continue
            candidate_period = self._period_label(
                companyfacts, accessions[index], form, reports[index]
            )
            if period_label is None or period_label == candidate_period:
                candidates.append((index, candidate_period))
        if not candidates:
            raise IngestionAbstention(
                "DISCLOSURE_NOT_FOUND", "discovery", f"No SEC filing for {company.ticker}."
            )
        index, resolved_period = candidates[0]
        accession = accessions[index]
        accession_slug = accession.replace("-", "")
        cik_int = str(int(company.provider_company_id))
        source_uri = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_slug}/{primary_docs[index]}"
        year = int(resolved_period[:4])
        suffix = resolved_period[4:]
        report_end = datetime.fromisoformat(reports[index]).date()
        period_start = f"{report_end.year}-01-01"
        return DiscoveredFiling(
            provider="SEC",
            filing_id=f"sec-{accession}",
            title=f"{company.legal_name} {forms[index]} filed {filing_dates[index]}",
            document_type="annual_report" if forms[index] == "10-K" else "quarterly_report",
            evidence_document_type="annual_report" if forms[index] == "10-K" else "interim_report",
            source_uri=source_uri,
            published_at=datetime.fromisoformat(accepted[index].replace("Z", "+00:00")).isoformat(),
            reporting_period={
                "period_start": period_start,
                "period_end": report_end.isoformat(),
                "fiscal_year": year,
                "fiscal_period": suffix,
                "period_basis": "ytd",
                "accounting_standard": "US_GAAP",
                "statement_scope": "consolidated",
                "restatement_status": "as_reported",
            },
            company=company,
        )

    @staticmethod
    def _period_label(
        companyfacts: JsonObject,
        accession: str,
        form: str,
        report_date: str,
    ) -> str:
        facts = cast(JsonObject, companyfacts.get("facts", {}))
        us_gaap = cast(JsonObject, facts.get("us-gaap", {}))
        for concept in ("NetIncomeLoss", "Revenues", "Assets"):
            fact = cast(JsonObject, us_gaap.get(concept, {}))
            units = cast(JsonObject, fact.get("units", {}))
            for items in units.values():
                for item in cast(list[JsonObject], items):
                    if item.get("accn") != accession:
                        continue
                    fy = item.get("fy")
                    fp = item.get("fp")
                    if isinstance(fy, int) and fp in {"FY", "Q1", "Q2", "Q3"}:
                        return f"{fy}{fp}"
        end_date = datetime.fromisoformat(report_date).date()
        if form == "10-K":
            return f"{end_date.year}FY"
        quarter = {3: "Q1", 6: "Q2", 9: "Q3"}.get(end_date.month, "Q3")
        return f"{end_date.year}{quarter}"

    @staticmethod
    def _headers() -> dict[str, str]:
        user_agent = os.getenv(
            "RESEARCHFORGE_SEC_USER_AGENT",
            "ResearchForge/1.6 researchforge@example.com",
        )
        return {"User-Agent": user_agent, "Accept": "application/json"}


class HkexDiscoveryProvider:
    """Resolve HKEX issuers and official annual/interim report PDFs."""

    stocks_url = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"
    stocks_zh_url = "https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json"
    prefix_url = "https://www1.hkexnews.hk/search/prefix.do"
    search_url = "https://www1.hkexnews.hk/search/titleSearchServlet.do"

    def __init__(self) -> None:
        self._stock_ids: dict[str, str] = {}

    @cached_property
    def english_stocks(self) -> tuple[JsonObject, ...]:
        return tuple(cast(list[JsonObject], _json_get(self.stocks_url)))

    @cached_property
    def chinese_stocks(self) -> tuple[JsonObject, ...]:
        return tuple(cast(list[JsonObject], _json_get(self.stocks_zh_url)))

    def resolve(self, query: str) -> ResolvedCompany | None:
        english = self.english_stocks
        chinese = self.chinese_stocks
        raw = query.strip().upper().removesuffix(".HK")
        code = raw.zfill(5) if raw.isdigit() else None
        normalized = _normalized(raw)
        traditional = _normalized(_S2T.convert(query.strip()))

        tickers: set[str] = set()
        if code is not None:
            tickers = {str(item.get("c")) for item in english if str(item.get("c")) == code}
        else:
            tickers.update(
                str(item.get("c"))
                for item in english
                if _normalized(str(item.get("n", ""))) == normalized
            )
            tickers.update(
                str(item.get("c"))
                for item in chinese
                if _normalized(str(item.get("n", ""))) == traditional
            )
        if not tickers and len(normalized) >= 2:
            tickers.update(
                str(item.get("c"))
                for item in english
                if normalized in _normalized(str(item.get("n", "")))
            )
            tickers.update(
                str(item.get("c"))
                for item in chinese
                if traditional in _normalized(str(item.get("n", "")))
            )
        tickers.discard("None")
        if len(tickers) > 1:
            primary = {ticker for ticker in tickers if ticker.isdigit() and int(ticker) < 10_000}
            if len(primary) == 1:
                tickers = primary
        if len(tickers) != 1:
            return None
        ticker = next(iter(tickers))
        matches = [item for item in english if str(item.get("c")) == ticker]
        if len(matches) != 1:
            return None
        item = matches[0]
        stock_id = self._stock_id(ticker)
        return ResolvedCompany(
            company_id=f"hk_{ticker}",
            legal_name=str(item["n"]),
            ticker=ticker,
            exchange="HKEX",
            country_code="HK",
            market="HK",
            provider_company_id=stock_id,
        )

    def _stock_id(self, ticker: str) -> str:
        cached = self._stock_ids.get(ticker)
        if cached is not None:
            return cached
        params = urlencode(
            {"callback": "callback", "lang": "EN", "type": "A", "name": ticker, "market": "SEHK"}
        )
        request = Request(f"{self.prefix_url}?{params}", headers=_BROWSER_HEADERS)
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
        match = re.search(r'"stockId":(\d+)', raw)
        if match is None:
            raise IngestionAbstention(
                "COMPANY_NOT_FOUND", "discovery", f"HKEX stock id missing for {ticker}."
            )
        stock_id = match.group(1)
        self._stock_ids[ticker] = stock_id
        return stock_id

    def discover(
        self,
        company: ResolvedCompany,
        *,
        period_label: str | None,
        research_time: datetime,
    ) -> DiscoveredFiling:
        end = research_time.date()
        start = end.replace(year=max(2000, end.year - 4))
        params = {
            "sortDir": "1",
            "sortByOptions": "DateTime",
            "category": "0",
            "market": "SEHK",
            "stockId": company.provider_company_id,
            "documentType": "-1",
            "fromDate": start.strftime("%Y%m%d"),
            "toDate": end.strftime("%Y%m%d"),
            "title": "Annual Report"
            if period_label is None or period_label.endswith("FY")
            else "Interim Report",
            "searchType": "1",
            "t1code": "40000",
            "t2Gcode": "-2",
            "t2code": "40100",
            "rowRange": "200",
            "lang": "EN",
        }
        outer = cast(JsonObject, _json_get(f"{self.search_url}?{urlencode(params)}"))
        rows = cast(list[JsonObject], json.loads(str(outer.get("result", "[]"))))
        rows = [row for row in rows if str(row.get("FILE_TYPE", "")).upper() == "PDF"]
        if period_label is not None:
            rows = [row for row in rows if self._period_from_row(row) == period_label]
        if not rows:
            raise IngestionAbstention(
                "DISCLOSURE_NOT_FOUND", "discovery", f"No HKEX report for {company.ticker}."
            )
        row = max(
            rows, key=lambda item: datetime.strptime(str(item["DATE_TIME"]), "%d/%m/%Y %H:%M")
        )
        resolved_period = self._period_from_row(row)
        if resolved_period is None:
            raise IngestionAbstention(
                "PERIOD_UNRESOLVED", "discovery", "Could not resolve HKEX report period."
            )
        year = int(resolved_period[:4])
        suffix = resolved_period[4:]
        period_end = f"{year}-12-31" if suffix == "FY" else f"{year}-06-30"
        published = datetime.strptime(str(row["DATE_TIME"]), "%d/%m/%Y %H:%M").replace(
            tzinfo=timezone(timedelta(hours=8))
        )
        return DiscoveredFiling(
            provider="HKEX",
            filing_id=f"hkex-{row['NEWS_ID']}",
            title=str(row["TITLE"]),
            document_type="annual_report" if suffix == "FY" else "semiannual_report",
            evidence_document_type="annual_report" if suffix == "FY" else "interim_report",
            source_uri=f"https://www1.hkexnews.hk{row['FILE_LINK']}",
            published_at=published.isoformat(),
            reporting_period={
                "period_start": f"{year}-01-01",
                "period_end": period_end,
                "fiscal_year": year,
                "fiscal_period": suffix,
                "period_basis": "ytd",
                "accounting_standard": "IFRS",
                "statement_scope": "consolidated",
                "restatement_status": "as_reported",
            },
            company=company,
        )

    @staticmethod
    def _period_from_row(row: JsonObject) -> str | None:
        title = str(row.get("TITLE", ""))
        year_match = re.search(r"20\d{2}", title)
        if year_match is None:
            return None
        suffix = "H1" if "INTERIM" in title.upper() else "FY"
        return f"{year_match.group(0)}{suffix}"


class OfficialDisclosureDiscovery:
    """Resolve one company across CNINFO, SEC and HKEX without silent guessing."""

    def __init__(self) -> None:
        self.providers = (
            CninfoDiscoveryProvider(),
            SecDiscoveryProvider(),
            HkexDiscoveryProvider(),
        )

    def resolve(self, query: str, *, market_hint: Market | None = None) -> ResolvedCompany:
        providers = [
            p for p in self.providers if market_hint is None or self._market(p) == market_hint
        ]
        matches = [
            match for provider in providers if (match := provider.resolve(query)) is not None
        ]
        unique = {match.company_id: match for match in matches}
        if len(unique) != 1:
            raise IngestionAbstention(
                "COMPANY_NOT_UNAMBIGUOUS",
                "discovery",
                f"Company query {query!r} resolved to {len(unique)} official-market entities.",
            )
        return next(iter(unique.values()))

    def discover(
        self,
        query: str,
        *,
        period_label: str | None,
        research_time: datetime,
        market_hint: Market | None = None,
    ) -> DiscoveredFiling:
        company = self.resolve(query, market_hint=market_hint)
        provider = next(item for item in self.providers if self._market(item) == company.market)
        return provider.discover(company, period_label=period_label, research_time=research_time)

    @staticmethod
    def _market(provider: object) -> Market:
        if isinstance(provider, CninfoDiscoveryProvider):
            return "CN"
        if isinstance(provider, SecDiscoveryProvider):
            return "US"
        return "HK"
