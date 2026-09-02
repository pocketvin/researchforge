"""Real public-disclosure ingestion for the bounded V1.5 product namespace."""

from researchforge.ingestion.pipeline import (
    FilingRegistry,
    IngestionAbstention,
    ProductDisclosureIngestion,
)

__all__ = ["FilingRegistry", "IngestionAbstention", "ProductDisclosureIngestion"]
