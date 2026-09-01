"""CLI smoke tests over the same lifecycle service."""

from __future__ import annotations

import json
from pathlib import Path

from researchforge.api.app import PROJECT_ROOT
from researchforge.cli import main
from tests.runtime_helpers import assert_v14_schema

EXPECTED_CATL_2024H1 = {
    "cash_conversion": "1.955345691552841179348299138",
    "gross_margin": "0.2653344423755971583069020985",
    "gross_profit": "44248984800.00",
    "profit_cash_divergence": "0",
}


def test_cli_run_outputs_persisted_bundle(tmp_path: Path, capsys: object) -> None:
    from _pytest.capture import CaptureFixture

    capture = capsys
    assert isinstance(capture, CaptureFixture)
    main(
        [
            "--artifact-root",
            str(tmp_path),
            "run",
            "--company",
            "cn_300750",
            "--period",
            "2024H1",
            "--question",
            "利润是否转化为现金流?",
            "--research-time",
            "2024-08-01T00:00:00+08:00",
            "--idempotency-key",
            "cli-catl-2024h1",
        ]
    )

    payload = json.loads(capture.readouterr().out)
    assert payload["manifest"]["lifecycle_state"] == "succeeded"
    assert payload["result"]["task_type"] == "filing_analysis"
    assert len(payload["trace"]["stages"]) == 10


def test_cli_verify_persists_schema_evaluation(tmp_path: Path, capsys: object) -> None:
    from _pytest.capture import CaptureFixture

    capture = capsys
    assert isinstance(capture, CaptureFixture)
    main(
        [
            "--artifact-root",
            str(tmp_path),
            "run",
            "--company",
            "cn_300750",
            "--period",
            "2024H1",
            "--question",
            "利润是否转化为现金流?",
            "--research-time",
            "2024-08-01T00:00:00+08:00",
            "--idempotency-key",
            "cli-verify-catl-2024h1",
        ]
    )
    run_payload = json.loads(capture.readouterr().out)
    run_id = run_payload["manifest"]["run_id"]
    expected_file = tmp_path / "expected.json"
    expected_file.write_text(
        json.dumps(EXPECTED_CATL_2024H1),
        encoding="utf-8",
    )

    main(
        [
            "--artifact-root",
            str(tmp_path),
            "verify",
            run_id,
            "--case-id",
            "golden_g0_catl_2024h1_cli",
            "--expected-calculations",
            str(expected_file),
        ]
    )
    evaluation = json.loads(capture.readouterr().out)

    assert evaluation["metrics"]["task_score"] == 1.0
    assert evaluation["failure_events"] == []


def test_cli_preregisters_primary_grouping_without_consuming_final_test(
    tmp_path: Path, capsys: object
) -> None:
    from _pytest.capture import CaptureFixture

    capture = capsys
    assert isinstance(capture, CaptureFixture)
    main(
        [
            "--artifact-root",
            str(tmp_path),
            "evolution-preregister",
            "--experiment-id",
            "experiment_primary_preregistered",
            "--suite",
            str(PROJECT_ROOT / "benchmark" / "suites" / "v1.4-primary-preregistered.json"),
        ]
    )
    experiment = json.loads(capture.readouterr().out)

    assert_v14_schema(experiment, "evolution-experiment.schema.json")
    assert experiment["status"] == "preregistered"
    assert experiment["outcome"] == "PENDING"
    assert experiment["final_test_consumed"] is False
    assert {split: len(cases) for split, cases in experiment["split_case_ids"].items()} == {
        "evolution": 12,
        "validation": 6,
        "final_test": 6,
    }

    main(
        [
            "--artifact-root",
            str(tmp_path),
            "evolution-show",
            "experiment_primary_preregistered",
        ]
    )
    assert json.loads(capture.readouterr().out) == experiment


def test_cli_simulated_usability_preflight_never_contacts_provider(
    tmp_path: Path, capsys: object, monkeypatch: object
) -> None:
    from _pytest.capture import CaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

    capture = capsys
    patcher = monkeypatch
    assert isinstance(capture, CaptureFixture)
    assert isinstance(patcher, MonkeyPatch)
    patcher.delenv("OPENAI_API_KEY", raising=False)
    patcher.delenv("RESEARCHFORGE_ROTATED_KEY_CONFIRMED", raising=False)
    main(
        [
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "run",
            "--company",
            "cn_300750",
            "--period",
            "2024H1",
            "--question",
            "利润是否转化为现金流?",
            "--research-time",
            "2024-08-01T00:00:00+08:00",
            "--idempotency-key",
            "cli-simulated-usability-source",
        ]
    )
    run_id = json.loads(capture.readouterr().out)["manifest"]["run_id"]
    screenshots = []
    for name in ("research", "skill-lab"):
        path = tmp_path / f"{name}.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\ncli-test")
        screenshots.append(path)

    main(
        [
            "--artifact-root",
            str(tmp_path / "artifacts"),
            "usability-preflight",
            "--run-id",
            run_id,
            "--research-screenshot",
            str(screenshots[0]),
            "--skill-lab-screenshot",
            str(screenshots[1]),
        ]
    )
    report = json.loads(capture.readouterr().out)

    assert report["status"] == "BLOCKED"
    assert report["provider_contacted"] is False
    assert report["evidence_label"] == "SIMULATED"
