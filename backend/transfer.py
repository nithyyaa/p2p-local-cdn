"""TCP server for peer-to-peer chunk transfers."""

import hashlib
import json
import logging
import socketserver
from pathlib import Path

from backend.chunk_store import ChunkStore
from backend.config import Settings

logger = logging.getLogger("p2p.transfer")

MAX_REQUEST_BYTES = 4096
MAX_CHUNK_BYTES = 64 * 1024 * 1024


class ChunkTransferHandler(socketserver.StreamRequestHandler):
    """Handle requests for individual SHA-256-addressed chunks."""

    def handle(self):
        try:
            raw_request = self.rfile.readline(MAX_REQUEST_BYTES + 1)

            if not raw_request or len(raw_request) > MAX_REQUEST_BYTES:
                self._send_error("Invalid request")
                return

            try:
                request = json.loads(raw_request.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_error("Malformed JSON")
                return

            if not isinstance(request, dict):
                self._send_error("Request must be a JSON object")
                return

            chunk_hash = request.get("hash")

            if (
                not isinstance(chunk_hash, str)
                or len(chunk_hash) != 64
                or any(c not in "0123456789abcdef" for c in chunk_hash)
            ):
                self._send_error("Invalid chunk hash")
                return

            try:
                data = self.server.chunk_store.get_chunk(chunk_hash)
            except FileNotFoundError:
                self._send_error("Chunk not found")
                return
            except ValueError:
                self._send_error("Chunk integrity verification failed")
                return

            if len(data) > MAX_CHUNK_BYTES:
                self._send_error("Chunk exceeds transfer limit")
                return

            # Header is one JSON line; payload follows as exact-length bytes.
            header = {
                "status": "ok",
                "hash": chunk_hash,
                "size": len(data),
            }
            self.wfile.write(
                json.dumps(header).encode("utf-8") + b"\n"
            )
            self.wfile.write(data)
            self.wfile.flush()

        except (ConnectionError, OSError):
            logger.warning("Peer disconnected during chunk transfer")

    def _send_error(self, message: str):
        response = {"status": "error", "message": message}
        self.wfile.write(json.dumps(response).encode("utf-8") + b"\n")
        self.wfile.flush()


class _ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ChunkTransferServer:
    """Manage a TCP server that serves verified chunks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.chunk_store = ChunkStore(settings)
        self._server = None

    def start(self):
        """Start the TCP receiver in a background thread."""
        if self._server is not None:
            raise RuntimeError("Transfer server is already running")

        handler = ChunkTransferHandler
        server = _ThreadedTCPServer(
            (self.settings.api_host, self.settings.transfer_port),
            handler,
        )
        server.chunk_store = self.chunk_store

        import threading

        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever,
            name="p2p-chunk-transfer",
            daemon=True,
        )
        self._thread.start()

        logger.info(
            "TCP chunk transfer listening on %s:%d",
            self.settings.api_host,
            self.settings.transfer_port,
        )

    def stop(self):
        """Stop the TCP receiver and release its socket."""
        if self._server is None:
            return

        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._server = None