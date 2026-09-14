"""Zero-provider-call smoke for the packaged canonical V2 Web/API stack."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any, cast


def request_json(url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status} from {url}")
        return cast(dict[str, Any], json.load(response))


def request_text(url: str, *, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP {response.status} from {url}")
        return cast(str, response.read().decode())


def expect_status(url: str, expected: int, *, timeout: float = 10.0) -> None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            actual = response.status
    except urllib.error.HTTPError as exc:
        actual = exc.code
    if actual != expected:
        raise RuntimeError(f"expected HTTP {expected} from {url}, got {actual}")


def run_smoke(base_url: str) -> dict[str, Any]:
    health = request_text(f"{base_url}/healthz")
    if health != "ok":
        raise RuntimeError("frontend health response was not 'ok'")
    capabilities = request_json(f"{base_url}/v2/capabilities")
    if capabilities.get("real_agent_loop") is not True:
        raise RuntimeError("V2 capability surface is not the canonical agent runtime")
    frontend = request_text(f"{base_url}/")
    if 'id="root"' not in frontend:
        raise RuntimeError("frontend root was not served")
    expect_status(f"{base_url}/v1/runtime-capabilities", 404)
    expect_status(f"{base_url}/v2/research-runs/run_missing", 404)
    return {
        "status": "PASS",
        "runtime": "v2",
        "provider": capabilities.get("provider"),
        "model": capabilities.get("model"),
        "agent_ready": capabilities.get("agent_ready"),
        "legacy_v1_live_api": False,
        "frontend_served": True,
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:4173")
    args = parser.parse_args()
    try:
        print(json.dumps(run_smoke(args.base_url.rstrip("/")), indent=2))
    except (OSError, RuntimeError, urllib.error.HTTPError) as exc:
        raise SystemExit(f"Docker smoke failed: {exc}") from exc


if __name__ == "__main__":
    main()
