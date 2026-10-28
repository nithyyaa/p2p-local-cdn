"""Thread-safe tracking of actual file transfer operations."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any


class TransferTracker:
    """Store recent transfer activity for the dashboard."""

    def __init__(self, max_records: int = 200) -> None:
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._max_records = max_records

    def start(
        self,
        name: str,
        peer: str = "local cache",
        total_chunks: int = 0,
    ) -> str:
        """Create a record when a file transfer begins."""
        transfer_id = uuid.uuid4().hex

        record = {
            "id": transfer_id,
            "name": name,
            "peer": peer,
            "status": "downloading",
            "progress": 0,
            "bytes": 0,
            "bytes_done": 0,
            "bytes_total": 0,
            "peer_bytes": 0,
            "cache_bytes": 0,
            "chunks_done": 0,
            "chunks_total": max(0, total_chunks),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": 0.0,
            "_started_monotonic": time.monotonic(),
        }

        with self._lock:
            self._records.insert(0, record)
            del self._records[self._max_records:]

        return transfer_id

    def update_chunk(
        self,
        transfer_id: str,
        chunk_bytes: int,
        source: str,
    ) -> None:
        """Record a successfully retrieved chunk."""
        with self._lock:
            record = self._find(transfer_id)
            if record is None or record["status"] != "downloading":
                return

            record["chunks_done"] += 1
            record["bytes_done"] += chunk_bytes

            if source == "peer":
                record["peer_bytes"] += chunk_bytes
            else:
                record["cache_bytes"] += chunk_bytes

            total = record["chunks_total"]
            if total:
                record["progress"] = min(
                    99,
                    round(record["chunks_done"] / total * 100),
                )

    def finish(
        self,
        transfer_id: str,
        status: str,
        file_bytes: int = 0,
    ) -> None:
        """Mark a transfer as completed or failed."""
        if status not in {"completed", "failed"}:
            raise ValueError("Status must be completed or failed.")

        with self._lock:
            record = self._find(transfer_id)
            if record is None:
                return

            record["status"] = status
            record["elapsed_seconds"] = round(
                time.monotonic() - record["_started_monotonic"],
                3,
            )

            if status == "completed":
                record["progress"] = 100
                record["bytes"] = max(0, file_bytes)

            record["finished_at"] = datetime.now(
                timezone.utc
            ).isoformat()

    def list_records(self) -> list[dict[str, Any]]:
        """Return dashboard-safe copies of recent transfer records."""
        with self._lock:
            return [
                {
                    key: value
                    for key, value in record.items()
                    if not key.startswith("_")
                }
                for record in self._records
            ]

    def _find(self, transfer_id: str) -> dict[str, Any] | None:
        """Find a record while the caller holds the lock."""
        return next(
            (
                record
                for record in self._records
                if record["id"] == transfer_id
            ),
            None,
        )