"""Shared official-disclosure discovery and extraction primitives for V2."""

from researchforge.ingestion.discovery import OfficialDisclosureDiscovery
from researchforge.ingestion.errors import IngestionAbstention

__all__ = ["IngestionAbstention", "OfficialDisclosureDiscovery"]
