"""Content-addressed JSON artifacts with small mutable run pointers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class RunNotFoundError(KeyError):
    """Raised when a run pointer does not exist."""


class IdempotencyConflictError(ValueError):
    """Raised when one idempotency key is reused for different immutable input."""


@dataclass(frozen=True, slots=True)
class StoredJsonArtifact:
    """Identity and location of one immutable JSON blob."""

    digest: str
    artifact_id: str
    path: Path


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize content deterministically for hashing and persistence."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def payload_sha256(payload: Any) -> str:
    """Return the canonical JSON SHA-256 for a payload."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


class ContentAddressedJsonStore:
    """Persist immutable JSON objects below a SHA-256 directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.objects = self.root / "objects" / "sha256"
        self.objects.mkdir(parents=True, exist_ok=True)

    def put(self, payload: Any) -> StoredJsonArtifact:
        content = canonical_json_bytes(payload)
        digest = hashlib.sha256(content).hexdigest()
        path = self.objects / digest[:2] / f"{digest}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != content:
                raise RuntimeError("content-address collision or corrupted artifact")
        else:
            try:
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError as exc:
                if path.read_bytes() != content:
                    raise RuntimeError("concurrent content-address collision") from exc
            else:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
        return StoredJsonArtifact(
            digest=digest,
            artifact_id=f"artifact_sha256_{digest}",
            path=path,
        )

    def get(self, digest_or_artifact_id: str) -> Any:
        digest = digest_or_artifact_id.removeprefix("artifact_sha256_")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("artifact identity must contain one lowercase SHA-256")
        path = self.objects / digest[:2] / f"{digest}.json"
        try:
            content = path.read_bytes()
        except FileNotFoundError as exc:
            raise KeyError(digest_or_artifact_id) from exc
        if hashlib.sha256(content).hexdigest() != digest:
            raise RuntimeError("artifact content hash mismatch")
        return json.loads(content)


class FileRunRepository:
    """Map logical run artifacts to immutable content-addressed JSON blobs."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.store = ContentAddressedJsonStore(self.root)
        self.run_dir = self.root / "runs"
        self.idempotency_dir = self.root / "idempotency"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.idempotency_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def request_fingerprint(request: dict[str, Any]) -> str:
        """Hash immutable input while excluding the key that identifies retries."""
        immutable = {key: value for key, value in request.items() if key != "idempotency_key"}
        return payload_sha256(immutable)

    @staticmethod
    def _safe_key_name(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(canonical_json_bytes(payload))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def create_or_get(
        self,
        request: dict[str, Any],
        run_id: str,
        manifest: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        fingerprint = self.request_fingerprint(request)
        key_path = self.idempotency_dir / f"{self._safe_key_name(request['idempotency_key'])}.json"
        with self._lock:
            if key_path.exists():
                record = json.loads(key_path.read_text(encoding="utf-8"))
                if record["request_fingerprint"] != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency key is already bound to different immutable input"
                    )
                return self.get_manifest(record["run_id"]), False

            artifact = self.store.put(manifest)
            pointer: dict[str, Any] = {
                "run_id": run_id,
                "request_fingerprint": fingerprint,
                "manifest_digest": artifact.digest,
                "result_digest": None,
                "trace_digest": None,
                "calculation_digests": [],
                "plan_digest": None,
                "evaluation_digest": None,
                "cancel_requested": False,
            }
            self._atomic_write(self.run_dir / f"{run_id}.json", pointer)
            self._atomic_write(
                key_path,
                {"run_id": run_id, "request_fingerprint": fingerprint},
            )
            return manifest, True

    def _pointer(self, run_id: str) -> dict[str, Any]:
        path = self.run_dir / f"{run_id}.json"
        try:
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc

    def _save_pointer(self, pointer: dict[str, Any]) -> None:
        self._atomic_write(self.run_dir / f"{pointer['run_id']}.json", pointer)

    def get_manifest(self, run_id: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.store.get(self._pointer(run_id)["manifest_digest"]))

    def save_manifest(self, run_id: str, manifest: dict[str, Any]) -> None:
        artifact = self.store.put(manifest)
        with self._lock:
            pointer = self._pointer(run_id)
            pointer["manifest_digest"] = artifact.digest
            self._save_pointer(pointer)

    def save_result(self, run_id: str, result: dict[str, Any]) -> None:
        artifact = self.store.put(result)
        with self._lock:
            pointer = self._pointer(run_id)
            pointer["result_digest"] = artifact.digest
            self._save_pointer(pointer)

    def save_trace(self, run_id: str, trace: dict[str, Any]) -> None:
        artifact = self.store.put(trace)
        with self._lock:
            pointer = self._pointer(run_id)
            pointer["trace_digest"] = artifact.digest
            self._save_pointer(pointer)

    def save_plan(self, run_id: str, plan: dict[str, Any]) -> None:
        artifact = self.store.put(plan)
        with self._lock:
            pointer = self._pointer(run_id)
            pointer["plan_digest"] = artifact.digest
            self._save_pointer(pointer)

    def save_calculations(self, run_id: str, calculations: list[dict[str, Any]]) -> None:
        digests = [self.store.put(calculation).digest for calculation in calculations]
        with self._lock:
            pointer = self._pointer(run_id)
            pointer["calculation_digests"] = digests
            self._save_pointer(pointer)

    def save_evaluation(self, run_id: str, evaluation: dict[str, Any]) -> None:
        artifact = self.store.put(evaluation)
        with self._lock:
            pointer = self._pointer(run_id)
            pointer["evaluation_digest"] = artifact.digest
            self._save_pointer(pointer)

    def _get_linked(self, run_id: str, field: str) -> Any:
        digest = self._pointer(run_id)[field]
        if digest is None:
            raise KeyError(f"run {run_id} has no {field}")
        return self.store.get(digest)

    def get_result(self, run_id: str) -> dict[str, Any]:
        return cast(dict[str, Any], self._get_linked(run_id, "result_digest"))

    def get_trace(self, run_id: str) -> dict[str, Any]:
        return cast(dict[str, Any], self._get_linked(run_id, "trace_digest"))

    def get_calculations(self, run_id: str) -> list[dict[str, Any]]:
        pointer = self._pointer(run_id)
        return [
            cast(dict[str, Any], self.store.get(digest))
            for digest in pointer["calculation_digests"]
        ]

    def get_evaluation(self, run_id: str) -> dict[str, Any]:
        return cast(dict[str, Any], self._get_linked(run_id, "evaluation_digest"))

    def artifact_references(self, run_id: str) -> dict[str, str]:
        pointer = self._pointer(run_id)
        references = {
            kind: str(pointer[field])
            for kind, field in (
                ("manifest", "manifest_digest"),
                ("result", "result_digest"),
                ("trace", "trace_digest"),
                ("plan", "plan_digest"),
                ("evaluation", "evaluation_digest"),
            )
            if pointer.get(field) is not None
        }
        for index, digest in enumerate(pointer["calculation_digests"], start=1):
            references[f"calculation_{index:03d}"] = str(digest)
        return references

    def request_cancel(self, run_id: str) -> bool:
        with self._lock:
            pointer = self._pointer(run_id)
            already_requested = bool(pointer["cancel_requested"])
            pointer["cancel_requested"] = True
            self._save_pointer(pointer)
            return not already_requested

    def is_cancel_requested(self, run_id: str) -> bool:
        return bool(self._pointer(run_id)["cancel_requested"])

    def list_run_ids(self) -> list[str]:
        """List only validated logical run IDs from local pointer records."""
        run_ids: list[str] = []
        for path in sorted(self.run_dir.glob("*.json")):
            pointer = json.loads(path.read_text(encoding="utf-8"))
            run_id = str(pointer["run_id"])
            if path.name == f"{run_id}.json":
                run_ids.append(run_id)
        return run_ids
