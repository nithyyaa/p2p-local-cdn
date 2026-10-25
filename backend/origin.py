"""HTTP origin server for the P2P LAN CDN."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def create_origin_app(root_dir: str | Path) -> FastAPI:
    """Create an HTTP app that serves files from a designated directory."""
    root = Path(root_dir).resolve()

    if not root.is_dir():
        raise ValueError(f"Origin directory does not exist: {root}")

    app = FastAPI(title="P2P CDN Origin Server")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "p2p-cdn-origin"}

    @app.get("/files/{file_name}")
    def get_file(file_name: str):
        # Accept only a filename, not an arbitrary filesystem path.
        if file_name in {".", ".."} or "/" in file_name or "\\" in file_name:
            raise HTTPException(status_code=400, detail="Invalid filename")

        file_path = (root / file_name).resolve()

        # Ensure the resolved path stays inside the configured origin directory.
        if file_path.parent != root:
            raise HTTPException(status_code=400, detail="Invalid filename")

        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )

    return app
