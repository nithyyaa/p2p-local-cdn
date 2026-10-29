
import hashlib
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


def test_download_endpoint_falls_back_to_origin():
    content = b"Origin fallback integration test!"
    chunk_hash = hashlib.sha256(content).hexdigest()

    manifest = {
        "file_name": "fallback_test.txt",
        "file_size": len(content),
        "chunk_size": len(content),
        "chunk_count": 1,
        "chunks": [
            {
                "index": 0,
                "size": len(content),
                "sha256": chunk_hash,
            }
        ],
    }

    origin_file = settings.origin_files_dir / "fallback_test.txt"
    origin_file.parent.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as client:
        state = app.state

        try:
            origin_file.write_bytes(content)

            with (
                patch.object(
                    state.peer_manager.chunk_store,
                    "get_chunk",
                    side_effect=FileNotFoundError(chunk_hash),
                ),
                patch.object(
                    state.peer_manager,
                    "get_chunk_from_peers",
                    side_effect=ConnectionError("No peers available"),
                ),
            ):
                response = client.post(
                    "/api/files/download",
                    json={"manifest": manifest},
                )

            assert response.status_code == 200, response.text
            assert response.content == content

        finally:
            origin_file.unlink(missing_ok=True)
