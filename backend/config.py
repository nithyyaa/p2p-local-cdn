
"""Central configuration for one P2P LAN CDN node."""

from __future__ import annotations

import ipaddress
import os
import socket
import uuid
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API_PORT = 8000
DEFAULT_TRANSFER_PORT = 9100
DEFAULT_DISCOVERY_PORT = 9200
DEFAULT_CHUNK_SIZE = 1024 * 1024

MIN_CHUNK_SIZE = 16 * 1024
MAX_CHUNK_SIZE = 64 * 1024 * 1024


class ConfigError(ValueError):
    """Raised when an environment variable contains an invalid value."""


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _env_int(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default

    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(
            f"{name} must be a whole number, got {raw!r}"
        ) from None

    if not minimum <= value <= maximum:
        raise ConfigError(
            f"{name} must be between {minimum} and {maximum}, "
            f"got {value}"
        )

    return value


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()

    if not raw:
        return default.resolve()

    path = Path(raw).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def _env_bind_host(name: str, default: str) -> str:
    value = _env_str(name, default)

    try:
        ipaddress.IPv4Address(value)
    except ValueError:
        raise ConfigError(
            f"{name} must be an IPv4 address, got {value!r}"
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
    origin_dir: Path | None = None

    @property
    def chunks_dir(self) -> Path:
        """Verified chunks stored by SHA-256 hash."""
        return self.storage_dir / "chunks"

    @property
    def manifests_dir(self) -> Path:
        """Stored file manifests."""
        return self.storage_dir / "manifests"

    @property
    def downloads_dir(self) -> Path:
        """Completed files downloaded by this node."""
        return self.storage_dir / "downloads"

    @property
    def origin_files_dir(self) -> Path:
        """Authoritative origin files, separate from downloads."""
        if self.origin_dir is not None:
            return self.origin_dir

        return (PROJECT_ROOT / "origin_files").resolve()

    @property
    def node_id_file(self) -> Path:
        return self.storage_dir / "node_id.txt"


def load_settings() -> Settings:
    """Build settings from defaults and P2P_* environment variables."""
    loaded = Settings(
        node_name=_env_str(
            "P2P_NODE_NAME",
            socket.gethostname(),
        ),
        api_host=_env_bind_host(
            "P2P_API_HOST",
            "0.0.0.0",
        ),
        api_port=_env_int(
            "P2P_API_PORT",
            DEFAULT_API_PORT,
            1,
            65535,
        ),
        transfer_port=_env_int(
            "P2P_TRANSFER_PORT",
            DEFAULT_TRANSFER_PORT,
            1,
            65535,
        ),
        discovery_port=_env_int(
            "P2P_DISCOVERY_PORT",
            DEFAULT_DISCOVERY_PORT,
            1,
            65535,
        ),
        storage_dir=_env_path(
            "P2P_STORAGE_DIR",
            PROJECT_ROOT / "storage",
        ),
        chunk_size=_env_int(
            "P2P_CHUNK_SIZE",
            DEFAULT_CHUNK_SIZE,
            MIN_CHUNK_SIZE,
            MAX_CHUNK_SIZE,
        ),
        origin_dir=_env_path(
            "P2P_ORIGIN_DIR",
            PROJECT_ROOT / "origin_files",
        ),
    )

    ports = (
        loaded.api_port,
        loaded.transfer_port,
        loaded.discovery_port,
    )

    if len(set(ports)) != len(ports):
        raise ConfigError(
            "API, transfer, and discovery ports must be different: "
            f"{ports}"
        )

    return loaded


def ensure_storage_dirs(cfg: Settings) -> None:
    """Create required storage and origin directories."""
    for folder in (
        cfg.chunks_dir,
        cfg.manifests_dir,
        cfg.downloads_dir,
        cfg.origin_files_dir,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def load_or_create_node_id(cfg: Settings) -> str:
    """Load the persistent node ID or create one."""
    path = cfg.node_id_file

    try:
        return uuid.UUID(
            path.read_text(encoding="utf-8").strip()
        ).hex
    except (FileNotFoundError, ValueError):
        pass

    node_id = uuid.uuid4().hex
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(node_id + "\n", encoding="utf-8")

    return node_id


settings = load_settings()
