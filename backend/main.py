"""FastAPI entry point for one P2P LAN CDN node.

Step 1 scope: start the API, prepare the storage folders and expose
GET /api/health, so we can prove that two laptops can reach each other.

Run from the project folder (D:\\p2p-local-cdn) with the venv active:

    python -m backend.main
"""

from __future__ import annotations

import ipaddress
import logging
import platform
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, Request

from backend.config import ensure_storage_dirs, load_or_create_node_id, settings
from backend.origin import create_origin_app
logger = logging.getLogger("p2p.node")

# Used only to ask the operating system which network adapter it would use
# for its default route. Connecting a UDP socket sends no packets, so nothing
# is ever sent to this address. 192.0.2.1 is reserved for documentation
# (RFC 5737); it is not a peer and does not need to exist.
_ROUTE_PROBE = ("192.0.2.1", 9)


def _is_lan_candidate(ip: str) -> bool:
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    # 127.x.x.x is loopback (reachable only from this machine).
    # 169.254.x.x is link-local: Windows self-assigns it when an adapter
    # could not get a real address, so other laptops cannot use it.
    return not (
        addr.is_loopback or addr.is_link_local or addr.is_unspecified or addr.is_multicast
    )


def detect_ipv4_addresses() -> tuple[str | None, list[str]]:
    """Return (primary, all_addresses) for this machine's usable IPv4 addresses.

    primary: the address of the adapter that holds the default route, which
        is usually the Wi-Fi adapter when you are on a phone hotspot.
    all_addresses: every usable IPv4 address the OS reports. On Windows this
        can include virtual adapters (WSL, Hyper-V, VirtualBox) that other
        laptops cannot reach.
    """
    primary: str | None = None
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(_ROUTE_PROBE)
        candidate = probe.getsockname()[0]
        if _is_lan_candidate(candidate):
            primary = candidate
    except OSError:
        pass  # no default route, e.g. not connected to any network
    finally:
        probe.close()

    addresses = [primary] if primary else []
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM)
    except socket.gaierror:
        infos = []
    for info in infos:
        ip = info[4][0]
        if _is_lan_candidate(ip) and ip not in addresses:
            addresses.append(ip)
    return primary, addresses


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts, before any request is handled.
    ensure_storage_dirs(settings)
    app.state.node_id = load_or_create_node_id(settings)
    app.state.started_at = datetime.now(timezone.utc)
    app.state.started_monotonic = time.monotonic()
    logger.info(
        "Node %s (%s) ready. Storage folder: %s",
        app.state.node_id,
        settings.node_name,
        settings.storage_dir,
    )
    yield


app = FastAPI(title="P2P LAN CDN node", version="0.1.0", lifespan=lifespan)
origin_app = create_origin_app(settings.downloads_dir)
app.mount("/origin", origin_app)

@app.get("/")
def root() -> dict[str, str]:
    """Placeholder until the dashboard is added in a later step."""
    return {"service": "p2p-lan-cdn-node", "health": "/api/health", "api_docs": "/docs"}


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    state = request.app.state
    primary, addresses = detect_ipv4_addresses()
    server = request.scope.get("server")  # this node's (ip, port) the request arrived on
    client = request.client               # the asker's (ip, port)
    return {
        "status": "ok",
        "node_id": state.node_id,
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
        "started_at": state.started_at.isoformat(timespec="seconds"),
        "uptime_seconds": round(time.monotonic() - state.started_monotonic, 1),
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    )
    port = settings.api_port
    host = ipaddress.IPv4Address(settings.api_host)
    primary, addresses = detect_ipv4_addresses()

    logger.info("Starting node '%s' on %s:%d", settings.node_name, settings.api_host, port)
    logger.info("Test on this laptop:      http://127.0.0.1:%d/api/health", port)
    if host.is_loopback:
        logger.warning(
            "P2P_API_HOST is %s, so other laptops cannot connect. Use 0.0.0.0 for LAN access.",
            settings.api_host,
        )
    else:
        lan_urls = addresses if host.is_unspecified else [settings.api_host]
        if not lan_urls:
            logger.warning("No LAN IPv4 address found. Connect to the hotspot, then restart.")
        for ip in lan_urls:
            note = "  (default route)" if ip == primary else ""
            logger.info("Test from another laptop: http://%s:%d/api/health%s", ip, port, note)
        if len(lan_urls) > 1:
            logger.info(
                "Several addresses found: use the one 'ipconfig' shows under your Wi-Fi adapter."
            )

    uvicorn.run(app, host=settings.api_host, port=port, log_level="info")


if __name__ == "__main__":
    main()