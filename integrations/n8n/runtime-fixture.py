"""Test-only transport backend. Never serves a financial fact, calculation or report."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

RUN_ID = "run_" + "f" * 32
scenario = "failed"
polls = 0


class Handler(BaseHTTPRequestHandler):
    def reply(self, code: int, body: Any) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        global scenario, polls
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        scenario = body["research_question"]
        polls = 0
        self.reply(202, {"run_id": RUN_ID, "lifecycle_state": "queued"})

    def do_GET(self) -> None:
        global polls
        if self.path == "/healthz":
            self.reply(200, {"status": "ok", "version": "1.7.1"})
        elif self.path == "/v1/catalog":
            self.reply(
                200,
                {
                    "data_namespace": "product",
                    "companies": [{"company_id": "cn_300750", "period_labels": ["2024H1"]}],
                    "supported_task_types": ["filing_analysis"],
                },
            )
        elif self.path == f"/v1/research-runs/{RUN_ID}":
            polls += 1
            if "unavailable" in scenario:
                self.reply(503, {"message": "test-only unavailable"})
                return
            state = "running" if polls <= 2 or "forever" in scenario else "failed"
            if "cancelled" in scenario and polls > 2:
                state = "cancelled"
            if "missing-result" in scenario:
                state = "succeeded"
            self.reply(200, {"run_id": RUN_ID, "lifecycle_state": state})
        else:
            self.reply(404, {"code": "NO_RESEARCH_ARTIFACTS_IN_TEST_FIXTURE"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8018), Handler).serve_forever()
