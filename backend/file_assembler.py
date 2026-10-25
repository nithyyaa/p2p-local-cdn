
"""Reassemble complete files from SHA-256-verified chunks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable


class FileAssemblyError(ValueError):
    """Raised when a file cannot be safely assembled from its chunks."""


def assemble_file(
    manifest: dict[str, Any],
    chunks_dir: str | Path,
    output_dir: str | Path,
    get_chunk: Callable[[str], bytes] | None = None,
) -> Path:
    """Assemble a file in manifest order, verifying each chunk's SHA-256.

    If get_chunk is supplied, it is called with each chunk hash to retrieve
    chunk data. Otherwise, chunks are read from chunks_dir/<sha256>.
    """
    if not isinstance(manifest, dict):
        raise FileAssemblyError("Manifest must be a dictionary.")

    file_name = manifest.get("file_name")
    if (
        not isinstance(file_name, str)
        or not file_name
        or file_name in {".", ".."}
        or Path(file_name).name != file_name
        or "/" in file_name
        or "\\" in file_name
    ):
        raise FileAssemblyError("Manifest contains an invalid filename.")

    chunks = manifest.get("chunks")
    if not isinstance(chunks, list):
        raise FileAssemblyError("Manifest chunks must be a list.")

    expected_count = manifest.get("chunk_count")
    expected_size = manifest.get("file_size")

    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count < 0
        or expected_count != len(chunks)
    ):
        raise FileAssemblyError("Manifest chunk count is inconsistent.")

    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or expected_size < 0
    ):
        raise FileAssemblyError("Manifest file size is invalid.")

    chunks_path = Path(chunks_dir)
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    output_path = destination_dir / file_name
    temporary_path = destination_dir / f".{file_name}.assembling"

    total_size = 0
    whole_file_hash = hashlib.sha256()

    try:
        with temporary_path.open("wb") as output:
            for index, entry in enumerate(chunks):
                if not isinstance(entry, dict):
                    raise FileAssemblyError(
                        f"Chunk entry {index} must be an object."
                    )

                if entry.get("index") != index:
                    raise FileAssemblyError(
                        f"Chunk index {index} is missing or out of order."
                    )

                chunk_hash = entry.get("sha256")
                if (
                    not isinstance(chunk_hash, str)
                    or re.fullmatch(r"[0-9a-f]{64}", chunk_hash) is None
                ):
                    raise FileAssemblyError(
                        f"Chunk {index} has an invalid SHA-256 hash."
                    )

                expected_chunk_size = entry.get("size")
                if (
                    isinstance(expected_chunk_size, bool)
                    or not isinstance(expected_chunk_size, int)
                    or expected_chunk_size < 0
                ):
                    raise FileAssemblyError(
                        f"Chunk {index} has an invalid size."
                    )

                if get_chunk is None:
                    try:
                        data = (chunks_path / chunk_hash).read_bytes()
                    except OSError as exc:
                        raise FileAssemblyError(
                            f"Chunk {index} is unavailable."
                        ) from exc
                else:
                    data = get_chunk(chunk_hash)

                if not isinstance(data, bytes):
                    raise FileAssemblyError(
                        f"Chunk {index} did not return bytes."
                    )

                if len(data) != expected_chunk_size:
                    raise FileAssemblyError(
                        f"Chunk {index} has an incorrect size."
                    )

                if hashlib.sha256(data).hexdigest() != chunk_hash:
                    raise FileAssemblyError(
                        f"Chunk {index} failed SHA-256 verification."
                    )

                output.write(data)
                whole_file_hash.update(data)
                total_size += len(data)

        if total_size != expected_size:
            raise FileAssemblyError(
                "Assembled file size does not match the manifest."
            )

        temporary_path.replace(output_path)
        return output_path

    finally:
        if temporary_path.exists():
            temporary_path.unlink()
