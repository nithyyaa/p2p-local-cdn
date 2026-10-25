"""TCP client for downloading and verifying chunks from CDN peers."""

import hashlib
import json
import socket


MAX_HEADER_BYTES = 4096
MAX_CHUNK_BYTES = 64 * 1024 * 1024


class PeerTransferError(Exception):
    """Raised when a peer transfer fails."""


def download_chunk(
    peer_host: str,
    peer_port: int,
    chunk_hash: str,
    timeout: float = 10.0,
) -> bytes:
    """Download a chunk from a peer and verify its SHA-256 hash."""

    if (
        not isinstance(chunk_hash, str)
        or len(chunk_hash) != 64
        or any(char not in "0123456789abcdef" for char in chunk_hash)
    ):
        raise ValueError("Invalid SHA-256 chunk hash")

    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    try:
        with socket.create_connection(
            (peer_host, peer_port),
            timeout=timeout,
        ) as sock:
            sock.settimeout(timeout)

            request = json.dumps({"hash": chunk_hash}).encode("utf-8") + b"\n"
            sock.sendall(request)

            with sock.makefile("rb") as reader:
                raw_header = reader.readline(MAX_HEADER_BYTES + 1)

                if (
                    not raw_header
                    or len(raw_header) > MAX_HEADER_BYTES
                    or not raw_header.endswith(b"\n")
                ):
                    raise PeerTransferError("Invalid response header")

                try:
                    header = json.loads(raw_header.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise PeerTransferError("Malformed response header") from exc

                if not isinstance(header, dict):
                    raise PeerTransferError("Response header must be a JSON object")

                if header.get("status") != "ok":
                    message = header.get("message", "Peer transfer failed")
                    raise PeerTransferError(str(message))

                if header.get("hash") != chunk_hash:
                    raise PeerTransferError("Peer returned an unexpected chunk hash")

                size = header.get("size")

                if (
                    isinstance(size, bool)
                    or not isinstance(size, int)
                    or size < 0
                    or size > MAX_CHUNK_BYTES
                ):
                    raise PeerTransferError("Invalid chunk size in response")

                chunks = []
                remaining = size

                while remaining:
                    block = reader.read(min(remaining, 64 * 1024))

                    if not block:
                        raise PeerTransferError(
                            "Connection closed before the chunk was fully received"
                        )

                    chunks.append(block)
                    remaining -= len(block)

                data = b"".join(chunks)

    except (socket.timeout, OSError) as exc:
        raise PeerTransferError(f"Could not download chunk: {exc}") from exc

    actual_hash = hashlib.sha256(data).hexdigest()

    if actual_hash != chunk_hash:
        raise PeerTransferError("Downloaded chunk failed SHA-256 verification")

    return data
