import hashlib
import tempfile
import unittest
from pathlib import Path

from backend.chunk_store import ChunkStore
from backend.config import load_settings


class TestChunkStore(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.settings = load_settings()
        self.settings = self.settings.__class__(
            **{
                **self.settings.__dict__,
                "storage_dir": Path(self.temp_dir.name),
            }
        )

        self.store = ChunkStore(self.settings)
        self.data = b"Hello from the P2P CDN!"
        self.digest = hashlib.sha256(self.data).hexdigest()

    def test_store_and_retrieve_chunk(self):
        self.store.store_chunk(self.data, self.digest)
        self.assertEqual(self.store.get_chunk(self.digest), self.data)

    def test_reject_wrong_hash(self):
        with self.assertRaises(ValueError):
            self.store.store_chunk(self.data, "0" * 64)

    def test_missing_chunk(self):
        with self.assertRaises(FileNotFoundError):
            self.store.get_chunk(self.digest)

    def test_reject_invalid_hash(self):
        with self.assertRaises(ValueError):
            self.store.get_chunk("../invalid")

    def test_deduplicate_chunk(self):
        first = self.store.store_chunk(self.data, self.digest)
        second = self.store.store_chunk(self.data, self.digest)

        self.assertEqual(first, second)
        self.assertEqual(len(list(self.settings.chunks_dir.iterdir())), 1)

    def test_detect_corrupted_chunk(self):
        path = self.store.store_chunk(self.data, self.digest)
        path.write_bytes(b"corrupted")

        with self.assertRaises(ValueError):
            self.store.get_chunk(self.digest)


if __name__ == "__main__":
    unittest.main()