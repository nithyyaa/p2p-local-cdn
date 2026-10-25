
"""File chunking and SHA-256 manifest generation for the P2P LAN CDN."""

import hashlib
from pathlib import Path
from typing import Any


DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def build_manifest(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict[str, Any]:
    """
    Read a file in chunks and build a JSON-serializable manifest.

    Each chunk entry contains its index, byte size, and SHA-256 hash.
    File contents are not stored in memory all at once.
    """
    path = Path(file_path)

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    chunks: list[dict[str, Any]] = []
    total_size = 0

    with path.open("rb") as file:
        index = 0

        while True:
            data = file.read(chunk_size)

            if not data:
                break

            chunks.append(
                {
                    "index": index,
                    "size": len(data),
                    "sha256": sha256_bytes(data),
                }
            )

            total_size += len(data)
            index += 1

    return {
        "file_name": path.name,
        "file_size": total_size,
        "chunk_size": chunk_size,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
