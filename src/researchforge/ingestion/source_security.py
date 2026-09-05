"""Official-source URL guards shared by live discovery and acquisition adapters."""

from __future__ import annotations

from collections.abc import Collection
from urllib.parse import urlparse

from researchforge.ingestion.errors import IngestionAbstention


def validate_official_https(
    url: str,
    *,
    allowed_hosts: Collection[str],
    provider: str,
    stage: str,
) -> None:
    """Reject non-HTTPS or redirected non-official source locations."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    allowed = {item.casefold() for item in allowed_hosts}
    if parsed.scheme != "https" or host not in allowed:
        raise IngestionAbstention(
            "UNTRUSTED_SOURCE_URI",
            stage,
            f"{provider} URL is not HTTPS on an allowlisted official host.",
        )
