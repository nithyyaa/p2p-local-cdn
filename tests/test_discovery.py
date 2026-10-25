
import json
import socket
import time
from dataclasses import replace

from backend.config import settings
from backend.discovery import PeerDiscovery


def test_discovery_starts_and_stops():
    config = replace(settings, discovery_port=0)
    discovery = PeerDiscovery(config)

    discovery.start()

    assert discovery.running is True
    assert discovery.socket is not None

    discovery.stop()

    assert discovery.running is False


def test_discovery_records_valid_announcement():
    config = replace(settings, discovery_port=0)
    discovery = PeerDiscovery(config)

    discovery.start()

    try:
        assert discovery.socket is not None
        port = discovery.socket.getsockname()[1]

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            message = {
                "node_id": "test-node-123",
                "node_name": "Test Peer",
                "transfer_port": 9100,
            }

            sender.sendto(
                json.dumps(message).encode("utf-8"),
                ("127.0.0.1", port),
            )

        deadline = time.time() + 2
        peers = []

        while time.time() < deadline:
            peers = discovery.get_peers()

            if any(
                peer["node_id"] == "test-node-123"
                for peer in peers
            ):
                break

            time.sleep(0.05)

        peer = next(
            peer
            for peer in peers
            if peer["node_id"] == "test-node-123"
        )

        assert peer["node_name"] == "Test Peer"
        assert peer["host"] == "127.0.0.1"
        assert peer["transfer_port"] == 9100

    finally:
        discovery.stop()


def test_discovery_ignores_invalid_announcement():
    config = replace(settings, discovery_port=0)
    discovery = PeerDiscovery(config)

    discovery.start()

    try:
        assert discovery.socket is not None
        port = discovery.socket.getsockname()[1]

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(
                b"not valid JSON",
                ("127.0.0.1", port),
            )

        time.sleep(0.2)

        assert discovery.get_peers() == []

    finally:
        discovery.stop()
