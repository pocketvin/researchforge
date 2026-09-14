"""Local runtime settings with secret-safe `.env` loading."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def has_secret(value: SecretStr | None) -> bool:
    """Return True only for a non-empty secret value."""
    return value is not None and bool(value.get_secret_value().strip())


class RuntimeSettings(BaseSettings):
    """ResearchForge runtime configuration; secret values are never serialized."""

    model_config = SettingsConfigDict(extra="ignore", env_file_encoding="utf-8")

    openai_api_key: SecretStr | None = None
    researchforge_provider: Literal["openai", "qwen", "hybrid"] = "openai"
    researchforge_rotated_key_confirmed: bool = False
    researchforge_model: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"
    researchforge_qwen_api_key: SecretStr | None = None
    researchforge_qwen_base_url: str | None = None
    researchforge_qwen_model: Literal["qwen-plus"] = "qwen-plus"
    researchforge_qwen_review_model: Literal["qwen3-max", "qwen-max", "qwen-plus"] = "qwen-plus"
    researchforge_qwen_fallback_synthesis_model: Literal["qwen3-max", "qwen-max", "qwen-plus"] = (
        "qwen3-max"
    )
    researchforge_qwen_vision_model: Literal["qwen3-vl-plus"] = "qwen3-vl-plus"
    researchforge_deepseek_api_key: SecretStr | None = None
    researchforge_deepseek_base_url: str | None = None
    researchforge_deepseek_model: Literal["deepseek-v4-flash"] = "deepseek-v4-flash"
    researchforge_kimi_api_key: SecretStr | None = None
    researchforge_kimi_base_url: str | None = None
    researchforge_kimi_model: Literal["kimi-k3"] = "kimi-k3"
    researchforge_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = (
        "medium"
    )
    researchforge_reasoning_mode: Literal["auto", "openai", "deterministic"] = "auto"
    researchforge_openai_store: bool = False
    researchforge_budget_usd: Decimal = Field(default=Decimal("20.00"), gt=0, le=20)
    researchforge_v2_run_budget_usd: Decimal = Field(default=Decimal("0.35"), gt=0, le=2)
    researchforge_sec_user_agent: str = "ResearchForge/2.0 researchforge@example.com"
    researchforge_artifact_root: Path | None = None
    researchforge_api_docs_enabled: bool = False


def load_runtime_settings(project_root: Path) -> RuntimeSettings:
    """Read process environment and the ignored project `.env` without exposing secrets."""
    settings = RuntimeSettings(_env_file=project_root / ".env")  # type: ignore[call-arg]
    if settings.researchforge_openai_store:
        raise ValueError("RESEARCHFORGE_OPENAI_STORE must remain false")
    if settings.researchforge_provider in {"qwen", "hybrid"}:
        if (
            not has_secret(settings.researchforge_qwen_api_key)
            or not settings.researchforge_qwen_base_url
        ):
            raise ValueError("Qwen provider requires a local API key and base URL")
        if not settings.researchforge_qwen_base_url.startswith("https://"):
            raise ValueError("Qwen provider base URL must use HTTPS")
    if settings.researchforge_provider == "hybrid":
        if (
            not has_secret(settings.researchforge_deepseek_api_key)
            or not settings.researchforge_deepseek_base_url
        ):
            raise ValueError("Hybrid provider requires a DeepSeek API key and base URL")
        if not settings.researchforge_deepseek_base_url.startswith("https://"):
            raise ValueError("DeepSeek provider base URL must use HTTPS")
        kimi_key_present = has_secret(settings.researchforge_kimi_api_key)
        kimi_base_present = bool(settings.researchforge_kimi_base_url)
        if kimi_key_present != kimi_base_present:
            raise ValueError("Optional Kimi standby requires both API key and base URL, or neither")
        if (
            settings.researchforge_kimi_base_url
            and not settings.researchforge_kimi_base_url.startswith("https://")
        ):
            raise ValueError("Kimi standby base URL must use HTTPS")
    return settings
