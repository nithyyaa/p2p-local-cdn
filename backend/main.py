
"""FastAPI entry point for one P2P LAN CDN node.

Start the API, prepare storage folders, expose the health and peer APIs,
mount the HTTP origin server, and manage the TCP chunk-transfer server
and UDP peer-discovery service.

Run from the project folder with the virtual environment active:

    python -m backend.main
"""

from __future__ import annotations

import ipaddress
import logging
import platform
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.chunk_store import ChunkStore
from backend.config import (
    ensure_storage_dirs,
    load_or_create_node_id,
    settings,
)
from backend.discovery import PeerDiscovery
from backend.file_assembler import assemble_file, FileAssemblyError
from backend.origin import create_origin_app
from backend.peer_manager import PeerManager
from backend.chunker import build_manifest
from backend.transfer import ChunkTransferServer

logger = logging.getLogger("p2p.node")

_ROUTE_PROBE = ("192.0.2.1", 9)


class ManifestRequest(BaseModel):
    """Request a manifest for a file available from the origin."""

    file_name: str = Field(min_length=1, max_length=255)


class DownloadRequest(BaseModel):
    """Request assembly of a file from its manifest."""

    manifest: dict[str, Any]
    peer_host: str | None = None
    peer_port: int | None = Field(default=None, ge=1, le=65535)


def detect_ipv4_addresses() -> tuple[str | None, list[str]]:
    """Detect the primary and local IPv4 addresses."""

    primary: str | None = None
    addresses: set[str] = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(_ROUTE_PROBE)
            address = probe.getsockname()[0]
            if address and not address.startswith("127."):
                primary = address
                addresses.add(address)
    except OSError:
        logger.debug("Could not detect primary IPv4 address", exc_info=True)

    try:
        for result in socket.getaddrinfo(
            socket.gethostname(),
            None,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        ):
            address = result[4][0]
            if not address.startswith("127."):
                addresses.add(address)
    except OSError:
        logger.debug("Could not enumerate local IPv4 addresses", exc_info=True)

    return primary, sorted(addresses)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and stop this node's services."""

    ensure_storage_dirs(settings)
    node_id = load_or_create_node_id(settings)

    peer_manager = PeerManager(settings)
    transfer_server = ChunkTransferServer(settings)
    discovery = PeerDiscovery(settings)

    app.state.node_id = node_id
    app.state.peer_manager = peer_manager
    app.state.transfer_server = transfer_server
    app.state.discovery = discovery
    app.state.started_at = datetime.now(timezone.utc)

    try:
        transfer_server.start()
        logger.info(
            "TCP chunk transfer listening on port %s",
            settings.transfer_port,
        )

        discovery.start()
        logger.info(
            "UDP peer discovery started on port %s",
            settings.discovery_port,
        )

        logger.info(
            "Node %s (%s) ready. Storage folder: %s",
            node_id,
            settings.node_name,
            settings.storage_dir,
        )

        yield

    finally:
        try:
            discovery.stop()
        except Exception:
            logger.exception("Error stopping peer discovery")

        try:
            transfer_server.stop()
        except Exception:
            logger.exception("Error stopping TCP transfer server")


app = FastAPI(
    title="P2P LAN CDN",
    description="Peer-to-peer content delivery for local networks.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount(
    "/origin",
    create_origin_app(root_dir=settings.downloads_dir),
)


