
"""Coordinate peer downloads and verified local chunk caching."""

import re

from backend.chunk_store import ChunkStore
from backend.config import Settings
from backend.peer_client import PeerTransferError, download_chunk


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class PeerManager:
    """Download chunks from peers and cache them locally."""

    def __init__(self, settings: Settings):
        self.chunk_store = ChunkStore(settings)

    def get_chunk(
        self,
        chunk_hash: str,
        peer_host: str,
        peer_port: int,
        timeout: float = 10.0,
    ) -> bytes:
        """Preserve the existing single-peer interface."""

        return self.get_chunk_from_peers(
            chunk_hash=chunk_hash,
            peers=[
                {
                    "host": peer_host,
                    "transfer_port": peer_port,
                }
            ],
            timeout=timeout,
        )

    def get_chunk_from_peers(
        self,
        chunk_hash: str,
        peers: list[dict],
        timeout: float = 10.0,
    ) -> bytes:
        """Use the local cache, then try each peer until one succeeds."""

        # 1. Validate the hash before using it in any filesystem path.
        if (
            not isinstance(chunk_hash, str)
            or not SHA256_PATTERN.fullmatch(chunk_hash)
        ):
            raise ValueError("Invalid SHA-256 chunk hash.")

        # 2. Check the local cache.
        try:
            return self.chunk_store.get_chunk(chunk_hash)

        except FileNotFoundError:
            pass

        except ValueError:
            # Remove only the cache entry addressed by the validated hash.
            cache_path = self.chunk_store.chunks_dir / chunk_hash
            cache_path.unlink(missing_ok=True)

        # 3. Try each peer in order.
        last_error: Exception | None = None

        for peer in peers:
            if not isinstance(peer, dict):
                continue

            host = peer.get("host")
            port = peer.get("transfer_port")

            if (
                not isinstance(host, str)
                or not host.strip()
                or not isinstance(port, int)
                or isinstance(port, bool)
                or not 1 <= port <= 65535
            ):
                continue

            try:
                data = download_chunk(
                    peer_host=host,
                    peer_port=port,
                    chunk_hash=chunk_hash,
                    timeout=timeout,
                )

                # Store only content verified against the expected hash.
                self.chunk_store.store_chunk(
                    data=data,
                    expected_hash=chunk_hash,
                )

                return data

            except (PeerTransferError, ValueError) as exc:
                # Remember the failure and continue to the next peer.
                last_error = exc

        # 4. Report failure if no peer could provide the chunk.
        if last_error is not None:
            raise last_error

        raise PeerTransferError(
            f"No available peer could provide chunk {chunk_hash}"
        )
