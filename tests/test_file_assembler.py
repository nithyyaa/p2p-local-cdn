
import hashlib
import pytest

from backend.file_assembler import assemble_file, FileAssemblyError
from backend.chunker import build_manifest


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_assembles_file_from_chunks(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"Hello P2P CDN!")

    manifest = build_manifest(source, chunk_size=5)
    chunks_dir = tmp_path / "chunks"
    output_dir = tmp_path / "downloads"
    chunks_dir.mkdir()

    for entry in manifest["chunks"]:
        start = entry["index"] * manifest["chunk_size"]
        data = source.read_bytes()[start:start + entry["size"]]
        (chunks_dir / entry["sha256"]).write_bytes(data)

    result = assemble_file(manifest, chunks_dir, output_dir)

    assert result.read_bytes() == source.read_bytes()


def test_rejects_corrupted_chunk(tmp_path):
    data = b"correct data"
    manifest = {
        "file_name": "test.txt",
        "file_size": len(data),
        "chunk_count": 1,
        "chunks": [
            {"index": 0, "size": len(data), "sha256": sha256(data)}
        ],
    }

    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    (chunks_dir / sha256(data)).write_bytes(b"wrong data!")

    with pytest.raises(FileAssemblyError):
        assemble_file(manifest, chunks_dir, tmp_path / "downloads")


def test_rejects_missing_chunk(tmp_path):
    data = b"missing chunk"
    manifest = {
        "file_name": "test.txt",
        "file_size": len(data),
        "chunk_count": 1,
        "chunks": [
            {"index": 0, "size": len(data), "sha256": sha256(data)}
        ],
    }

    with pytest.raises(FileAssemblyError):
        assemble_file(
            manifest,
            tmp_path / "chunks",
            tmp_path / "downloads",
        )


def test_rejects_inconsistent_file_size(tmp_path):
    data = b"sample"
    manifest = {
        "file_name": "test.txt",
        "file_size": len(data) + 1,
        "chunk_count": 1,
        "chunks": [
            {"index": 0, "size": len(data), "sha256": sha256(data)}
        ],
    }

    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    (chunks_dir / sha256(data)).write_bytes(data)

    with pytest.raises(FileAssemblyError):
        assemble_file(manifest, chunks_dir, tmp_path / "downloads")
