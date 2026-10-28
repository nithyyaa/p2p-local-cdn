
"""UDP-based peer discovery for the P2P LAN CDN."""

import json
import socket
import threading
import time
from typing import Any

from backend.config import Settings


class PeerDiscovery:
    """Discover other CDN nodes on the local network using UDP."""

    def __init__(
        self,
        settings: Settings,
        node_id: str | None = None,
    ):
        self.settings = settings
        self.node_id = node_id
        self.peers: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.running = False
        self.socket: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.announcer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start listening for peer announcements."""
        if self.running:
            return

        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp_socket.bind(("", self.settings.discovery_port))
        udp_socket.settimeout(1.0)

        self.socket = udp_socket
        self.running = True

        self.thread = threading.Thread(
            target=self._listen,
            daemon=True,
            name="peer-discovery-listener",
        )
        self.thread.start()

    def _listen(self) -> None:
        """Receive and record announcements from other peers."""
        while self.running:
            try:
                if self.socket is None:
                    break
                data, address = self.socket.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                message = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            if not isinstance(message, dict):
                continue

            peer_id = message.get("node_id")
            peer_name = message.get("node_name")
            peer_port = message.get("transfer_port")

            # Ignore announcements from this node itself.
            if self.node_id is not None and peer_id == self.node_id:
                continue

            if (
                not isinstance(peer_id, str)
                or not peer_id
                or not isinstance(peer_name, str)
                or not isinstance(peer_port, int)
                or isinstance(peer_port, bool)
                or not 1 <= peer_port <= 65535
            ):
                continue

            with self.lock:
                self.peers[peer_id] = {
                    "node_id": peer_id,
                    "node_name": peer_name,
                    "host": address[0],
                    "transfer_port": peer_port,
                    "last_seen": time.time(),
                }

    def announce(self, node_id: str, node_name: str) -> None:
        """Broadcast this node's presence to the local network."""
        message = {
            "node_id": node_id,
            "node_name": node_name,
            "transfer_port": self.settings.transfer_port,
        }

        data = json.dumps(message).encode("utf-8")

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_BROADCAST,
                1,
            )
            udp_socket.sendto(
                data,
                ("255.255.255.255", self.settings.discovery_port),
            )

    def announce_periodically(
        self,
        node_id: str,
        node_name: str,
        interval: float = 10.0,
    ) -> None:
        """Announce this node periodically in a background thread."""
        if interval <= 0:
            raise ValueError("Announcement interval must be positive")

        if self.announcer_thread is not None and self.announcer_thread.is_alive():
            return

        # Keep the local ID available to the listener.
        self.node_id = node_id

        def broadcast_loop() -> None:
            while self.running:
                try:
                    self.announce(node_id, node_name)
                except OSError:
                    pass

                # Use an event so shutdown can interrupt the wait.
                if self._stop_event.wait(interval):
                    break

        self._stop_event.clear()
        self.announcer_thread = threading.Thread(
            target=broadcast_loop,
            daemon=True,
            name="peer-announcer",
        )
        self.announcer_thread.start()

    def get_peers(self) -> list[dict[str, Any]]:
        """Return a snapshot of peers seen within the last 30 seconds."""
        cutoff = time.time() - 30

        with self.lock:
            self.peers = {
                peer_id: peer
                for peer_id, peer in self.peers.items()
                if peer["last_seen"] >= cutoff
            }
            return [peer.copy() for peer in self.peers.values()]

    def stop(self) -> None:
        """Stop the discovery listener and announcer."""
        self.running = False
        self._stop_event.set()

        if self.socket is not None:
            self.socket.close()
            self.socket = None

        if self.thread is not None:
            self.thread.join(timeout=2.0)
            self.thread = None

        if self.announcer_thread is not None:
            self.announcer_thread.join(timeout=2.0)
            self.announcer_thread = None
