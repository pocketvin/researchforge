"""Run-owned immutable artifacts and an append-only, replayable event journal."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from researchforge.adapters.storage import (
    ContentAddressedJsonStore,
    IdempotencyConflictError,
    RunNotFoundError,
    canonical_json_bytes,
    payload_sha256,
)
from researchforge.file_lock import exclusive_file_lock
from researchforge.v2.contracts import Json, ResearchRequest, TraceEvent

TERMINAL = frozenset({"succeeded", "failed", "cancelled", "timed_out", "insufficient_data"})
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,254}$")


def now() -> str:
    return datetime.now(UTC).isoformat()


def safe_id(value: str) -> str:
    if SAFE_ID.fullmatch(value) is None:
        raise ValueError("invalid artifact identity")
    return value


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class ResearchRepository:
    """Separate V2 namespace; pointers are mutable, their CAS payloads are
    immutable."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.cas = ContentAddressedJsonStore(self.root)
        for folder in ("runs", "idempotency", "events", "locks", "blobs", "checkpoints"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def _pointer_path(self, run_id: str) -> Path:
        return self.root / "runs" / f"{safe_id(run_id)}.json"

    def _pointer(self, run_id: str) -> Json:
        try:
            return cast(Json, json.loads(self._pointer_path(run_id).read_text()))
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc

    def create(self, request: ResearchRequest, configuration: Json) -> tuple[Json, bool]:
        payload = request.model_dump(mode="json")
        fingerprint = payload_sha256({k: v for k, v in payload.items() if k != "idempotency_key"})
        key = hashlib.sha256(request.idempotency_key.encode()).hexdigest()
        key_path = self.root / "idempotency" / f"{key}.json"
        with exclusive_file_lock(self.root / "locks" / "submission.lock"):
            if key_path.exists():
                prior = json.loads(key_path.read_text())
                if prior["fingerprint"] != fingerprint:
                    raise IdempotencyConflictError(
                        "key already belongs to different research input"
                    )
                return self.get(prior["run_id"]), False
            run_id = f"run_{uuid.uuid4().hex}"
            manifest = {
                "schema_version": "2.0.0",
                "run_id": run_id,
                "lifecycle_state": "queued",
                "request": payload,
                "created_at": now(),
                "started_at": None,
                "finished_at": None,
                "configuration": configuration,
                "artifacts": {},
                "failure": None,
                "usage": {},
                "cancel_requested": False,
            }
            digest = self.cas.put(manifest).digest
            atomic_bytes(self._pointer_path(run_id), canonical_json_bytes({"digest": digest}))
            atomic_bytes(
                key_path, canonical_json_bytes({"run_id": run_id, "fingerprint": fingerprint})
            )
        self.emit(run_id, "run_queued", "intake", "研究任务已创建", "queued")
        return manifest, True

    def get(self, run_id: str) -> Json:
        return cast(Json, self.cas.get(self._pointer(run_id)["digest"]))

    def update(self, run_id: str, **changes: Any) -> Json:
        with exclusive_file_lock(self.root / "locks" / f"{safe_id(run_id)}.pointer.lock"):
            manifest = {**self.get(run_id), **changes}
            digest = self.cas.put(manifest).digest
            atomic_bytes(self._pointer_path(run_id), canonical_json_bytes({"digest": digest}))
            return manifest

    def attach(self, run_id: str, name: str, payload: Any) -> str:
        digest = self.cas.put(payload).digest
        with exclusive_file_lock(self.root / "locks" / f"{safe_id(run_id)}.pointer.lock"):
            manifest = self.get(run_id)
            manifest["artifacts"] = {**manifest["artifacts"], name: digest}
            pointer = {"digest": self.cas.put(manifest).digest}
            atomic_bytes(self._pointer_path(run_id), canonical_json_bytes(pointer))
        return digest

    def artifact(self, run_id: str, name: str) -> Any:
        return self.cas.get(self.get(run_id)["artifacts"][name])

    def list_runs(self, limit: int = 30) -> list[Json]:
        manifests = [self.get(path.stem) for path in (self.root / "runs").glob("run_*.json")]
        manifests.sort(key=lambda item: str(item["created_at"]), reverse=True)
        return manifests[:limit]

    def put_blob(self, payload: bytes, extension: str) -> str:
        if extension not in {"pdf", "html", "png"}:
            raise ValueError("unsupported blob type")
        digest = hashlib.sha256(payload).hexdigest()
        blob_id = f"{digest}.{extension}"
        path = self.root / "blobs" / blob_id
        with exclusive_file_lock(self.root / "locks" / f"blob-{digest}.lock"):
            if not path.exists():
                atomic_bytes(path, payload)
            elif path.read_bytes() != payload:
                raise RuntimeError("blob hash collision or corrupted data")
        return blob_id

    def blob_path(self, blob_id: str) -> Path:
        if re.fullmatch(r"[0-9a-f]{64}\.(pdf|html|png)", blob_id) is None:
            raise ValueError("invalid blob identity")
        path = self.root / "blobs" / blob_id
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != blob_id.split(".")[0]:
            raise RuntimeError("source blob hash mismatch")
        return path

    def emit(
        self,
        run_id: str,
        event_type: str,
        name: str,
        label: str,
        status: str,
        *,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        duration_ms: int | None = None,
        data: Json | None = None,
    ) -> Json:
        self._pointer(run_id)
        folder = self.root / "events" / safe_id(run_id)
        folder.mkdir(parents=True, exist_ok=True)
        with exclusive_file_lock(self.root / "locks" / f"{run_id}.events.lock"):
            previous = sorted(folder.glob("*.json"))
            sequence = int(previous[-1].stem) + 1 if previous else 1
            event = TraceEvent(
                run_id=run_id,
                sequence=sequence,
                event_type=event_type,
                timestamp=now(),
                name=name,
                label=label,
                status=status,
                span_id=span_id,
                parent_span_id=parent_span_id,
                duration_ms=duration_ms,
                data=data or {},
            ).model_dump(mode="json")
            digest = self.cas.put(event).digest
            atomic_bytes(
                folder / f"{sequence:08d}.json", canonical_json_bytes({("digest"): digest})
            )
        return event

    def events(self, run_id: str, after: int = 0, limit: int = 1000) -> list[Json]:
        self._pointer(run_id)
        folder = self.root / "events" / safe_id(run_id)
        paths = [path for path in sorted(folder.glob("*.json")) if int(path.stem) > after][:limit]
        return [
            cast(Json, self.cas.get(json.loads(path.read_text())[("digest")])) for path in paths
        ]

    @contextmanager
    def span(
        self,
        run_id: str,
        name: str,
        label: str,
        *,
        parent: str | None = None,
        data: Json | None = None,
    ) -> Iterator[str]:
        span_id = f"span_{uuid.uuid4().hex}"
        started = time.monotonic()
        self.emit(
            run_id,
            "span_started",
            name,
            label,
            "running",
            span_id=span_id,
            parent_span_id=parent,
            data=data,
        )
        try:
            yield span_id
        except Exception as exc:
            self.emit(
                run_id,
                "span_finished",
                name,
                label,
                "failed",
                span_id=span_id,
                parent_span_id=parent,
                duration_ms=int((time.monotonic() - started) * 1000),
                data={"error_type": type(exc).__name__},
            )
            raise
        else:
            self.emit(
                run_id,
                "span_finished",
                name,
                label,
                "succeeded",
                span_id=span_id,
                parent_span_id=parent,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
