"""Real public-disclosure ingestion for the bounded V1.5 product namespace."""

from researchforge.ingestion.errors import IngestionAbstention
from researchforge.ingestion.pipeline import FilingRegistry, ProductDisclosureIngestion

__all__ = ["FilingRegistry", "IngestionAbstention", "ProductDisclosureIngestion"]
