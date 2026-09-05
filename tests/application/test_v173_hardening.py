from __future__ import annotations

import threading
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from researchforge.adapters.checkpoints import DurableJsonCheckpointSaver
from researchforge.adapters.storage import FileRunRepository
from researchforge.api.app import DEFAULT_PRODUCT_ROOT, DEFAULT_SKILL_MANIFEST
from researchforge.application.autonomous import AutonomousResearchCoordinator
from researchforge.application.budget import BudgetExceededError, BudgetLedger
from researchforge.application.contracts import AutonomousResearchRequest, ResearchRunRequest
from researchforge.application.service import ResearchRunService
from researchforge.ingestion.errors import IngestionAbstention
from tests.runtime_helpers import assert_v173_schema


def _product_service(root: Path, data_root: Path = DEFAULT_PRODUCT_ROOT) -> ResearchRunService:
    return ResearchRunService.build(
        root,
        data_root,
        DEFAULT_SKILL_MANIFEST,
        data_namespace="product",
    )


def _coordinator(
    root: Path,
    *,
    discovery: object | None = None,
) -> AutonomousResearchCoordinator:
    base = _product_service(root)
    return AutonomousResearchCoordinator(
        root,
        lambda package: _product_service(root, package),
        discovery=discovery,  # type: ignore[arg-type]
        reviewed_root=DEFAULT_PRODUCT_ROOT,
        submission_service=base,
    )


def _request(
    *,
    key: str,
    mode: str = "financial_snapshot",
    question: str = "分析经营现金流。",
) -> AutonomousResearchRequest:
    return AutonomousResearchRequest(
        company_query="宁德时代",
        market_hint="CN",
        requested_period_label="2024H1",
        research_mode=mode,  # type: ignore[arg-type]
        research_question=question,
        research_time=datetime.fromisoformat("2026-09-05T20:00:00+08:00"),
        idempotency_key=key,
    )


