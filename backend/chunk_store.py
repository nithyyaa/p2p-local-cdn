"""Secure storage and SHA-256 verification for CDN chunks."""

import hashlib
from pathlib import Path

from backend.config import Settings


class ChunkStore:
    """Store chunks by hash and verify their integrity."""

    def __init__(self, settings: Settings):
        self.chunks_dir = settings.chunks_dir
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_hash(data: bytes) -> str:
        """Calculate the SHA-256 hash of a chunk."""
        return hashlib.sha256(data).hexdigest()

    def store_chunk(self, data: bytes, expected_hash: str) -> Path:
        """
        Verify a chunk and store it under its SHA-256 hash.

        Raises ValueError if the data does not match the expected hash.
        """
        actual_hash = self.calculate_hash(data)

        if actual_hash != expected_hash:
            raise ValueError("Chunk integrity verification failed")

        chunk_path = self.chunks_dir / actual_hash

        # Reuse an existing chunk only if its contents are still valid.
        if chunk_path.is_file():
            existing_data = chunk_path.read_bytes()

            if self.calculate_hash(existing_data) == actual_hash:
                return chunk_path

        # Write to a temporary file before replacing the destination.
        temp_path = self.chunks_dir / f".{actual_hash}.tmp"

        try:
            temp_path.write_bytes(data)
            temp_path.replace(chunk_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        return chunk_path

    def get_chunk(self, chunk_hash: str) -> bytes:
        """Retrieve a chunk after verifying its stored contents."""
        if (
            len(chunk_hash) != 64
            or any(char not in "0123456789abcdef" for char in chunk_hash)
        ):
            raise ValueError("Invalid SHA-256 hash")

        chunk_path = self.chunks_dir / chunk_hash

        if not chunk_path.is_file():
            raise FileNotFoundError(f"Chunk not found: {chunk_hash}")

        data = chunk_path.read_bytes()

        if self.calculate_hash(data) != chunk_hash:
            raise ValueError("Stored chunk failed integrity verification")

        return data