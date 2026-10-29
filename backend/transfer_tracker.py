
"""Thread-safe tracking of actual file transfer operations."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any


VALID_SOURCES = {"peer", "cache", "origin"}


class TransferTracker:
    """Store recent transfer activity for the dashboard."""

    def __init__(self, max_records: int = 200) -> None:
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self._max_records = max(1, max_records)

    def start(
        self,
        name: str,
        peer: str = "local cache",
        total_chunks: int = 0,
        total_bytes: int = 0,
    ) -> str:
        """Create a record when a file transfer begins."""
        transfer_id = uuid.uuid4().hex

        total_chunks = max(0, total_chunks)
        total_bytes = max(0, total_bytes)

        record = {
            "id": transfer_id,
            "name": name,
            "peer": peer,
            "status": "downloading",
            "source": None,
            "progress": 0,
            "bytes": 0,
            "bytes_done": 0,
            "bytes_total": total_bytes,
            "peer_bytes": 0,
            "cache_bytes": 0,
            "origin_bytes": 0,
            "chunks_done": 0,
            "chunks_total": total_chunks,
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
        """Record a successfully retrieved chunk and its actual source."""
        if (
            isinstance(chunk_bytes, bool)
            or not isinstance(chunk_bytes, int)
            or chunk_bytes < 0
        ):
            raise ValueError("chunk_bytes must be a non-negative integer.")

        if source not in VALID_SOURCES:
            raise ValueError("source must be one of: peer, cache, origin.")

        with self._lock:
            record = self._find(transfer_id)

            if record is None or record["status"] != "downloading":
                return

            record["chunks_done"] += 1
            record["bytes_done"] += chunk_bytes

            if source == "peer":
                record["peer_bytes"] += chunk_bytes
            elif source == "cache":
                record["cache_bytes"] += chunk_bytes
            else:
                record["origin_bytes"] += chunk_bytes

            # Determine the overall source from actual bytes retrieved.
            source_bytes = {
                "peer": record["peer_bytes"],
                "cache": record["cache_bytes"],
                "origin": record["origin_bytes"],
            }

            used_sources = [
                name for name, count in source_bytes.items() if count > 0
            ]

            if len(used_sources) == 1:
                record["source"] = used_sources[0]
            elif len(used_sources) > 1:
                record["source"] = "mixed"

            total_bytes = record["bytes_total"]

            if total_bytes > 0:
                record["progress"] = min(
                    99,
                    round(record["bytes_done"] / total_bytes * 100),
                )
            elif record["chunks_total"] > 0:
                record["progress"] = min(
                    99,
                    round(
                        record["chunks_done"]
                        / record["chunks_total"]
                        * 100
                    ),
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

        if (
            isinstance(file_bytes, bool)
            or not isinstance(file_bytes, int)
            or file_bytes < 0
        ):
            raise ValueError("file_bytes must be a non-negative integer.")

        with self._lock:
            record = self._find(transfer_id)

            if record is None or record["status"] != "downloading":
                return

            accounted_bytes = (
                record["peer_bytes"]
                + record["cache_bytes"]
                + record["origin_bytes"]
            )

            # Validate before changing the record's final status.
            if status == "completed":
                if accounted_bytes != record["bytes_done"]:
                    raise RuntimeError(
                        "Transfer accounting mismatch: source byte totals "
                        "do not match bytes_done."
                    )

                if file_bytes != record["bytes_done"]:
                    raise ValueError(
                        "file_bytes does not match the bytes recorded "
                        "by update_chunk()."
                    )

                if (
                    record["bytes_total"] > 0
                    and record["bytes_total"] != file_bytes
                ):
                    raise ValueError(
                        "file_bytes does not match bytes_total."
                    )

            elapsed = max(
                0.0,
                time.monotonic() - record["_started_monotonic"],
            )

            record["status"] = status
            record["elapsed_seconds"] = round(elapsed, 6)
            record["finished_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            if status == "completed":
                if record["bytes_total"] == 0:
                    record["bytes_total"] = file_bytes

                record["bytes"] = record["bytes_done"]
                record["progress"] = 100
            else:
                record["bytes"] = record["bytes_done"]

            # Calculate speed using the unrounded elapsed time.
            record["speed"] = (
                round(record["bytes"] / elapsed, 2)
                if elapsed > 0
                else 0.0
            )

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
