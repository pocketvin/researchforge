"""Small durable LangGraph checkpointer for the file-backed L1 runtime."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import InMemorySaver


def _encode_typed(value: tuple[str, bytes]) -> list[str]:
    return [value[0], base64.b64encode(value[1]).decode("ascii")]


def _decode_typed(value: list[str]) -> tuple[str, bytes]:
    return value[0], base64.b64decode(value[1], validate=True)


class DurableJsonCheckpointSaver(InMemorySaver):
    """Persist LangGraph checkpoints atomically without executable pickle data.

    This adapter is intentionally limited to the single-process file runtime. The
    PostgreSQL product stage replaces it for multi-process coordination.
    """

    format_version = 1

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._persistence_lock = threading.RLock()
        super().__init__()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("format_version") != self.format_version:
            raise ValueError("unsupported LangGraph checkpoint file format")
        for item in payload.get("storage", []):
            self.storage[item["thread_id"]][item["checkpoint_ns"]][item["checkpoint_id"]] = (
                _decode_typed(item["checkpoint"]),
                _decode_typed(item["metadata"]),
                item["parent_checkpoint_id"],
            )
        for item in payload.get("writes", []):
            outer_key = (
                item["thread_id"],
                item["checkpoint_ns"],
                item["checkpoint_id"],
            )
            for write in item["values"]:
                inner_key = (write["task_id"], write["write_index"])
                self.writes[outer_key][inner_key] = (
                    write["task_id"],
                    write["channel"],
                    _decode_typed(write["value"]),
                    write["task_path"],
                )
        for item in payload.get("blobs", []):
            key = (
                item["thread_id"],
                item["checkpoint_ns"],
                item["channel"],
                item["version"],
            )
            self.blobs[key] = _decode_typed(item["value"])

    def _payload(self) -> dict[str, Any]:
        storage = []
        for thread_id, namespaces in self.storage.items():
            for checkpoint_ns, checkpoints in namespaces.items():
                for checkpoint_id, storage_value in checkpoints.items():
                    checkpoint, metadata, parent_checkpoint_id = storage_value
                    storage.append(
                        {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": checkpoint_id,
                            "checkpoint": _encode_typed(checkpoint),
                            "metadata": _encode_typed(metadata),
                            "parent_checkpoint_id": parent_checkpoint_id,
                        }
                    )
        writes = []
        for (thread_id, checkpoint_ns, checkpoint_id), values in self.writes.items():
            encoded_values = []
            for (task_id, write_index), write_value in values.items():
                _, channel, typed_value, task_path = write_value
                encoded_values.append(
                    {
                        "task_id": task_id,
                        "write_index": write_index,
                        "channel": channel,
                        "value": _encode_typed(typed_value),
                        "task_path": task_path,
                    }
                )
            writes.append(
                {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                    "values": encoded_values,
                }
            )
        blobs = [
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "channel": channel,
                "version": version,
                "value": _encode_typed(blob_value),
            }
            for (thread_id, checkpoint_ns, channel, version), blob_value in self.blobs.items()
        ]
        return {
            "format_version": self.format_version,
            "storage": storage,
            "writes": writes,
            "blobs": blobs,
        }

    def _sync(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}."
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(
                    self._payload(),
                    handle,
                    ensure_ascii=True,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        with self._persistence_lock:
            return super().get_tuple(config)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        with self._persistence_lock:
            return iter(list(super().list(config, filter=filter, before=before, limit=limit)))

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        with self._persistence_lock:
            updated = super().put(config, checkpoint, metadata, new_versions)
            self._sync()
            return updated

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        with self._persistence_lock:
            super().put_writes(config, writes, task_id, task_path)
            self._sync()

    def delete_thread(self, thread_id: str) -> None:
        with self._persistence_lock:
            super().delete_thread(thread_id)
            self._sync()
