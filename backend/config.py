"""Central configuration for one P2P LAN CDN node.

Every setting has a default and can be overridden with an environment
variable. That lets you run two nodes side by side on one laptop, for
example in PowerShell:

    $env:P2P_API_PORT = "8001"
    $env:P2P_TRANSFER_PORT = "9101"
    $env:P2P_DISCOVERY_PORT = "9201"
    $env:P2P_STORAGE_DIR = "storage-node2"
    python -m backend.main

No IP addresses are configured here on purpose. Each node reads its own
addresses from the operating system at runtime, and nodes will find each
other with UDP discovery (a later step).
"""

from __future__ import annotations

import ipaddress
import os
import socket
import uuid
from dataclasses import dataclass
from pathlib import Path

# The project folder, e.g. D:\p2p-local-cdn (the folder that contains backend\).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API_PORT = 8000        # TCP: FastAPI backend and dashboard
DEFAULT_TRANSFER_PORT = 9100   # TCP: peer-to-peer chunk transfers
DEFAULT_DISCOVERY_PORT = 9200  # UDP: peer discovery broadcasts
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB per chunk

MIN_CHUNK_SIZE = 16 * 1024         # 16 KiB
MAX_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MiB


class ConfigError(ValueError):
    """Raised when an environment variable holds an invalid value."""


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}") from None
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    path = Path(raw).expanduser()
    if not path.is_absolute():
        # Relative paths are taken relative to the project folder, not to
        # whichever folder the terminal happens to be in.
        path = PROJECT_ROOT / path
    return path.resolve()


def _env_bind_host(name: str, default: str) -> str:
    value = _env_str(name, default)
    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise ConfigError(
            f"{name} must be an IPv4 address such as 0.0.0.0 (all adapters) "
            f"or 127.0.0.1 (this laptop only), got {value!r}"
        ) from None
    return value


@dataclass(frozen=True)
class Settings:
    node_name: str
    api_host: str
    api_port: int
    transfer_port: int
    discovery_port: int
    storage_dir: Path
    chunk_size: int

    @property
    def chunks_dir(self) -> Path:
        """Verified chunks, stored under their SHA-256 hash."""
        return self.storage_dir / "chunks"

    @property
    def manifests_dir(self) -> Path:
        """Manifests: the ordered list of chunk hashes for each file."""
        return self.storage_dir / "manifests"

    @property
    def downloads_dir(self) -> Path:
        """Complete files reassembled from verified chunks."""
        return self.storage_dir / "downloads"

    @property
    def node_id_file(self) -> Path:
        return self.storage_dir / "node_id.txt"


def load_settings() -> Settings:
    """Build the settings from defaults plus any P2P_* environment variables."""
    loaded = Settings(
        node_name=_env_str("P2P_NODE_NAME", socket.gethostname()),
        api_host=_env_bind_host("P2P_API_HOST", "0.0.0.0"),
        api_port=_env_int("P2P_API_PORT", DEFAULT_API_PORT, 1, 65535),
        transfer_port=_env_int("P2P_TRANSFER_PORT", DEFAULT_TRANSFER_PORT, 1, 65535),
        discovery_port=_env_int("P2P_DISCOVERY_PORT", DEFAULT_DISCOVERY_PORT, 1, 65535),
        storage_dir=_env_path("P2P_STORAGE_DIR", PROJECT_ROOT / "storage"),
        chunk_size=_env_int("P2P_CHUNK_SIZE", DEFAULT_CHUNK_SIZE, MIN_CHUNK_SIZE, MAX_CHUNK_SIZE),
    )
    ports = (loaded.api_port, loaded.transfer_port, loaded.discovery_port)
    if len(set(ports)) != len(ports):
        raise ConfigError(
            f"API, transfer and discovery ports must all be different, got {ports}"
        )
    return loaded


def ensure_storage_dirs(cfg: Settings) -> None:
    """Create the storage sub-folders if they do not exist yet."""
    for folder in (cfg.chunks_dir, cfg.manifests_dir, cfg.downloads_dir):
        folder.mkdir(parents=True, exist_ok=True)


def load_or_create_node_id(cfg: Settings) -> str:
    """Return this node's permanent ID, creating it on first run.

    The ID is a random UUID saved in the storage folder, so it stays the same
    across restarts but differs on every laptop (and for every storage folder,
    if you run two nodes on one laptop).
    """
    path = cfg.node_id_file
    try:
        return uuid.UUID(path.read_text(encoding="utf-8").strip()).hex
    except (FileNotFoundError, ValueError):
        pass  # first run, or the file was damaged: make a new ID
    node_id = uuid.uuid4().hex
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(node_id + "\n", encoding="utf-8")
    return node_id


# Loaded once when the module is first imported; other modules use this.
settings = load_settings()