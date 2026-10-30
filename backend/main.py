
"""FastAPI entry point for one P2P LAN CDN node.

Run from the project folder with the virtual environment active:
    python -m backend.main
"""

from __future__ import annotations

import hashlib
import hmac
import httpx
import ipaddress
import logging
import os
import platform
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.config import ensure_storage_dirs, load_or_create_node_id, settings
from backend.chunker import build_manifest
from backend.chunk_store import ChunkStore
from backend.discovery import PeerDiscovery
from backend.file_assembler import assemble_file, FileAssemblyError
from backend.origin import create_origin_app
from backend.peer_manager import PeerManager
from backend.transfer import ChunkTransferServer
from backend.transfer_tracker import TransferTracker

logger = logging.getLogger("p2p.node")
_ROUTE_PROBE = ("192.0.2.1", 9)


class ManifestRequest(BaseModel):
    """Request a manifest for a file available from the origin."""

    file_name: str = Field(min_length=1, max_length=255)


class PeerManifestRequest(BaseModel):
    """Request a file manifest from a discovered peer."""

    file_name: str = Field(min_length=1, max_length=255)
    peer_host: str = Field(min_length=1, max_length=255)


class DownloadRequest(BaseModel):
    """Request a complete file assembled from verified chunks."""

    manifest: dict[str, Any]
    peer_host: str | None = None
    peer_port: int | None = None


def _is_lan_candidate(ip: str) -> bool:
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False

    return not (
        addr.is_loopback
        or addr.is_link_local
        or addr.is_unspecified
        or addr.is_multicast
    )


def detect_ipv4_addresses() -> tuple[str | None, list[str]]:
    """Return the primary IPv4 address and other usable IPv4 addresses."""
    primary: str | None = None
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        probe.connect(_ROUTE_PROBE)
        candidate = probe.getsockname()[0]

        if _is_lan_candidate(candidate):
            primary = candidate

    except OSError:
        pass

    finally:
        probe.close()

    addresses = [primary] if primary else []

    try:
        infos = socket.getaddrinfo(
            socket.gethostname(),
            None,
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )
    except socket.gaierror:
        infos = []

    for info in infos:
        ip = info[4][0]

        if _is_lan_candidate(ip) and ip not in addresses:
            addresses.append(ip)

    return primary, addresses


