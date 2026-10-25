import hashlib
import json
import socket
import threading
import unittest

from backend.peer_client import download_chunk, PeerTransferError


class TestPeerClient(unittest.TestCase):

    def start_mock_peer(self, response_header, data=b""):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def handle_client():
            try:
                conn, _ = server.accept()
                with conn:
                    reader = conn.makefile("rb")
                    reader.readline()  # Read the client's chunk request.

                    conn.sendall(
                        json.dumps(response_header).encode("utf-8") + b"\n"
                    )
                    if data:
                        conn.sendall(data)
            finally:
                server.close()

        thread = threading.Thread(target=handle_client, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)

        return port

    def test_successful_download(self):
        data = b"Hello from a peer!"
        digest = hashlib.sha256(data).hexdigest()
        port = self.start_mock_peer(
            {"status": "ok", "hash": digest, "size": len(data)},
            data,
        )

        received = download_chunk("127.0.0.1", port, digest)

        self.assertEqual(received, data)

    def test_peer_reports_missing_chunk(self):
        digest = hashlib.sha256(b"missing").hexdigest()
        port = self.start_mock_peer(
            {"status": "error", "message": "Chunk not found"}
        )

        with self.assertRaises(PeerTransferError):
            download_chunk("127.0.0.1", port, digest)

    def test_reject_wrong_hash_in_header(self):
        data = b"test data"
        requested_hash = hashlib.sha256(data).hexdigest()
        wrong_hash = hashlib.sha256(b"different data").hexdigest()

        port = self.start_mock_peer(
            {"status": "ok", "hash": wrong_hash, "size": len(data)},
            data,
        )

        with self.assertRaises(PeerTransferError):
            download_chunk("127.0.0.1", port, requested_hash)

    def test_reject_corrupted_content(self):
        expected = b"original content"
        corrupted = b"corrupted content"
        digest = hashlib.sha256(expected).hexdigest()

        port = self.start_mock_peer(
            {"status": "ok", "hash": digest, "size": len(corrupted)},
            corrupted,
        )

        with self.assertRaises(PeerTransferError):
            download_chunk("127.0.0.1", port, digest)

    def test_reject_invalid_hash(self):
        with self.assertRaises(ValueError):
            download_chunk("127.0.0.1", 9100, "invalid")


if __name__ == "__main__":
    unittest.main()
