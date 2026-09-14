"""CLI tests for the thin V2 API client."""

from __future__ import annotations

import json

from researchforge import cli


def test_cli_capabilities_reads_v2_api(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_request(base: str, path: str, *, body=None):
        calls.append((base, path, body))
        return {"version": "2.0.0-alpha.1", "provider": "hybrid"}

    monkeypatch.setattr(cli, "_request", fake_request)
    cli.main(["--api-base", "http://test", "capabilities"])
    assert json.loads(capsys.readouterr().out)["provider"] == "hybrid"
    assert calls == [("http://test", "/v2/capabilities", None)]


def test_cli_run_submits_one_v2_request(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_request(base: str, path: str, *, body=None):
        captured.update({"base": base, "path": path, "body": body})
        return {"run_id": "run_cli", "created": True}

    monkeypatch.setattr(cli, "_request", fake_request)
    cli.main(
        [
            "--api-base",
            "http://test",
            "run",
            "宁德时代",
            "分析现金流是否健康",
            "--market",
            "CN",
            "--period",
            "2024H1",
            "--research-time",
            "2026-09-14T00:00:00+08:00",
            "--idempotency-key",
            "cli-v2-test",
        ]
    )
    assert json.loads(capsys.readouterr().out)["run_id"] == "run_cli"
    assert captured["path"] == "/v2/research-runs"
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["company_query"] == "宁德时代"
    assert body["requested_period_label"] == "2024H1"
    assert "research_mode" not in body


def test_cli_show_reads_selected_v2_resource(monkeypatch, capsys) -> None:
    calls: list[str] = []

    def fake_request(base: str, path: str, *, body=None):
        del base, body
        calls.append(path)
        return {"run_id": "run_cli", "report": {"executive_summary": "ok"}}

    monkeypatch.setattr(cli, "_request", fake_request)
    cli.main(["show", "run_cli", "--resource", "result"])
    assert json.loads(capsys.readouterr().out)["report"]["executive_summary"] == "ok"
    assert calls == ["/v2/research-runs/run_cli/result"]
