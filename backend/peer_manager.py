"""Coordinate peer downloads and verified local chunk caching."""

from backend.chunk_store import ChunkStore
from backend.config import Settings
from backend.peer_client import PeerTransferError, download_chunk


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
        """Return a locally cached chunk or download and cache it from a peer."""

        # 1. Try the local cache first.
        try:
            return self.chunk_store.get_chunk(chunk_hash)
        except FileNotFoundError:
            pass

        # 2. Download the missing chunk from the peer.
        data = download_chunk(
            peer_host=peer_host,
            peer_port=peer_port,
            chunk_hash=chunk_hash,
            timeout=timeout,
        )

        # 3. Verify and save it in local storage.
        self.chunk_store.store_chunk(
            data=data,
            expected_hash=chunk_hash,
        )

        # 4. Return the verified content.
        return data
