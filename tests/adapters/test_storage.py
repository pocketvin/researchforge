"""Content-addressing and run-pointer regression tests."""

from __future__ import annotations

import os
import threading
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


def test_content_store_concurrent_identical_puts_are_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker_count = 8
    stores = [ContentAddressedJsonStore(tmp_path) for _ in range(worker_count)]
    barrier = threading.Barrier(worker_count)
    original_link = os.link
    results = []
    errors: list[BaseException] = []

    def racing_link(source: os.PathLike[str], target: os.PathLike[str]) -> None:
        barrier.wait(timeout=5)
        original_link(source, target)

    monkeypatch.setattr(os, "link", racing_link)

    def worker(store: ContentAddressedJsonStore) -> None:
        try:
            results.append(store.put({"shared": "evidence", "value": 42}))
        except BaseException as exc:  # pragma: no cover - assertion reports thread failures
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(store,)) for store in stores]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert len(results) == worker_count
    assert len({item.digest for item in results}) == 1
    assert len({item.path for item in results}) == 1
    assert stores[0].get(results[0].digest) == {"shared": "evidence", "value": 42}
    assert len(list((tmp_path / "objects").rglob("*.json"))) == 1


@pytest.mark.parametrize(
    "identity",
    ["../secret", "artifact_sha256_../secret", "A" * 64, "0" * 63],
)
def test_content_store_rejects_non_hash_identity(tmp_path: Path, identity: str) -> None:
    store = ContentAddressedJsonStore(tmp_path)

    with pytest.raises(ValueError, match="SHA-256"):
        store.get(identity)