@app.get("/")
def root() -> dict[str, str]:
    """Return basic node information."""

    return {
        "name": "P2P LAN CDN",
        "node_name": settings.node_name,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    """Return node health and network information."""

    primary, addresses = detect_ipv4_addresses()
    started_at = getattr(request.app.state, "started_at", None)

    uptime = (
        max(
            0.0,
            (datetime.now(timezone.utc) - started_at).total_seconds(),
        )
        if started_at
        else 0.0
    )

    return {
        "status": "ok",
        "node_id": getattr(request.app.state, "node_id", None),
        "node_name": settings.node_name,
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "primary_ipv4": primary,
        "lan_ipv4": addresses,
        "served_on": f"{settings.api_host}:{settings.api_port}",
        "requested_by": (
            request.client.host if request.client else None
        ),
        "ports": {
            "api_tcp": settings.api_port,
            "transfer_tcp": settings.transfer_port,
            "discovery_udp": settings.discovery_port,
        },
        "chunk_size_bytes": settings.chunk_size,
        "started_at": started_at.isoformat() if started_at else None,
        "uptime_seconds": round(uptime, 1),
    }


@app.get("/api/peers")
def list_peers(request: Request) -> dict[str, Any]:
    """Return currently discovered peers."""

    discovery = request.app.state.discovery
    peers = discovery.get_peers()

    return {
        "status": "ok",
        "node_id": request.app.state.node_id,
        "peer_count": len(peers),
        "peers": peers,
    }


@app.get("/api/chunks/{chunk_hash}")
def get_chunk_from_peer(
    chunk_hash: str,
    peer_host: str,
    peer_port: int,
    request: Request,
) -> dict[str, Any]:
    """Fetch a chunk from a peer and cache it locally."""

    try:
        data = request.app.state.peer_manager.get_chunk(
            chunk_hash=chunk_hash,
            peer_host=peer_host,
            peer_port=peer_port,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
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


@app.post("/api/files/manifest")
def create_file_manifest(
    body: ManifestRequest,
) -> dict[str, Any]:
    """Create a manifest and cache the file's chunks locally."""

    file_name = body.file_name

    if (
        Path(file_name).name != file_name
        or file_name in {".", ".."}
        or "/" in file_name
        or "\\" in file_name
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file name.",
        )

    origin_file = Path(settings.downloads_dir) / file_name

    if not origin_file.is_file():
        raise HTTPException(
            status_code=404,
            detail="The requested file is not available from the origin.",
        )

    try:
        manifest = build_manifest(
            origin_file,
            chunk_size=settings.chunk_size,
        )

        chunk_store = ChunkStore(settings)

        with open(origin_file, "rb") as file:
            for chunk_info in manifest["chunks"]:
                file.seek(
                    chunk_info["index"] * manifest["chunk_size"]
                )
                chunk_data = file.read(chunk_info["size"])

                # Verify that the file hasn't changed since manifest creation.
                import hashlib

                actual_hash = hashlib.sha256(chunk_data).hexdigest()
                if actual_hash != chunk_info["sha256"]:
                    raise ValueError(
                        "File content changed while creating the manifest."
                    )

                # Confirm the store_chunk signature in chunk_store.py
                # before relying on this call.
                chunk_store.store_chunk(
    data=chunk_data,
    expected_hash=chunk_info["sha256"],
)

    except (OSError, ValueError) as exc:
        logger.exception("Could not create manifest or cache file chunks")
        raise HTTPException(
            status_code=500,
            detail="Unable to create a manifest or cache the file's chunks.",
        ) from exc

    return {
        "status": "ok",
        "manifest": manifest,
    }


@app.post("/api/files/download")
def download_complete_file(
    body: DownloadRequest,
    request: Request,
) -> FileResponse:
    """Assemble a file from verified local or peer-provided chunks."""

    if (body.peer_host is None) != (body.peer_port is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both peer_host and peer_port, or neither.",
        )

    get_chunk = None

    if body.peer_host is not None and body.peer_port is not None:

        def get_chunk(chunk_hash: str) -> bytes:
            return request.app.state.peer_manager.get_chunk(
                chunk_hash=chunk_hash,
                peer_host=body.peer_host,
                peer_port=body.peer_port,
            )

    try:
        output_path = assemble_file(
            manifest=body.manifest,
            chunks_dir=settings.chunks_dir,
            output_dir=settings.downloads_dir,
            get_chunk=get_chunk,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                "A required chunk is not cached locally. "
                "Provide a peer that has the chunk."
            ),
        ) from exc
    except FileAssemblyError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Complete-file assembly failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to assemble the requested file.",
        ) from exc

    return FileResponse(
        path=str(output_path),
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
                "No LAN IPv4 address found. Connect to the hotspot, "
                "then restart."
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
                "Several addresses found. Use the address shown under "
                "the active Wi-Fi adapter in ipconfig."
            )

    uvicorn.run(
        app,
        host=settings.api_host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
