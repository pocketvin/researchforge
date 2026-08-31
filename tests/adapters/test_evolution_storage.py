"""Content-addressed controlled Evolution artifact tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from researchforge.adapters.evolution_storage import EvolutionArtifactRepository


def test_evolution_storage_rejects_path_traversal_and_round_trips(tmp_path: Path) -> None:
    repository = EvolutionArtifactRepository(tmp_path)
    payload = {"experiment_id": "experiment_safe", "outcome": "PENDING"}

    digest = repository.save("experiment_safe", "experiment", payload)

    assert len(digest) == 64
    assert repository.get("experiment_safe") == payload
    with pytest.raises(ValueError, match="identity is invalid"):
        repository.get("../outside")
    with pytest.raises(ValueError, match="identity is invalid"):
        repository.save("experiment_safe", "../../outside", payload)
