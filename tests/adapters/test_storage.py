"""Content-addressing and run-pointer regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from researchforge.adapters.storage import ContentAddressedJsonStore


def test_content_store_deduplicates_canonical_json(tmp_path: Path) -> None:
    store = ContentAddressedJsonStore(tmp_path)

    first = store.put({"b": 2, "a": 1})
    second = store.put({"a": 1, "b": 2})

    assert first.digest == second.digest
    assert first.path == second.path
    assert store.get(first.artifact_id) == {"a": 1, "b": 2}
    assert len(list((tmp_path / "objects").rglob("*.json"))) == 1


@pytest.mark.parametrize(
    "identity",
    ["../secret", "artifact_sha256_../secret", "A" * 64, "0" * 63],
)
def test_content_store_rejects_non_hash_identity(tmp_path: Path, identity: str) -> None:
    store = ContentAddressedJsonStore(tmp_path)

    with pytest.raises(ValueError, match="SHA-256"):
        store.get(identity)
