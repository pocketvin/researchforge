from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from researchforge.config import has_secret, load_runtime_settings
from researchforge.v2.runtime import build_service

_PROVIDER_ENV = (
    "OPENAI_API_KEY",
    "RESEARCHFORGE_PROVIDER",
    "RESEARCHFORGE_QWEN_API_KEY",
    "RESEARCHFORGE_QWEN_BASE_URL",
    "RESEARCHFORGE_DEEPSEEK_API_KEY",
    "RESEARCHFORGE_DEEPSEEK_BASE_URL",
    "RESEARCHFORGE_KIMI_API_KEY",
    "RESEARCHFORGE_KIMI_BASE_URL",
)


def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _PROVIDER_ENV:
        monkeypatch.delenv(name, raising=False)


def _write_hybrid_env(root: Path, *, kimi_key: str = "", kimi_base: str = "") -> None:
    (root / ".env").write_text(
        "\n".join(
            [
                "RESEARCHFORGE_PROVIDER=hybrid",
                "RESEARCHFORGE_QWEN_API_KEY=qwen-test-key",
                "RESEARCHFORGE_QWEN_BASE_URL=https://qwen.example/v1",
                "RESEARCHFORGE_DEEPSEEK_API_KEY=deepseek-test-key",
                "RESEARCHFORGE_DEEPSEEK_BASE_URL=https://deepseek.example",
                f"RESEARCHFORGE_KIMI_API_KEY={kimi_key}",
                f"RESEARCHFORGE_KIMI_BASE_URL={kimi_base}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_empty_secret_is_not_configured() -> None:
    assert has_secret(None) is False
    assert has_secret(SecretStr("")) is False
    assert has_secret(SecretStr("   ")) is False
    assert has_secret(SecretStr("configured")) is True


def test_hybrid_runtime_does_not_require_optional_kimi_standby(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_provider_env(monkeypatch)
    _write_hybrid_env(tmp_path)

    settings = load_runtime_settings(tmp_path)
    assert settings.researchforge_provider == "hybrid"
    assert has_secret(settings.researchforge_kimi_api_key) is False

    service = build_service(tmp_path, tmp_path / "artifacts")
    assert service.model_factory is not None
    assert service.configuration["provider"] == "hybrid"
    assert service.configuration["model"] == "deepseek-v4-flash"


def test_optional_kimi_standby_requires_key_and_base_url_together(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_provider_env(monkeypatch)
    _write_hybrid_env(tmp_path, kimi_key="kimi-test-key", kimi_base="")

    with pytest.raises(ValueError, match="Kimi standby requires both API key and base URL"):
        load_runtime_settings(tmp_path)


def test_required_provider_rejects_blank_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_provider_env(monkeypatch)
    (tmp_path / ".env").write_text(
        "RESEARCHFORGE_PROVIDER=qwen\n"
        "RESEARCHFORGE_QWEN_API_KEY=\n"
        "RESEARCHFORGE_QWEN_BASE_URL=https://qwen.example/v1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Qwen provider requires a local API key"):
        load_runtime_settings(tmp_path)
