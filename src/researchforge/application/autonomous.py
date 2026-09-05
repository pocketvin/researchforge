# ruff: noqa: RUF001 -- issuer names include real CJK punctuation.

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.storage import FileRunRepository, canonical_json_bytes
from researchforge.application.contracts import (
    AutonomousResearchRequest,
    ResearchRunRequest,
    RunSubmission,
)
from researchforge.application.service import (
    ResearchRunService,
    UnsupportedCapabilityError,
    enforce_research_question_policy,
)
from researchforge.file_lock import exclusive_file_lock
from researchforge.ingestion.discovery import (
    DiscoveredFiling,
    Market,
    OfficialDisclosureDiscovery,
    ResolvedCompany,
)
from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.hk_ifrs import HkIfrsProductIngestion
from researchforge.ingestion.pipeline import FilingRegistry, ProductDisclosureIngestion
from researchforge.ingestion.sec_xbrl import SecXbrlProductIngestion

JsonObject = dict[str, Any]
ServiceFactory = Callable[[Path], ResearchRunService]
V17_EVIDENCE_INDEX_VERSION = "1.1.0"
_TERMINAL_STATES = {"succeeded", "insufficient_data", "failed", "cancelled", "timed_out"}


def _entity_key(value: str) -> str:
    compact = re.sub(r"[\s.·\-_（）()]", "", value).casefold()
    for suffix in ("股份有限公司", "控股有限公司", "有限公司", "控股集团", "集团", "公司"):
        compact = compact.replace(suffix, "")
    return compact


def _period_label(period: JsonObject) -> str:
    return f"{period['fiscal_year']}{period['fiscal_period']}"


class AutonomousPreparationInterrupted(RuntimeError):
    def __init__(self, terminal_state: str, failure_code: str) -> None:
        super().__init__(failure_code)
        self.terminal_state = terminal_state
        self.failure_code = failure_code