def test_autonomous_submit_persists_queued_manifest_before_discovery(tmp_path: Path) -> None:
    class MustNotDiscover:
        def discover(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("submit must not contact a disclosure provider")

    coordinator = _coordinator(tmp_path, discovery=MustNotDiscover())
    submission = coordinator.submit(_request(key="v173-queued-before-discovery"))
    manifest = coordinator.submission_service.get_manifest(submission.run_id)  # type: ignore[union-attr]

    assert submission.created is True
    assert manifest["schema_version"] == "1.7.3"
    assert manifest["lifecycle_state"] == "queued"
    assert manifest["configuration"]["dataset_package_id"] is None
    assert manifest["preparation"]["state"] == "queued"
    assert_v173_schema(manifest, "run-manifest.schema.json")


def test_autonomous_queued_run_recovers_with_persisted_company_context(tmp_path: Path) -> None:
    first = _coordinator(tmp_path)
    submission = first.submit(_request(key="v173-recovery-reviewed-cache"))

    second = _coordinator(tmp_path)
    recovered = second.recover_interrupted_runs()
    manifest = second.submission_service.get_manifest(submission.run_id)  # type: ignore[union-attr]

    assert recovered == [submission.run_id]
    assert manifest["lifecycle_state"] == "succeeded"
    assert manifest["input"]["company_ids"] == ["cn_300750"]
    assert manifest["preparation"]["provider"] == "REVIEWED_CACHE"
    assert_v173_schema(manifest, "run-manifest.schema.json")


def test_autonomous_preparation_failure_is_persisted_without_fake_trace(tmp_path: Path) -> None:
    class UnavailableDiscovery:
        def discover(self, *args: object, **kwargs: object) -> object:
            raise IngestionAbstention(
                "DISCLOSURE_PROVIDER_UNAVAILABLE",
                "discovery",
                "Official provider unavailable in bounded test.",
            )

    coordinator = _coordinator(tmp_path, discovery=UnavailableDiscovery())
    submission = coordinator.submit(_request(key="v173-provider-unavailable", mode="general"))
    manifest = coordinator.execute(submission.run_id)

    assert manifest["lifecycle_state"] == "failed"
    assert manifest["artifacts"]["workflow_trace_id"] is None
    assert manifest["failure"]["code"] == "DISCLOSURE_PROVIDER_UNAVAILABLE"
    assert manifest["failure"]["retryable"] is True
    assert manifest["preparation"]["state"] == "failed"
    assert_v173_schema(manifest, "run-manifest.schema.json")


def test_autonomous_cancel_before_discovery_never_contacts_provider(tmp_path: Path) -> None:
    class MustNotDiscover:
        def discover(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("cancelled preparation contacted provider")

    coordinator = _coordinator(tmp_path, discovery=MustNotDiscover())
    submission = coordinator.submit(_request(key="v173-cancel-before-discovery", mode="general"))
    manifest = coordinator.cancel(submission.run_id)
    assert manifest["lifecycle_state"] == "cancelled"
    assert manifest["artifacts"]["workflow_trace_id"] is None
    assert manifest["failure"]["code"] == "CANCELLED_BY_USER"
    assert_v173_schema(manifest, "run-manifest.schema.json")


def test_file_repository_idempotency_is_atomic_across_instances(tmp_path: Path) -> None:
    repositories = [FileRunRepository(tmp_path), FileRunRepository(tmp_path)]
    barrier = threading.Barrier(2)
    outputs: list[tuple[str, bool]] = []
    errors: list[BaseException] = []
    request = {"idempotency_key": "atomic-idempotency", "payload": "same"}

    def worker(index: int) -> None:
        try:
            barrier.wait()
            run_id = f"run_{index:032x}"
            manifest = {"run_id": run_id, "lifecycle_state": "queued"}
            stored, created = repositories[index].create_or_get(request, run_id, manifest)
            outputs.append((stored["run_id"], created))
        except BaseException as exc:  # pragma: no cover - assertion helper
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len({run_id for run_id, _ in outputs}) == 1
    assert sum(created for _, created in outputs) == 1


def test_budget_reservation_is_atomic_across_instances(tmp_path: Path) -> None:
    state = tmp_path / "budget.json"
    ledgers = [BudgetLedger(cap=Decimal("1.00"), state_path=state) for _ in range(2)]
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker(ledger: BudgetLedger) -> None:
        barrier.wait()
        try:
            ledger.reserve(Decimal("0.75"))
        except BudgetExceededError:
            outcomes.append("blocked")
        else:
            outcomes.append("reserved")

    threads = [threading.Thread(target=worker, args=(ledger,)) for ledger in ledgers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["blocked", "reserved"]
    snapshot = BudgetLedger(cap=Decimal("1.00"), state_path=state).snapshot()
    assert snapshot.reserved == Decimal("0.75")


def test_terminal_runs_do_not_accumulate_shared_checkpoint_state(tmp_path: Path) -> None:
    services = [_product_service(tmp_path), _product_service(tmp_path)]
    run_ids: list[str] = []
    for index, service in enumerate(services):
        request = ResearchRunRequest(
            task_type="filing_analysis",
            research_question="分析经营现金流。",
            company_ids=["cn_300750"],
            requested_period_labels=["2024H1"],
            research_time=datetime.fromisoformat("2026-09-05T20:00:00+08:00"),
            idempotency_key=f"v173-concurrent-workflow-{index}",
        )
        run_ids.append(service.submit(request).run_id)

    threads = [
        threading.Thread(target=service.execute, args=(run_id,))
        for service, run_id in zip(services, run_ids, strict=True)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    states = [
        service.get_manifest(run_id)["lifecycle_state"]
        for service, run_id in zip(services, run_ids, strict=True)
    ]
    assert states == ["succeeded", "succeeded"]
    saver = DurableJsonCheckpointSaver(
        tmp_path / "checkpoints" / "langgraph-checkpoints-v1.7.3.json"
    )
    assert list(saver.storage) == []