def _count_cached_chunks() -> tuple[int, int]:
    """Return the number of cached chunks and total cached bytes."""
    count = 0
    total_bytes = 0
    chunks_dir = Path(settings.chunks_dir)

    if chunks_dir.exists():
        for path in chunks_dir.iterdir():
            if path.is_file():
                try:
                    count += 1
                    total_bytes += path.stat().st_size
                except OSError:
                    logger.debug(
                        "Could not stat cache file %s",
                        path,
                        exc_info=True,
                    )

    return count, total_bytes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the node and manage its background services."""
    ensure_storage_dirs(settings)

    app.state.node_id = load_or_create_node_id(settings)
    app.state.started_at = datetime.now(timezone.utc)
    app.state.started_monotonic = time.monotonic()
    app.state.peer_manager = PeerManager(settings)
    app.state.transfer_tracker = TransferTracker()

    transfer_server = ChunkTransferServer(settings)
    transfer_server.start()
    app.state.transfer_server = transfer_server

    discovery = PeerDiscovery(settings)
    app.state.peer_discovery = discovery

    try:
        discovery.start()
        discovery.announce_periodically(
            node_id=app.state.node_id,
            node_name=settings.node_name,
        )

        logger.info(
            "UDP peer discovery started on port %s",
            settings.discovery_port,
        )

        logger.info(
            "Node %s (%s) ready. Storage folder: %s",
            app.state.node_id,
            settings.node_name,
            settings.storage_dir,
        )

        yield

    finally:
        try:
            discovery.stop()
        except Exception:
            logger.exception("Error stopping UDP peer discovery")

        try:
            transfer_server.stop()
        except Exception:
            logger.exception("Error stopping TCP chunk-transfer server")


app = FastAPI(
    title="P2P LAN CDN node",
    version="0.3.0",
    lifespan=lifespan,
)


# API key is read from the environment when this module is imported.
# Set P2P_API_KEY before starting the backend.
API_KEY = os.environ.get("P2P_API_KEY", "").strip()
PUBLIC_PATHS = {"/", "/api/health"}


@app.middleware("http")
async def api_key_authentication(request: Request, call_next):
    """Require an API key for all HTTP routes except basic health checks."""
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    if not API_KEY:
        return JSONResponse(
            status_code=503,
            content={"detail": "API authentication is not configured."},
        )

    

    return await call_next(request)

# Allow the Vite development frontend to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.0.105:5173",
        "http://10.134.47.25:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/origin", create_origin_app(settings.origin_files_dir))


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "p2p-lan-cdn-node",
        "health": "/api/health",
        "peers": "/api/peers",
        "stats": "/api/stats",
        "transfers": "/api/transfers",
        "api_docs": "/docs",
    }


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    """Report node health, network addresses, ports, and uptime."""
    state = request.app.state
    primary, addresses = detect_ipv4_addresses()
    server = request.scope.get("server")
    client = request.client
    started_at = getattr(state, "started_at", None)

    uptime = (
        max(0.0, time.monotonic() - state.started_monotonic)
        if started_at
        else 0.0
    )

    return {
        "status": "ok",
        "node_id": getattr(state, "node_id", None),
        "node_name": settings.node_name,
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "primary_ipv4": primary,
        "lan_ipv4": addresses,
        "served_on": f"{server[0]}:{server[1]}" if server else None,
        "requested_by": client.host if client else None,
        "ports": {
            "api_tcp": server[1] if server else settings.api_port,
            "transfer_tcp": settings.transfer_port,
            "discovery_udp": settings.discovery_port,
        },
        "chunk_size_bytes": settings.chunk_size,
        "started_at": (
            started_at.isoformat(timespec="seconds")
            if started_at
            else None
        ),
        "uptime_seconds": round(uptime, 1),
    }


@app.get("/api/peers")
def list_peers(request: Request) -> dict[str, Any]:
    """List currently discovered peers, excluding this node."""
    state = request.app.state
    discovery: PeerDiscovery = state.peer_discovery

    peers = [
        peer
        for peer in discovery.get_peers()
        if peer.get("node_id") != state.node_id
    ]

    return {
        "status": "ok",
        "node_id": state.node_id,
        "peer_count": len(peers),
        "peers": peers,
    }


@app.get("/api/stats")
def stats(request: Request) -> dict[str, Any]:
    """Return node, cache, and recent transfer statistics."""
    cached_chunks, cached_bytes = _count_cached_chunks()
    peer_count = len(request.app.state.peer_discovery.get_peers())

    uptime = max(
        0.0,
        time.monotonic() - request.app.state.started_monotonic,
    )

    tracker: TransferTracker = request.app.state.transfer_tracker
    transfers = tracker.list_records()

    total_transfers = len(transfers)
    completed_transfers = sum(
        1 for transfer in transfers
        if transfer.get("status") == "completed"
    )
    failed_transfers = sum(
        1 for transfer in transfers
        if transfer.get("status") == "failed"
    )
    active_transfers = sum(
        1 for transfer in transfers
        if transfer.get("status") == "downloading"
    )

    peer_bytes = sum(
        transfer.get("peer_bytes", 0)
        for transfer in transfers
    )
    origin_bytes = sum(
        transfer.get("origin_bytes", 0)
        for transfer in transfers
    )
    cache_bytes = sum(
        transfer.get("cache_bytes", 0)
        for transfer in transfers
    )

    total_transferred_bytes = peer_bytes + origin_bytes + cache_bytes
    estimated_origin_bytes_saved = peer_bytes + cache_bytes

    return {
        "status": "ok",
        "node_id": request.app.state.node_id,
        "node_name": settings.node_name,
        "uptime_seconds": round(uptime, 1),
        "peer_count": peer_count,
        "cached_chunks": cached_chunks,
        "cached_bytes": cached_bytes,
        "cached_megabytes": round(cached_bytes / (1024 * 1024), 3),
        "transfer_metrics": {
            "total_transfers": total_transfers,
            "completed_transfers": completed_transfers,
            "failed_transfers": failed_transfers,
            "active_transfers": active_transfers,
            "peer_bytes": peer_bytes,
            "origin_bytes": origin_bytes,
            "cache_bytes": cache_bytes,
            "total_transferred_bytes": total_transferred_bytes,
            "estimated_origin_bytes_saved": estimated_origin_bytes_saved,
            "accounting_scope": "most_recent_tracked_transfers",
        },
        "ports": {
            "api": settings.api_port,
            "transfer": settings.transfer_port,
            "discovery": settings.discovery_port,
        },
    }


@app.get("/api/transfers")
def list_transfers(request: Request) -> dict[str, Any]:
    """Return recent file transfer records for the dashboard."""
    records = request.app.state.transfer_tracker.list_records()

    for record in records:
        elapsed = record.get("elapsed_seconds", 0.0)

        if record.get("status") == "downloading":
            elapsed = max(
                0.001,
                time.monotonic()
                - _transfer_start_monotonic(request, record["id"]),
            )

        transferred = record.get("bytes_done", 0)
        record["speed"] = (
            round(transferred / elapsed, 2) if elapsed > 0 else 0.0
        )

        if record.get("status") == "downloading":
            record["bytes"] = transferred

    return {"status": "ok", "transfers": records}


def _transfer_start_monotonic(request: Request, transfer_id: str) -> float:
    """Read the internal start timestamp without exposing it through the API."""
    tracker = request.app.state.transfer_tracker

    with tracker._lock:
        record = tracker._find(transfer_id)

        if record is None:
            return time.monotonic()

        return float(record["_started_monotonic"])


@app.get("/api/chunks/{chunk_hash}")
def get_chunk_from_peer(
    chunk_hash: str,
    peer_host: str,
    peer_port: int,
    request: Request,
) -> dict[str, Any]:
    """Fetch a chunk from a peer and cache it locally."""
    if len(chunk_hash) != 64 or any(
        c not in "0123456789abcdef" for c in chunk_hash.lower()
    ):
        raise HTTPException(
            status_code=400,
            detail="chunk_hash must be a SHA-256 hex digest.",
        )

    try:
        data = request.app.state.peer_manager.get_chunk(
            chunk_hash=chunk_hash,
            peer_host=peer_host,
            peer_port=peer_port,
        )

    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        logger.exception("Peer chunk download failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve the requested chunk from the peer.",
        ) from exc

    return {
        "status": "ok",
        "chunk_hash": chunk_hash,
        "size": len(data),
        "cached_locally": True,
    }


@app.post("/api/files/peer-manifest")
def create_peer_manifest(body: PeerManifestRequest, request: Request) -> dict[str, Any]:
    """Fetch a manifest from a discovered peer using server-side API authentication."""
    file_name = body.file_name.strip()

    if (
        not file_name
        or Path(file_name).name != file_name
        or "/" in file_name
        or "\\" in file_name
        or file_name in {".", ".."}
    ):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    try:
        peer_ip = ipaddress.ip_address(body.peer_host)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid peer IP address.",
        ) from exc

    if not peer_ip.is_private:
        raise HTTPException(
            status_code=400,
            detail="Peer must have a private LAN IP address.",
        )

    # Only allow peers currently advertised by this node's discovery service.
    discovery: PeerDiscovery = request.app.state.peer_discovery
    discovered_hosts = {
        str(peer.get("host"))
        for peer in discovery.get_peers()
        if peer.get("host")
        and peer.get("node_id") != request.app.state.node_id
    }
    if str(peer_ip) not in discovered_hosts:
        raise HTTPException(
            status_code=403,
            detail="The requested host is not a currently discovered peer.",
        )

    if not API_KEY:
        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured.",
        )

    peer_url = f"http://{peer_ip}:{settings.api_port}/api/files/manifest"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                peer_url,
                headers={"X-API-Key": API_KEY},
                json={"file_name": file_name},
            )
    except httpx.RequestError as exc:
        logger.warning("Could not contact peer manifest endpoint: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Could not contact the peer to prepare the file.",
        ) from exc

    if response.status_code != 200:
        detail = "The peer could not prepare the requested file."
        try:
            peer_detail = response.json().get("detail")
            if isinstance(peer_detail, str) and peer_detail:
                detail = peer_detail
        except (ValueError, AttributeError):
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="The peer returned an invalid manifest response.",
        ) from exc

    if not isinstance(data, dict) or not isinstance(data.get("manifest"), dict):
        raise HTTPException(
            status_code=502,
            detail="The peer returned an invalid manifest response.",
        )

    return data


@app.post("/api/files/manifest")
def create_file_manifest(body: ManifestRequest) -> dict[str, Any]:
    """Create a manifest for a file available in the origin directory."""
    file_name = body.file_name

    if (
        Path(file_name).name != file_name
        or "/" in file_name
        or "\\" in file_name
        or file_name in {".", ".."}
    ):
        raise HTTPException(status_code=400, detail="Invalid filename.")

    origin_file = settings.origin_files_dir / file_name
    if not origin_file.is_file():
        raise HTTPException(status_code=404, detail="Origin file not found.")

    try:
        manifest = build_manifest(
            origin_file,
            chunk_size=settings.chunk_size,
        )

        chunk_store = ChunkStore(settings)

        with origin_file.open("rb") as file:
            for chunk_info in manifest["chunks"]:
                file.seek(
                    chunk_info["index"] * manifest["chunk_size"]
                )
                chunk_data = file.read(chunk_info["size"])
                actual_hash = hashlib.sha256(chunk_data).hexdigest()
                expected_hash = chunk_info["sha256"]

                if actual_hash != expected_hash:
                    raise ValueError(
                        "File content changed while creating the manifest."
                    )

                chunk_store.store_chunk(
                    data=chunk_data,
                    expected_hash=expected_hash,
                )

    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.exception("Could not create manifest or cache file chunks")
        raise HTTPException(
            status_code=500,
            detail="Unable to create the manifest or cache the file's chunks.",
        ) from exc

    return {"status": "ok", "manifest": manifest}


@app.post("/api/files/download")
def download_complete_file(
    body: DownloadRequest,
    request: Request,
) -> FileResponse:
    """Assemble a complete file using cache, peer, or origin fallback."""
    if (body.peer_host is None) != (body.peer_port is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both peer_host and peer_port, or neither.",
        )

    if body.peer_host is not None:
        try:
            ipaddress.ip_address(body.peer_host)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="peer_host must be a valid IP address.",
            ) from exc

        if body.peer_port is None or not 1 <= body.peer_port <= 65535:
            raise HTTPException(
                status_code=400,
                detail="peer_port must be between 1 and 65535.",
            )

    manifest = body.manifest
    chunks = manifest.get("chunks")

    if not isinstance(chunks, list):
        raise HTTPException(
            status_code=400,
            detail="Manifest must contain a chunks list.",
        )

    file_name = str(
        manifest.get("file_name")
        or manifest.get("filename")
        or manifest.get("name")
        or manifest.get("file")
        or "download"
    )

    # Reject paths and traversal attempts.
    if (
        Path(file_name).name != file_name
        or "/" in file_name
        or "\\" in file_name
        or file_name in {".", ".."}
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename in manifest.",
        )

    peer_label = (
        f"{body.peer_host}:{body.peer_port}"
        if body.peer_host is not None and body.peer_port is not None
        else "cache/origin"
    )

    tracker: TransferTracker = request.app.state.transfer_tracker

    transfer_id = tracker.start(
        name=file_name,
        peer=peer_label,
        total_chunks=len(chunks),
        total_bytes=manifest.get("file_size", 0),
    )

    def retrieve_chunk(chunk_hash: str) -> bytes:
        """Retrieve a chunk from cache, peer, or origin and verify it."""
        peer_manager: PeerManager = request.app.state.peer_manager

        chunk_info = next(
            (
                chunk
                for chunk in chunks
                if isinstance(chunk, dict)
                and chunk.get("sha256") == chunk_hash
            ),
            None,
        )

        if chunk_info is None:
            raise FileAssemblyError(
                f"Chunk {chunk_hash} is not present in the manifest."
            )

        # 1. Check the local cache.
        try:
            data = peer_manager.chunk_store.get_chunk(chunk_hash)

            tracker.update_chunk(
                transfer_id=transfer_id,
                chunk_bytes=len(data),
                source="cache",
            )
            return data

        except (FileNotFoundError, ValueError):
            pass

        # 2. Discover peers automatically, unless one was explicitly specified.
        discovery: PeerDiscovery = request.app.state.peer_discovery

        if body.peer_host is not None and body.peer_port is not None:
            candidate_peers = [
                {
                    "host": body.peer_host,
                    "transfer_port": body.peer_port,
                }
            ]
        else:
            candidate_peers = [
                peer
                for peer in discovery.get_peers()
                if peer.get("node_id") != request.app.state.node_id
            ]

        if candidate_peers:
            try:
                data = peer_manager.get_chunk_from_peers(
                    chunk_hash=chunk_hash,
                    peers=candidate_peers,
                )

                # Verify again before returning the data.
                if hashlib.sha256(data).hexdigest() != chunk_hash:
                    raise FileAssemblyError(
                        f"Peer chunk failed SHA-256 verification: {chunk_hash}."
                    )

                tracker.update_chunk(
                    transfer_id=transfer_id,
                    chunk_bytes=len(data),
                    source="peer",
                )
                return data

            except Exception as exc:
                logger.warning(
                    "Peer retrieval failed for chunk %s: %s. "
                    "Attempting origin fallback.",
                    chunk_hash,
                    exc,
                )

        # 3. Fall back to the file in the configured origin directory.
        origin_dir = Path(settings.origin_files_dir).resolve()
        origin_path = (origin_dir / file_name).resolve()
        if origin_path.parent != origin_dir:
            raise FileAssemblyError("Invalid origin filename.")

        if not origin_path.is_file():
            raise FileAssemblyError(
                f"Chunk {chunk_hash} is unavailable in cache, peer, and origin."
            )

        chunk_size = manifest.get("chunk_size")
        chunk_index = chunk_info.get("index")
        expected_size = chunk_info.get("size")

        if (
            not isinstance(chunk_size, int)
            or isinstance(chunk_size, bool)
            or chunk_size <= 0
            or not isinstance(chunk_index, int)
            or isinstance(chunk_index, bool)
            or chunk_index < 0
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
        ):
            raise FileAssemblyError("Invalid chunk metadata in manifest.")

        with origin_path.open("rb") as origin_file:
            origin_file.seek(chunk_index * chunk_size)
            data = origin_file.read(expected_size)

        if len(data) != expected_size:
            raise FileAssemblyError(
                f"Origin returned an incomplete chunk: {chunk_hash}."
            )

        if hashlib.sha256(data).hexdigest() != chunk_hash:
            raise FileAssemblyError(
                f"Origin chunk failed SHA-256 verification: {chunk_hash}."
            )

        # Store only verified data.
        peer_manager.chunk_store.store_chunk(
            data=data,
            expected_hash=chunk_hash,
        )

        tracker.update_chunk(
            transfer_id=transfer_id,
            chunk_bytes=len(data),
            source="origin",
        )

        return data

    try:
        output_path = assemble_file(
            manifest=manifest,
            chunks_dir=settings.chunks_dir,
            output_dir=settings.downloads_dir,
            get_chunk=retrieve_chunk,
        )

        file_bytes = output_path.stat().st_size

    except FileAssemblyError as exc:
        tracker.finish(transfer_id, "failed")
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        tracker.finish(transfer_id, "failed")
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        tracker.finish(transfer_id, "failed")
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        tracker.finish(transfer_id, "failed")
        logger.exception("Complete-file assembly failed")

        raise HTTPException(
            status_code=502,
            detail="Unable to assemble the requested file.",
        ) from exc

    tracker.finish(
        transfer_id,
        "completed",
        file_bytes=file_bytes,
    )

    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type="application/octet-stream",
    )


def main() -> None:
    """Start the Uvicorn API server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    )

    port = settings.api_port
    host = ipaddress.IPv4Address(settings.api_host)
    primary, addresses = detect_ipv4_addresses()

    logger.info(
        "Starting node '%s' on %s:%d",
        settings.node_name,
        settings.api_host,
        port,
    )

    logger.info(
        "Test on this laptop: http://127.0.0.1:%d/api/health",
        port,
    )

    if host.is_loopback:
        logger.warning(
            "P2P_API_HOST is %s, so other laptops cannot connect. "
            "Use 0.0.0.0 for LAN access.",
            settings.api_host,
        )
    else:
        lan_urls = addresses if host.is_unspecified else [settings.api_host]

        if not lan_urls:
            logger.warning(
                "No LAN IPv4 address found. Connect to the hotspot, then restart."
            )

        for ip in lan_urls:
            note = " (default route)" if ip == primary else ""
            logger.info(
                "Test from another laptop: http://%s:%d/api/health%s",
                ip,
                port,
                note,
            )

        if len(lan_urls) > 1:
            logger.info(
                "Use the address shown under the active Wi-Fi adapter in ipconfig."
            )

    uvicorn.run(
        app,
        host=settings.api_host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