class AutonomousResearchCoordinator:
    """Persist, prepare, execute, and recover one autonomous company research run."""

    def __init__(
        self,
        artifact_root: Path,
        service_factory: ServiceFactory,
        *,
        discovery: OfficialDisclosureDiscovery | None = None,
        reviewed_root: Path | None = None,
        submission_service: ResearchRunService | None = None,
    ) -> None:
        self.artifact_root = artifact_root.resolve()
        self.service_factory = service_factory
        self.discovery = discovery or OfficialDisclosureDiscovery()
        self.reviewed_root = reviewed_root.resolve() if reviewed_root is not None else None
        self.submission_service = submission_service
        self.live_root = self.artifact_root / "live-data"
        self.context_root = self.artifact_root / "autonomous-context"
        self.context_root.mkdir(parents=True, exist_ok=True)
        self._context_lock = self.context_root / ".contexts.lock"

    def _resolved_request(
        self,
        request: AutonomousResearchRequest,
        filing: DiscoveredFiling,
    ) -> ResearchRunRequest:
        return ResearchRunRequest(
            task_type=(
                "filing_analysis"
                if request.research_mode == "financial_snapshot"
                else "company_research"
            ),
            research_question=request.research_question,
            company_ids=[filing.company.company_id],
            requested_period_labels=[filing.period_label],
            research_time=request.research_time,
            idempotency_key=request.idempotency_key,
        )

    def _resolve_package(
        self,
        request: AutonomousResearchRequest,
        *,
        should_cancel: Callable[[], bool] = lambda: False,
        deadline: float | None = None,
    ) -> tuple[ResearchRunService, DiscoveredFiling, Path, ResearchRunRequest]:
        def check_boundary() -> None:
            if should_cancel():
                raise AutonomousPreparationInterrupted("cancelled", "CANCELLED_BY_USER")
            if deadline is not None and time.monotonic() >= deadline:
                raise AutonomousPreparationInterrupted("timed_out", "TIMED_OUT")

        check_boundary()
        reviewed = (
            self._reviewed_package(request)
            if request.research_mode == "financial_snapshot"
            else None
        )
        if reviewed is None:
            filing = self.discovery.discover(
                request.company_query,
                period_label=request.requested_period_label,
                research_time=request.research_time,
                market_hint=request.market_hint,
            )
            check_boundary()
            record = filing.dynamic_record()
            if request.research_mode == "financial_snapshot":
                package_root = self.live_root / "packages" / str(record["record_id"])
            else:
                index_tag = V17_EVIDENCE_INDEX_VERSION.replace(".", "-")
                package_root = (
                    self.live_root / "v17-packages" / f"{record['record_id']}-evidence-{index_tag}"
                )
            self._ensure_package(record, filing, package_root)
        else:
            package_root, filing = reviewed
        check_boundary()
        service = self.service_factory(package_root)
        return service, filing, package_root, self._resolved_request(request, filing)

    def prepare(
        self,
        request: AutonomousResearchRequest,
    ) -> tuple[ResearchRunService, RunSubmission, DiscoveredFiling]:
        """Synchronous compatibility path used by regression and developer tooling."""
        enforce_research_question_policy(request.research_question)
        service, filing, package_root, standard_request = self._resolve_package(request)
        submission = service.submit(standard_request)
        self._write_context(
            submission.run_id,
            request,
            package_root=package_root,
            resolved_request=standard_request,
            filing=filing,
        )
        return service, submission, filing

    def _pending_request(self, request: AutonomousResearchRequest) -> ResearchRunRequest:
        market = (request.market_hint or "AUTO").casefold()
        digest = hashlib.sha256(request.company_query.strip().encode("utf-8")).hexdigest()[:16]
        return ResearchRunRequest(
            task_type=(
                "filing_analysis"
                if request.research_mode == "financial_snapshot"
                else "company_research"
            ),
            research_question=request.research_question,
            company_ids=[f"pending_{market}_{digest}"],
            requested_period_labels=[request.requested_period_label or "LATEST"],
            research_time=request.research_time,
            idempotency_key=request.idempotency_key,
        )

    def submit(self, request: AutonomousResearchRequest) -> RunSubmission:
        """Persist a run before network discovery so the HTTP request can return immediately."""
        enforce_research_question_policy(request.research_question)
        if self.submission_service is None:
            raise RuntimeError("autonomous background submission requires a lifecycle service")
        submission = self.submission_service.submit(self._pending_request(request))
        if submission.created:
            manifest = self.submission_service.get_manifest(submission.run_id)
            pending = {
                **manifest,
                "schema_version": "1.7.3",
                "autonomous_request": request.model_dump(mode="json"),
                "preparation": {
                    "state": "queued",
                    "stage": "discovery",
                    "provider": None,
                    "filing_id": None,
                    "message": "Awaiting official-source discovery.",
                },
                "configuration": {
                    **manifest["configuration"],
                    "dataset_package_id": None,
                    "dataset_package_hash": None,
                },
            }
            self.submission_service.persist_manifest(submission.run_id, pending)
        self._write_context(submission.run_id, request)
        return submission

    def execute(self, run_id: str) -> JsonObject:
        """Discover, ingest, bind the resolved package, then execute the Research graph."""
        lock_path = self.artifact_root / "autonomous-run-locks" / f"{run_id}.lock"
        with exclusive_file_lock(lock_path):
            return self._execute_locked(run_id)

    def _execute_locked(self, run_id: str) -> JsonObject:
        if self.submission_service is None:
            raise RuntimeError("autonomous execution requires a lifecycle service")
        repository = self.submission_service.repository
        manifest = repository.get_manifest(run_id)
        if manifest["lifecycle_state"] in _TERMINAL_STATES:
            return manifest
        context = self._read_context(run_id)
        request = AutonomousResearchRequest.model_validate(context["request"])
        now = datetime.now(UTC)
        started_at = manifest.get("started_at") or now.isoformat()
        elapsed = max(0.0, (now - datetime.fromisoformat(started_at)).total_seconds())
        remaining_total = max(0.0, float(manifest["limits"]["timeout_seconds"]) - elapsed)
        deadline = time.monotonic() + remaining_total
        running = {
            **manifest,
            "lifecycle_state": "running",
            "started_at": started_at,
            "preparation": {
                **manifest.get("preparation", {}),
                "state": "running",
                "stage": "discovery",
                "message": "Discovering and verifying official disclosure data.",
            },
        }
        self.submission_service.persist_manifest(run_id, running)

        def should_cancel() -> bool:
            return repository.is_cancel_requested(run_id)

        try:
            package_value = context.get("package_root")
            resolved_value = context.get("resolved_request")
            filing_value = context.get("filing")
            if package_value and resolved_value and filing_value:
                package_root = self._validated_context_package(Path(str(package_value)))
                service = self.service_factory(package_root)
                standard_request = ResearchRunRequest.model_validate(resolved_value)
                filing = self._context_filing(filing_value)
            else:
                service, filing, package_root, standard_request = self._resolve_package(
                    request, should_cancel=should_cancel, deadline=deadline
                )
                self._write_context(
                    run_id,
                    request,
                    package_root=package_root,
                    resolved_request=standard_request,
                    filing=filing,
                )
            if should_cancel():
                raise AutonomousPreparationInterrupted("cancelled", "CANCELLED_BY_USER")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AutonomousPreparationInterrupted("timed_out", "TIMED_OUT")
        except IngestionAbstention as exc:
            return self._finish_preparation_failure(run_id, running, exc)
        except AutonomousPreparationInterrupted as exc:
            return self._finish_preparation_interrupted(run_id, running, exc)
        except UnsupportedCapabilityError as exc:
            failure = IngestionAbstention("UNSUPPORTED_TASK", "planning", str(exc))
            return self._finish_preparation_failure(run_id, running, failure)

        service.adopt_existing_run(
            run_id,
            standard_request,
            running,
            extensions={
                "autonomous_request": request.model_dump(mode="json"),
                "preparation": {
                    "state": "completed",
                    "stage": "ready",
                    "provider": filing.provider,
                    "filing_id": filing.filing_id,
                    "message": "Official disclosure package is verified and bound to this run.",
                },
            },
        )
        remaining = max(1.0, deadline - time.monotonic())
        return service.execute(run_id, timeout_seconds=remaining)

    def _context_path(self, run_id: str) -> Path:
        if re.fullmatch(r"run_[0-9a-f]{32}", run_id) is None:
            raise ValueError("invalid autonomous run id")
        return self.context_root / f"{run_id}.json"

    def _read_context(self, run_id: str) -> JsonObject:
        value = json.loads(self._context_path(run_id).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("autonomous run context must be a JSON object")
        return cast(JsonObject, value)

    def _write_context(
        self,
        run_id: str,
        request: AutonomousResearchRequest,
        *,
        package_root: Path | None = None,
        resolved_request: ResearchRunRequest | None = None,
        filing: DiscoveredFiling | None = None,
    ) -> None:
        path = self._context_path(run_id)
        with exclusive_file_lock(self._context_lock):
            existing: JsonObject = (
                json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            )
            request_value = request.model_dump(mode="json")
            if existing.get("request") is not None and existing["request"] != request_value:
                raise RuntimeError("autonomous run context changed after submission")
            payload: JsonObject = {
                "schema_version": "1.7.3",
                "run_id": run_id,
                "request": request_value,
                "package_root": existing.get("package_root"),
                "resolved_request": existing.get("resolved_request"),
                "filing": existing.get("filing"),
            }
            if package_root is not None:
                payload["package_root"] = str(package_root.resolve())
            if resolved_request is not None:
                payload["resolved_request"] = resolved_request.model_dump(mode="json")
            if filing is not None:
                payload["filing"] = self._filing_context(filing)
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self.context_root, prefix=f".{run_id}."
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(canonical_json_bytes(payload))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, 0o600)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _filing_context(filing: DiscoveredFiling) -> JsonObject:
        return {
            "provider": filing.provider,
            "filing_id": filing.filing_id,
            "title": filing.title,
            "document_type": filing.document_type,
            "evidence_document_type": filing.evidence_document_type,
            "source_uri": filing.source_uri,
            "published_at": filing.published_at,
            "reporting_period": filing.reporting_period,
            "company": filing.company.artifact_value(),
        }

    @staticmethod
    def _context_filing(value: JsonObject) -> DiscoveredFiling:
        company = value["company"]
        country = str(company["country_code"])
        market: Market = "CN" if country == "CN" else "HK" if country == "HK" else "US"
        return DiscoveredFiling(
            provider=str(value["provider"]),
            filing_id=str(value["filing_id"]),
            title=str(value["title"]),
            document_type=str(value["document_type"]),
            evidence_document_type=str(value["evidence_document_type"]),
            source_uri=str(value["source_uri"]),
            published_at=str(value["published_at"]),
            reporting_period=dict(value["reporting_period"]),
            company=ResolvedCompany(
                company_id=str(company["company_id"]),
                legal_name=str(company["legal_name"]),
                ticker=str(company["ticker"]),
                exchange=str(company["exchange"]),
                country_code=country,
                market=market,
                provider_company_id=str(company["company_id"]),
            ),
        )

    def managed_run_ids(self) -> set[str]:
        return {path.stem for path in self.context_root.glob("run_*.json")}

    def cancel(self, run_id: str) -> JsonObject:
        """Cancel an autonomous run without inventing a graph trace before preparation."""
        if self.submission_service is None:
            raise RuntimeError("autonomous cancellation requires a lifecycle service")
        repository = self.submission_service.repository
        manifest = repository.get_manifest(run_id)
        if manifest["lifecycle_state"] in {
            "succeeded",
            "insufficient_data",
            "failed",
            "cancelled",
            "timed_out",
        }:
            return manifest
        repository.request_cancel(run_id)
        if manifest["lifecycle_state"] != "queued":
            return manifest
        lock_path = self.artifact_root / "autonomous-run-locks" / f"{run_id}.lock"
        with exclusive_file_lock(lock_path):
            current = repository.get_manifest(run_id)
            if current["lifecycle_state"] in {
                "succeeded",
                "insufficient_data",
                "failed",
                "cancelled",
                "timed_out",
            }:
                return current
            return self._finish_preparation_interrupted(
                run_id,
                current,
                AutonomousPreparationInterrupted("cancelled", "CANCELLED_BY_USER"),
            )

    def recover_interrupted_runs(self) -> list[str]:
        """Resume queued/running autonomous runs from preparation or graph checkpoints."""
        repository = FileRunRepository(self.artifact_root)
        recovered: list[str] = []
        for run_id in sorted(self.managed_run_ids()):
            try:
                manifest = repository.get_manifest(run_id)
            except KeyError:
                continue
            if manifest["lifecycle_state"] not in {"queued", "running"}:
                continue
            self.execute(run_id)
            recovered.append(run_id)
        return recovered

    def _validated_context_package(self, package_root: Path) -> Path:
        resolved = package_root.resolve()
        allowed = [self.artifact_root]
        if self.reviewed_root is not None:
            allowed.append(self.reviewed_root)
        if not any(resolved == root or root in resolved.parents for root in allowed):
            raise ValueError("autonomous recovery package escapes approved roots")
        if not (resolved / "manifest.json").is_file():
            raise ValueError("autonomous recovery package is unavailable")
        return resolved

    def _finish_preparation_failure(
        self,
        run_id: str,
        manifest: JsonObject,
        exc: IngestionAbstention,
    ) -> JsonObject:
        if self.submission_service is None:
            raise RuntimeError("autonomous execution requires a lifecycle service")
        retryable = exc.code == "DISCLOSURE_PROVIDER_UNAVAILABLE"
        terminal_state = "failed" if retryable else "insufficient_data"
        finished = {
            **manifest,
            "lifecycle_state": terminal_state,
            "finished_at": datetime.now(UTC).isoformat(),
            "preparation": {
                **manifest.get("preparation", {}),
                "state": "failed",
                "stage": exc.stage,
                "message": exc.reason,
            },
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0,
                "tool_calls": 0,
                "estimated_cost": 0,
                "cost_currency": "USD",
            },
            "failure": {
                "code": exc.code,
                "message": exc.reason,
                "retryable": retryable,
                "stage": exc.stage,
            },
        }
        self.submission_service.persist_manifest(run_id, finished)
        return finished

    def _finish_preparation_interrupted(
        self,
        run_id: str,
        manifest: JsonObject,
        exc: AutonomousPreparationInterrupted,
    ) -> JsonObject:
        if self.submission_service is None:
            raise RuntimeError("autonomous execution requires a lifecycle service")
        message = (
            "The run was cancelled during official-source preparation."
            if exc.terminal_state == "cancelled"
            else "The run exceeded its total autonomous research deadline during preparation."
        )
        finished = {
            **manifest,
            "lifecycle_state": exc.terminal_state,
            "finished_at": datetime.now(UTC).isoformat(),
            "preparation": {
                **manifest.get("preparation", {}),
                "state": exc.terminal_state,
                "stage": "preparation",
                "message": message,
            },
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_ms": 0,
                "tool_calls": 0,
                "estimated_cost": 0,
                "cost_currency": "USD",
            },
            "failure": {
                "code": exc.failure_code,
                "message": message,
                "retryable": False,
                "stage": "preparation",
            },
        }
        self.submission_service.persist_manifest(run_id, finished)
        return finished

    def _reviewed_package(
        self,
        request: AutonomousResearchRequest,
    ) -> tuple[Path, DiscoveredFiling] | None:
        if self.reviewed_root is None or request.requested_period_label is None:
            return None
        candidates: list[tuple[Path, DiscoveredFiling]] = []
        for package_root in sorted(self.reviewed_root.iterdir()):
            if not package_root.is_dir() or not (package_root / "manifest.json").is_file():
                continue
            sources = sorted((package_root / "source-documents").glob("*.json"))
            if len(sources) != 1:
                continue
            source = json.loads(sources[0].read_text(encoding="utf-8"))
            period = source.get("reporting_period")
            company = source.get("company")
            if not isinstance(period, dict) or not isinstance(company, dict):
                continue
            if _period_label(period) != request.requested_period_label:
                continue
            filing = self._cached_filing(source, period, company)
            if request.market_hint is not None and filing.company.market != request.market_hint:
                continue
            if datetime.fromisoformat(filing.published_at) > request.research_time:
                continue
            if self._matches_query(request.company_query, filing.company):
                candidates.append((package_root, filing))
        if len(candidates) > 1:
            raise IngestionAbstention(
                "COMPANY_NOT_UNAMBIGUOUS",
                "discovery",
                "Reviewed package cache matched more than one company package.",
            )
        return candidates[0] if candidates else None

    @staticmethod
    def _matches_query(query: str, company: ResolvedCompany) -> bool:
        raw = query.strip().casefold()
        if raw in {company.ticker.casefold(), company.company_id.casefold()}:
            return True
        needle = _entity_key(query)
        legal = _entity_key(company.legal_name)
        return bool(needle) and (needle == legal or (len(needle) >= 2 and needle in legal))

    @staticmethod
    def _cached_filing(
        source: JsonObject,
        period: JsonObject,
        company: JsonObject,
    ) -> DiscoveredFiling:
        country = str(company["country_code"])
        market: Market = "CN" if country == "CN" else "HK" if country == "HK" else "US"
        resolved = ResolvedCompany(
            company_id=str(company["company_id"]),
            legal_name=str(company["legal_name"]),
            ticker=str(company["ticker"]),
            exchange=str(company["exchange"]),
            country_code=country,
            market=market,
            provider_company_id=str(company["company_id"]),
        )
        document_type = str(source.get("document_type", "annual_report"))
        return DiscoveredFiling(
            provider="REVIEWED_CACHE",
            filing_id=f"cache-{source['document_id']}",
            title=str(source["title"]),
            document_type=document_type,
            evidence_document_type=document_type,
            source_uri=str(source["source_uri"]),
            published_at=str(source["published_at"]),
            reporting_period=period,
            company=resolved,
        )

    def _ensure_package(
        self,
        record: JsonObject,
        filing: DiscoveredFiling,
        package_root: Path,
    ) -> None:
        if (package_root / "manifest.json").is_file():
            return
        if filing.company.market == "US":
            SecXbrlProductIngestion().run(filing, package_root=package_root)
            return
        if filing.company.market == "HK":
            HkIfrsProductIngestion().run(filing, package_root=package_root)
            return
        registry_root = self.live_root / "registries"
        registry_root.mkdir(parents=True, exist_ok=True)
        registry_path = registry_root / f"{record['record_id']}.json"
        registry_payload = {
            "schema_version": "1.5.0",
            "data_namespace": "product",
            "records": [record],
        }
        registry_path.write_text(
            json.dumps(registry_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ingestion = ProductDisclosureIngestion(FilingRegistry(registry_path))
        manifest = ingestion.run(
            company_id=filing.company.company_id,
            period_label=filing.period_label,
            raw_root=self.live_root / "raw",
            package_root=package_root,
        )
        if manifest["status"] != "ready":
            abstentions = manifest.get("abstentions") or []
            reason = abstentions[0] if abstentions else {"message": "Unknown ingestion abstention"}
            raise IngestionAbstention(
                str(reason.get("code", "LIVE_INGESTION_ABSTAINED")),
                str(reason.get("stage", "ingestion")),
                str(reason.get("reason", "Live official filing could not be normalized.")),
            )
