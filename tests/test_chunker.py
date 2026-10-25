import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from backend.chunker import build_manifest, sha256_bytes


class TestChunker(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_path = Path(self.temp_dir.name)

    def create_file(self, name, data):
        path = self.temp_path / name
        path.write_bytes(data)
        return path

    def test_normal_file(self):
        path = self.create_file("hello.txt", b"Hello World")

        manifest = build_manifest(path, chunk_size=5)

        self.assertEqual(manifest["file_name"], "hello.txt")
        self.assertEqual(manifest["file_size"], 11)
        self.assertEqual(manifest["chunk_size"], 5)
        self.assertEqual(manifest["chunk_count"], 3)
        self.assertEqual(
            [chunk["size"] for chunk in manifest["chunks"]],
            [5, 5, 1],
        )

    def test_chunk_hashes(self):
        path = self.create_file("data.bin", b"Hello World")

        manifest = build_manifest(path, chunk_size=5)

        expected_hashes = [
            hashlib.sha256(b"Hello").hexdigest(),
            hashlib.sha256(b" Worl").hexdigest(),
            hashlib.sha256(b"d").hexdigest(),
        ]

        actual_hashes = [
            chunk["sha256"] for chunk in manifest["chunks"]
        ]

        self.assertEqual(actual_hashes, expected_hashes)

    def test_empty_file(self):
        path = self.create_file("empty.txt", b"")

        manifest = build_manifest(path, chunk_size=5)

        self.assertEqual(manifest["file_size"], 0)
        self.assertEqual(manifest["chunk_count"], 0)
        self.assertEqual(manifest["chunks"], [])

    def test_file_larger_than_one_chunk(self):
        data = b"A" * 12
        path = self.create_file("large.bin", data)

        manifest = build_manifest(path, chunk_size=5)

        self.assertEqual(manifest["chunk_count"], 3)
        self.assertEqual(
            [chunk["size"] for chunk in manifest["chunks"]],
            [5, 5, 2],
        )

    def test_sha256_bytes(self):
        self.assertEqual(
            sha256_bytes(b"abc"),
            hashlib.sha256(b"abc").hexdigest(),
        )

    def test_manifest_is_json_serializable(self):
        path = self.create_file("sample.txt", b"Test data")

        manifest = build_manifest(path, chunk_size=4)

        serialized = json.dumps(manifest)
        restored = json.loads(serialized)

        self.assertEqual(restored["file_name"], "sample.txt")
        self.assertEqual(restored["chunk_count"], 3)

    def test_invalid_chunk_size(self):
        path = self.create_file("sample.txt", b"Test")

        with self.assertRaises(ValueError):
            build_manifest(path, chunk_size=0)

        with self.assertRaises(ValueError):
            build_manifest(path, chunk_size=-1)

    def test_missing_file(self):
        path = self.temp_path / "missing.txt"

        with self.assertRaises(FileNotFoundError):
            build_manifest(path)


if __name__ == "__main__":
    unittest.main()
