
"""Tests for peer downloads and local chunk caching."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.chunk_store import ChunkStore
from backend.config import load_settings
from backend.peer_manager import PeerManager


class TestPeerManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        base_settings = load_settings()
        self.settings = base_settings.__class__(
            **{
                **base_settings.__dict__,
                "storage_dir": Path(self.temp_dir.name),
            }
        )

        self.manager = PeerManager(self.settings)
        self.data = b"Hello from a remote CDN peer!"
        self.chunk_hash = hashlib.sha256(self.data).hexdigest()

    @patch("backend.peer_manager.download_chunk")
    def test_downloads_and_caches_missing_chunk(self, mock_download):
        mock_download.return_value = self.data

        result = self.manager.get_chunk(
            self.chunk_hash, "127.0.0.1", 9100
        )

        self.assertEqual(result, self.data)
        mock_download.assert_called_once_with(
            peer_host="127.0.0.1",
            peer_port=9100,
            chunk_hash=self.chunk_hash,
            timeout=10.0,
        )
        self.assertEqual(
            ChunkStore(self.settings).get_chunk(self.chunk_hash),
            self.data,
        )

    @patch("backend.peer_manager.download_chunk")
    def test_uses_local_cache_without_downloading(self, mock_download):
        ChunkStore(self.settings).store_chunk(
            self.data, self.chunk_hash
        )

        result = self.manager.get_chunk(
            self.chunk_hash, "127.0.0.1", 9100
        )

        self.assertEqual(result, self.data)
        mock_download.assert_not_called()

    @patch("backend.peer_manager.download_chunk")
    def test_propagates_peer_transfer_failure(self, mock_download):
        from backend.peer_client import PeerTransferError

        mock_download.side_effect = PeerTransferError(
            "Peer unavailable"
        )

        with self.assertRaises(PeerTransferError):
            self.manager.get_chunk(
                self.chunk_hash, "127.0.0.1", 9100
            )

    @patch("backend.peer_manager.download_chunk")
    def test_rejects_corrupted_download(self, mock_download):
        mock_download.return_value = b"corrupted content"

        with self.assertRaises(ValueError):
            self.manager.get_chunk(
                self.chunk_hash, "127.0.0.1", 9100
            )


if __name__ == "__main__":
    unittest.main()
