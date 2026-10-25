import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path

from backend.config import load_settings
from backend.transfer import ChunkTransferServer


class TestChunkTransferServer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        base = load_settings()
        self.settings = base.__class__(
            **{
                **base.__dict__,
                "storage_dir": Path(self.temp_dir.name),
                "transfer_port": 0,
                "api_host": "127.0.0.1",
            }
        )

        self.server = ChunkTransferServer(self.settings)
        self.server.start()
        self.addCleanup(self.server.stop)

        self.port = self.server._server.server_address[1]

    def request_chunk(self, request):
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            sock.sendall(json.dumps(request).encode() + b"\n")

            reader = sock.makefile("rb")
            header = json.loads(reader.readline().decode())

            if header.get("status") == "ok":
                data = reader.read(header["size"])
                return header, data

            return header, b""

    def test_transfer_existing_chunk(self):
        data = b"Hello from a peer!"
        digest = hashlib.sha256(data).hexdigest()
        self.server.chunk_store.store_chunk(data, digest)

        header, received = self.request_chunk({"hash": digest})

        self.assertEqual(header["status"], "ok")
        self.assertEqual(header["hash"], digest)
        self.assertEqual(received, data)

    def test_missing_chunk(self):
        digest = hashlib.sha256(b"missing").hexdigest()

        header, _ = self.request_chunk({"hash": digest})

        self.assertEqual(header["status"], "error")
        self.assertEqual(header["message"], "Chunk not found")

    def test_invalid_hash(self):
        header, _ = self.request_chunk({"hash": "../invalid"})

        self.assertEqual(header["status"], "error")
        self.assertEqual(header["message"], "Invalid chunk hash")

    def test_malformed_json(self):
        with socket.create_connection(("127.0.0.1", self.port)) as sock:
            sock.sendall(b"{not-json}\n")
            reader = sock.makefile("rb")
            response = json.loads(reader.readline().decode())

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["message"], "Malformed JSON")

    def test_non_object_request(self):
        header, _ = self.request_chunk(["not", "an", "object"])

        self.assertEqual(header["status"], "error")
        self.assertEqual(header["message"], "Request must be a JSON object")


if __name__ == "__main__":
    unittest.main()