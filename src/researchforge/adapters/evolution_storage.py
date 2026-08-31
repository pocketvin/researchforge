"""Read-only UI repository for controlled Evolution artifacts."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.storage import ContentAddressedJsonStore, canonical_json_bytes

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$")


class EvolutionArtifactRepository:
    """Content-address experiment artifacts behind small logical pointers."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.store = ContentAddressedJsonStore(self.root)
        self.pointer_root = self.root / "evolution"
        self.pointer_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate(value: str) -> str:
        if SAFE_ID.fullmatch(value) is None:
            raise ValueError("evolution artifact identity is invalid")
        return value

    def _path(self, experiment_id: str, kind: str) -> Path:
        safe_experiment = self._validate(experiment_id)
        safe_kind = self._validate(kind)
        return self.pointer_root / safe_experiment / f"{safe_kind}.json"

    def save(self, experiment_id: str, kind: str, payload: dict[str, Any]) -> str:
        artifact = self.store.put(payload)
        path = self._path(experiment_id, kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        pointer = {
            "experiment_id": experiment_id,
            "kind": kind,
            "digest": artifact.digest,
        }
        content = canonical_json_bytes(pointer)
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return artifact.digest

    def get(self, experiment_id: str, kind: str = "experiment") -> dict[str, Any]:
        path = self._path(experiment_id, kind)
        try:
            pointer = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise KeyError(f"{experiment_id}/{kind}") from exc
        return cast(dict[str, Any], self.store.get(str(pointer["digest"])))
