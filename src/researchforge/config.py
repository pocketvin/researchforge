"""Local runtime settings with secret-safe `.env` loading."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """ResearchForge runtime configuration; secret values are never serialized."""

    model_config = SettingsConfigDict(extra="ignore", env_file_encoding="utf-8")

    openai_api_key: SecretStr | None = None
    researchforge_rotated_key_confirmed: bool = False
    researchforge_model: str = "gpt-5.6-luna"
    researchforge_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = (
        "medium"
    )
    researchforge_reasoning_mode: Literal["auto", "openai", "deterministic"] = "auto"
    researchforge_openai_store: bool = False
    researchforge_budget_usd: Decimal = Field(default=Decimal("20.00"), gt=0, le=20)
    researchforge_database_url: str | None = None
    researchforge_database_enabled: bool = False
    researchforge_artifact_root: Path | None = None
    researchforge_data_namespace: Literal["product", "fixture", "benchmark"] = "product"
    researchforge_data_root: Path | None = None


def load_runtime_settings(project_root: Path) -> RuntimeSettings:
    """Read process environment and the ignored project `.env` without exposing secrets."""
    settings = RuntimeSettings(_env_file=project_root / ".env")  # type: ignore[call-arg]
    if settings.researchforge_openai_store:
        raise ValueError("RESEARCHFORGE_OPENAI_STORE must remain false")
    return settings
